# =============================================================================
# Regras Operativas Service - Multi-stage Dockerfile
# =============================================================================
# Build: docker build -t regras-operativas-service:latest .
# Run:   docker run -p 8000:8000 --env-file .env regras-operativas-service:latest
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies with uv
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system dependencies and uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:$PATH"

# Create virtual environment
RUN uv venv /opt/venv

# Copy dependency files
COPY pyproject.toml README.md ./

# Install dependencies into virtual environment
RUN uv pip install --python=/opt/venv/bin/python --no-cache .

# -----------------------------------------------------------------------------
# Stage 2: Production - Minimal runtime image
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS production

# Labels
LABEL org.opencontainers.image.title="Regras Operativas Service"
LABEL org.opencontainers.image.description="Reservoir operation rules service for NEWAVE/DECOMP"
LABEL org.opencontainers.image.version="2.0.0"
LABEL org.opencontainers.image.vendor="Energy Planning Team"
LABEL org.opencontainers.image.source="https://github.com/your-org/regras-operativas-service"

# Create non-root user
RUN groupadd -r -g 1000 app && useradd -r -u 1000 -g app app

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy application code
COPY --chown=app:app app/ ./app/
COPY --chown=app:app main.py ./
COPY --chown=app:app regras.json ./
COPY --chown=app:app regras_reservatorios.csv ./

# Create temp directory for processing
RUN mkdir -p /tmp/regras-operativas && chown app:app /tmp/regras-operativas
ENV TEMP_DIR=/tmp/regras-operativas

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')" || exit 1

# Default command - run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
