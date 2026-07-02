"""
utils/watsonx_client.py – Thin wrapper around the ibm-watsonx-ai SDK.

All model calls go through this module so config changes propagate
from a single place.
"""

import re
import logging
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Human-readable hint added to IAM / credential error messages so the user
# knows exactly what to fix in their .env file.
# ---------------------------------------------------------------------------
_CREDENTIAL_HINT = (
    "\n\nTo fix this:\n"
    "1. Open your .env file in the startup-blueprint/ directory.\n"
    "2. Ensure WATSONX_API_KEY is a valid IBM Cloud API key "
    "(create one at https://cloud.ibm.com/iam/apikeys).\n"
    "3. Ensure WATSONX_PROJECT_ID matches your watsonx.ai project "
    "(found in your project's Manage tab on dataplatform.cloud.ibm.com).\n"
    "4. Ensure WATSONX_URL is the correct regional endpoint, e.g. "
    "https://us-south.ml.cloud.ibm.com\n"
    "5. Save the .env file and restart the Flask server."
)


def _build_credentials() -> Credentials:
    """Return a Credentials object from the current config values."""
    return Credentials(
        url=config.WATSONX_URL,
        api_key=config.WATSONX_API_KEY,
    )


def _make_model(max_new_tokens: int | None = None) -> ModelInference:
    """
    Instantiate a ModelInference object directly from Credentials.

    Note: ModelInference handles its own token management internally —
    no separate APIClient() call is needed (and calling APIClient()
    eagerly forces an IAM round-trip before generate_text is even called,
    which turns a retryable network error into an immediate crash).
    """
    params = {
        GenParams.TEMPERATURE:        config.AGENT_TEMPERATURE,
        GenParams.MAX_NEW_TOKENS:     max_new_tokens or config.AGENT_MAX_TOKENS,
        GenParams.TOP_P:              config.AGENT_TOP_P,
        GenParams.REPETITION_PENALTY: 1.1,
        GenParams.STOP_SEQUENCES:     [],
    }
    return ModelInference(
        model_id=config.GRANITE_MODEL_ID,
        params=params,
        credentials=_build_credentials(),
        project_id=config.WATSONX_PROJECT_ID,
    )


def _friendly_error(exc: Exception) -> str:
    """
    Convert a raw WMLClientError / requests exception into a message
    that helps the user understand whether the problem is credentials,
    network, quota, or something else.
    """
    raw = str(exc)
    low = raw.lower()

    if "400" in raw or "iam token" in low or "api_key" in low:
        return (
            "IBM Cloud IAM authentication failed (HTTP 400). "
            "Your WATSONX_API_KEY is invalid, expired, or missing."
            + _CREDENTIAL_HINT
        )
    if "401" in raw or "unauthorized" in low:
        return (
            "IBM Cloud returned 401 Unauthorized. "
            "Check that your API key has 'Editor' or higher access to the "
            "watsonx.ai service in your IBM Cloud IAM settings."
            + _CREDENTIAL_HINT
        )
    if "403" in raw or "forbidden" in low:
        return (
            "IBM Cloud returned 403 Forbidden. "
            "Your API key does not have permission to use this watsonx.ai project. "
            "Verify the project ID and IAM role."
            + _CREDENTIAL_HINT
        )
    if "404" in raw or "not found" in low:
        return (
            "Resource not found (HTTP 404). "
            "Double-check WATSONX_PROJECT_ID and WATSONX_URL in your .env file."
            + _CREDENTIAL_HINT
        )
    if "connection" in low or "timeout" in low or "network" in low:
        return (
            f"Network error connecting to IBM watsonx.ai ({config.WATSONX_URL}). "
            "Check your internet connection and that WATSONX_URL is correct."
        )
    return raw


def generate_blueprint(user_idea: str, system_prompt: str) -> dict:
    """
    Send the startup idea to IBM Granite and return a structured response.

    Returns:
        {
          "success": bool,
          "blueprint": str,        # full markdown text
          "readiness_score": int,  # 0-100
          "error": str | None
        }
    """
    try:
        model = _make_model()

        # Granite instruct-style prompt
        prompt = (
            f"<|system|>\n{system_prompt}\n<|user|>\n"
            f"Generate a complete startup blueprint for the following idea:\n\n"
            f"{user_idea}\n<|assistant|>\n"
        )

        response = model.generate_text(prompt=prompt)

        blueprint_text = response if isinstance(response, str) else str(response)
        readiness_score = _extract_readiness_score(blueprint_text)

        return {
            "success": True,
            "blueprint": blueprint_text,
            "readiness_score": readiness_score,
            "error": None,
        }

    except Exception as exc:
        msg = _friendly_error(exc)
        logger.error("watsonx generate_blueprint error: %s", msg)
        return {
            "success": False,
            "blueprint": "",
            "readiness_score": 0,
            "error": msg,
        }


def validate_idea(user_idea: str, system_prompt: str) -> dict:
    """
    Quick 5-dimension idea validation (faster / shorter call).

    Returns:
        {
          "success": bool,
          "validation": str,
          "error": str | None
        }
    """
    try:
        model = _make_model(max_new_tokens=600)

        prompt = (
            f"<|system|>\n{system_prompt}\n<|user|>\n"
            f"Perform ONLY the 5-dimension idea validation (no full blueprint) "
            f"for the following startup idea:\n\n{user_idea}\n"
            f"Format each dimension as a bold heading followed by one sentence.\n"
            f"End with a 'Quick Verdict:' line.\n<|assistant|>\n"
        )

        response = model.generate_text(prompt=prompt)
        return {
            "success": True,
            "validation": response if isinstance(response, str) else str(response),
            "error": None,
        }

    except Exception as exc:
        msg = _friendly_error(exc)
        logger.error("watsonx validate_idea error: %s", msg)
        return {
            "success": False,
            "validation": "",
            "error": msg,
        }


def _extract_readiness_score(text: str) -> int:
    """
    Parse 'Business Readiness Score: XX/100' from the blueprint text.
    Falls back to 0 if not found.
    """
    pattern = r"Business\s+Readiness\s+Score[:\s]+(\d{1,3})\s*/\s*100"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        score = int(match.group(1))
        return max(0, min(100, score))
    return 0
