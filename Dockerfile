# ==============================================================================
# Startup Blueprint AI – Dockerfile
# Compatible with IBM Cloud Code Engine (port 8080, non-root user)
# ==============================================================================

# --- Stage 1: Build / dependency installation ---
FROM python:3.12-slim AS builder

WORKDIR /build

# Install only build-time dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- Stage 2: Runtime image ---
FROM python:3.12-slim AS runtime

# Create a non-root user for security (Code Engine best practice)
RUN useradd --uid 1001 --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=appuser:appuser . .

# Remove any local .env so secrets must come from environment variables
RUN rm -f .env

# Switch to non-root user
USER appuser

# Code Engine listens on 8080
EXPOSE 8080

# Health check – Code Engine uses HTTP probes
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')"

# Start with Gunicorn (production WSGI server)
# --workers: 2 × CPU + 1 is a good baseline; Code Engine starter = 1 vCPU
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "app:app"]
