"""
app.py – Main Flask application for the Startup Blueprint Generator Agent.

Routes:
  GET  /                   → Landing page
  GET  /chat               → Chat / blueprint generation interface
  GET  /dashboard          → Blueprint history dashboard
  POST /api/generate       → Generate full blueprint (JSON)
  POST /api/validate       → Quick 5-dimension idea validation (JSON)
  POST /api/download-pdf   → Download blueprint as PDF
  GET  /api/health         → Health-check endpoint (for Code Engine probes)
  POST /api/clear-history  → Clear session blueprint history
"""

import json
import logging
import re
from datetime import datetime
from io import BytesIO

from flask import (
    Flask, render_template, request, jsonify,
    session, send_file, g
)

import config
from config import build_system_prompt
from utils.watsonx_client import generate_blueprint, validate_idea
from utils.pdf_generator import markdown_to_pdf

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Flask app initialisation
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB request limit

SYSTEM_PROMPT = build_system_prompt()

# ---------------------------------------------------------------------------
# Context processors
# ---------------------------------------------------------------------------

@app.context_processor
def inject_globals():
    """Make common values available to all templates."""
    return {
        "app_name": "Startup Blueprint AI",
        "model_id": config.GRANITE_MODEL_ID,
        "current_year": datetime.now().year,
    }


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _get_history() -> list:
    return session.get("blueprint_history", [])


def _save_to_history(idea: str, blueprint: str, score: int) -> None:
    history = _get_history()
    history.insert(0, {
        "id": len(history) + 1,
        "idea": idea[:120] + ("…" if len(idea) > 120 else ""),
        "full_idea": idea,
        "score": score,
        "timestamp": datetime.now().strftime("%d %b %Y, %H:%M"),
        "preview": blueprint[:300] + "…" if len(blueprint) > 300 else blueprint,
        "blueprint": blueprint,
    })
    # Keep last 20 blueprints in session
    session["blueprint_history"] = history[:20]


def _extract_startup_name(blueprint_text: str) -> str:
    """Try to pull the suggested startup name from the blueprint."""
    match = re.search(
        r"(?:Startup Name|Name)[:\s*#]+([A-Za-z0-9 &.,'\"!-]{2,60})",
        blueprint_text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip().strip("*#").strip()
    return "My Startup"


def _validate_credentials() -> bool:
    return bool(config.WATSONX_API_KEY and config.WATSONX_PROJECT_ID)


# ---------------------------------------------------------------------------
# Routes – Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Landing page."""
    return render_template("index.html")


@app.route("/chat")
def chat():
    """Blueprint generation chat interface."""
    return render_template("chat.html")


@app.route("/dashboard")
def dashboard():
    """Blueprint history dashboard."""
    history = _get_history()
    return render_template("dashboard.html", history=history)


# ---------------------------------------------------------------------------
# Routes – API
# ---------------------------------------------------------------------------

@app.route("/api/health")
def health():
    """Health-check endpoint (used by Code Engine liveness probes)."""
    creds_ok = _validate_credentials()
    return jsonify({
        "status": "ok" if creds_ok else "degraded",
        "credentials_configured": creds_ok,
        "model": config.GRANITE_MODEL_ID,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }), 200


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """
    Generate a full startup blueprint.

    Request JSON:  { "idea": "<startup idea text>" }
    Response JSON: {
        "success": bool,
        "blueprint": str,
        "readiness_score": int,
        "startup_name": str,
        "error": str | null
    }
    """
    if not _validate_credentials():
        return jsonify({
            "success": False,
            "error": (
                "IBM watsonx.ai credentials are not configured. "
                "Please set WATSONX_API_KEY and WATSONX_PROJECT_ID "
                "in your .env file."
            ),
        }), 503

    data = request.get_json(silent=True) or {}
    idea = (data.get("idea") or "").strip()

    if not idea:
        return jsonify({"success": False, "error": "Please provide a startup idea."}), 400

    if len(idea) < 10:
        return jsonify({
            "success": False,
            "error": "Your idea is too short. Please describe it in at least a sentence.",
        }), 400

    if len(idea) > 3000:
        return jsonify({
            "success": False,
            "error": "Idea text is too long (max 3 000 characters). Please summarise.",
        }), 400

    logger.info("Generating blueprint for idea: %.80s…", idea)
    result = generate_blueprint(idea, SYSTEM_PROMPT)

    if result["success"]:
        startup_name = _extract_startup_name(result["blueprint"])
        _save_to_history(idea, result["blueprint"], result["readiness_score"])
        return jsonify({
            "success": True,
            "blueprint": result["blueprint"],
            "readiness_score": result["readiness_score"],
            "startup_name": startup_name,
            "error": None,
        })

    return jsonify({"success": False, "error": result["error"]}), 500


@app.route("/api/validate", methods=["POST"])
def api_validate():
    """
    Quick 5-dimension idea validation (no full blueprint).

    Request JSON:  { "idea": "<startup idea text>" }
    Response JSON: { "success": bool, "validation": str, "error": str | null }
    """
    if not _validate_credentials():
        return jsonify({
            "success": False,
            "error": "IBM watsonx.ai credentials not configured.",
        }), 503

    data = request.get_json(silent=True) or {}
    idea = (data.get("idea") or "").strip()

    if not idea:
        return jsonify({"success": False, "error": "Please provide a startup idea."}), 400

    result = validate_idea(idea, SYSTEM_PROMPT)
    return jsonify(result), 200 if result["success"] else 500


@app.route("/api/download-pdf", methods=["POST"])
def api_download_pdf():
    """
    Convert a blueprint to PDF and return it as a file download.

    Request JSON:  { "blueprint": str, "startup_name": str }
    """
    data = request.get_json(silent=True) or {}
    blueprint_md = (data.get("blueprint") or "").strip()
    startup_name = (data.get("startup_name") or "My Startup").strip()

    if not blueprint_md:
        return jsonify({"success": False, "error": "No blueprint content provided."}), 400

    try:
        pdf_bytes = markdown_to_pdf(blueprint_md, startup_name)
        filename  = re.sub(r"[^\w\s-]", "", startup_name).strip().replace(" ", "_")
        filename  = f"{filename}_Blueprint.pdf"

        return send_file(
            BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as exc:
        logger.error("PDF generation error: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": f"PDF generation failed: {exc}"}), 500


@app.route("/api/clear-history", methods=["POST"])
def api_clear_history():
    """Clear the blueprint history stored in the user's session."""
    session.pop("blueprint_history", None)
    return jsonify({"success": True, "message": "History cleared."})


@app.route("/api/history")
def api_history():
    """Return current blueprint history as JSON."""
    return jsonify({"success": True, "history": _get_history()})


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404,
                           message="Page not found."), 404


@app.errorhandler(413)
def request_too_large(e):
    return jsonify({"success": False, "error": "Request too large."}), 413


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500,
                           message="Internal server error."), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    debug = config.FLASK_ENV == "development"
    logger.info(
        "Starting Startup Blueprint AI on port %d (debug=%s, model=%s)",
        config.PORT, debug, config.GRANITE_MODEL_ID,
    )
    app.run(host="0.0.0.0", port=config.PORT, debug=debug)
