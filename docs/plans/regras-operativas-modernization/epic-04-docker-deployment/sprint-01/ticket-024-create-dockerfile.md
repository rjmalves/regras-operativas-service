# [TICKET-024] Create Dockerfile

> **Epic**: [Epic 04: Docker & Deployment](../00-epic-overview.md)  
> **Sprint**: [Sprint 1](./00-sprint-overview.md)  
> **Dependencies**: TICKET-023 (pyproject.toml)  
> **Blocks**: TICKET-025 (docker-compose)

## Context

### Background

Create a production-ready Dockerfile using multi-stage build pattern and `uv` for fast dependency installation. The image should be small (<200MB), secure (non-root user), and include health checks.

### Reference

Based on flexibilizador-service Dockerfile pattern.

## Specification

### Files to Create

1. `Dockerfile`
2. `.dockerignore`

### Dockerfile Implementation

```dockerfile
# =============================================================================
# Stage 1: Builder - Install dependencies with uv
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install uv for fast dependency management
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"

# Create virtual environment
RUN uv venv /opt/venv

# Copy dependency files
COPY pyproject.toml README.md ./

# Install production dependencies only
RUN uv pip install --python=/opt/venv/bin/python --no-cache .

# =============================================================================
# Stage 2: Production - Minimal runtime image
# =============================================================================
FROM python:3.12-slim AS production

# Labels
LABEL org.opencontainers.image.title="Regras Operativas Service"
LABEL org.opencontainers.image.description="Reservoir operation rules service for NEWAVE/DECOMP"
LABEL org.opencontainers.image.version="2.0.0"
LABEL org.opencontainers.image.vendor="Energy Planning Team"

# Create non-root user
RUN groupadd -r -g 1000 app \
    && useradd -r -u 1000 -g app app

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set PATH to use virtual environment
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application code
COPY --chown=app:app app/ ./app/
COPY --chown=app:app main.py ./

# Create temp directory for processing
RUN mkdir -p /tmp/regras-operativas \
    && chown -R app:app /tmp/regras-operativas

# Environment defaults
ENV HOST=0.0.0.0
ENV PORT=8000
ENV LOG_LEVEL=INFO
ENV TEMP_DIR=/tmp/regras-operativas

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')" || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# Stage 3: Development - With dev dependencies (optional)
# =============================================================================
FROM builder AS dev-builder

# Install dev dependencies
RUN uv pip install --python=/opt/venv/bin/python --no-cache ".[dev]"

FROM production AS development

# Copy dev venv
COPY --from=dev-builder /opt/venv /opt/venv

# Override for development
ENV LOG_LEVEL=DEBUG

# Use reload for development
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### .dockerignore Implementation

```dockerignore
# Git
.git
.gitignore

# Python
__pycache__
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.env
.venv
env/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# Tests
tests/
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/

# Documentation
docs/
*.md
!README.md

# CI/CD
.github/
.gitlab-ci.yml
Jenkinsfile

# Docker
Dockerfile*
docker-compose*.yml
.docker/

# Misc
*.log
*.tmp
.DS_Store
Thumbs.db

# Local data
regras.json
regras_reservatorios.csv
*.zip

# Deploy scripts
deploy/
```

## Build and Test Commands

### Build Production Image

```bash
# Build production image
docker build -t regras-operativas-service:2.0.0 .

# Build with specific target
docker build --target production -t regras-operativas-service:2.0.0 .
```

### Build Development Image

```bash
# Build development image with dev dependencies
docker build --target development -t regras-operativas-service:dev .
```

### Test Image

```bash
# Check image size
docker images regras-operativas-service:2.0.0

# Run container
docker run -d --name regras-test \
    -p 8000:8000 \
    -e AWS_REGION=us-east-1 \
    -e DEFAULT_DECOMP_BUCKET=decomp-bucket \
    -e DEFAULT_NEWAVE_BUCKET=newave-bucket \
    regras-operativas-service:2.0.0

# Check health
curl http://localhost:8000/health/live

# View logs
docker logs regras-test

# Stop and remove
docker stop regras-test && docker rm regras-test
```

### Verify Image Size

```bash
# Should be under 200MB
docker images regras-operativas-service:2.0.0 --format "{{.Size}}"
```

## Acceptance Criteria

- [ ] `docker build` succeeds without errors
- [ ] Image size < 200MB
- [ ] Container starts successfully
- [ ] Health check passes: `curl localhost:8000/health/live`
- [ ] Non-root user (uid 1000) runs the process
- [ ] No secrets in image layers
- [ ] `.dockerignore` excludes tests, docs, local files

## Implementation Guide

### Step 1: Create .dockerignore

Create `.dockerignore` to exclude unnecessary files from build context.

### Step 2: Create Dockerfile

Create `Dockerfile` with multi-stage build.

### Step 3: Build and Test

```bash
# Build
docker build -t regras-operativas-service:2.0.0 .

# Test startup
docker run --rm -p 8000:8000 regras-operativas-service:2.0.0 &
sleep 5
curl http://localhost:8000/health/live
docker stop $(docker ps -q --filter ancestor=regras-operativas-service:2.0.0)
```

### Step 4: Verify Size

```bash
docker images regras-operativas-service:2.0.0
```

## Pitfalls to Avoid

- ⚠️ Don't include AWS credentials in image
- ⚠️ Don't run as root
- ⚠️ Don't include dev dependencies in production image
- ⚠️ Use `--no-cache` with uv/pip to reduce image size
- ⚠️ Clean up apt cache after installs

## Definition of Done

- [ ] Dockerfile created
- [ ] .dockerignore created
- [ ] Build succeeds
- [ ] Image < 200MB
- [ ] Container runs
- [ ] Health check works
- [ ] Non-root user verified

## Effort Estimate

**Points**: 3  
**Confidence**: High  
**Rationale**: Standard multi-stage Docker pattern, based on flexibilizador template
