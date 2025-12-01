# [TICKET-027] Update README.md

> **Epic**: [Epic 05: Documentation & Release](../00-epic-overview.md)  
> **Sprint**: [Sprint 1](./00-sprint-overview.md)  
> **Dependencies**: All implementation tickets complete  
> **Blocks**: TICKET-030 (release)

## Context

### Background

The README.md needs a complete rewrite for v2.0.0, reflecting the new S3-based architecture, Docker deployment, and modernized API. The documentation should enable new developers to understand, deploy, and use the service quickly.

### Current State

Basic README exists but documents the legacy PM2/filesystem approach.

## Specification

### File to Update

`README.md`

### Target Structure

```markdown
# regras-operativas-service

Service for applying reservoir operation rules to NEWAVE and DECOMP energy planning models. Part of the HPC processing pipeline.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

The regras-operativas-service applies configurable reservoir operation rules to NEWAVE and DECOMP simulation files. It reads source case data from S3, calculates rule activation based on reservoir storage levels, and writes modified files back to S3.

### Key Features

- **S3 Integration**: Read/write artifacts from S3 buckets
- **Multi-Source Support**: Aggregate data from multiple source executions
- **NEWAVE Support**: Modify `re.dat` and `modif.dat` files
- **DECOMP Support**: Modify `dadger.rvX` files
- **Docker Deployment**: Containerized with Docker Compose
- **Health Endpoints**: Kubernetes-ready liveness and readiness probes

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone repository
git clone https://github.com/your-org/regras-operativas-service.git
cd regras-operativas-service

# Configure environment
cp .env.example .env
# Edit .env with your AWS credentials and bucket names

# Start service
docker compose up -d

# Check health
curl http://localhost:8000/health/live
```

### Local Development

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --extra dev

# Run locally
uv run uvicorn main:app --reload --port 8000

# Run tests
uv run pytest
```

## API Reference

### Apply Reservoir Rules

**POST** `/reservoir/`

Apply reservoir operation rules to a destination case based on source case data.

#### Request

```json
{
  "sources": [
    {
      "bucket": "decomp-bucket",
      "execution_hash": "abc123def456",
      "program": "DECOMP"
    }
  ],
  "destination": {
    "bucket": "newave-bucket",
    "execution_hash": "xyz789ghi012",
    "program": "NEWAVE",
    "output_prefix": "ingest"
  },
  "rules": [
    {
      "reservoirCode": 156,
      "uheCode": 156,
      "constraintType": "QDEF",
      "month": 1,
      "minVolume": 0.0,
      "maxVolume": 30.0,
      "minLimit": 100.0,
      "maxLimit": 99999.0,
      "frequency": "M",
      "label": "Restricao Exemplo"
    }
  ]
}
```

#### Response (Success - 200)

```json
{
  "success": true,
  "execution_hash": "xyz789ghi012",
  "output_key": "ingest/xyz789ghi012_regras.zip",
  "rules_applied": [...],
  "message": "Applied 5 reservoir rules"
}
```

#### Response (Error - 404)

```json
{
  "error_code": "ARTIFACT_NOT_FOUND",
  "message": "Object not found: s3://decomp-bucket/artifacts/abc123/entradas/deck_processado.zip",
  "details": {
    "bucket": "decomp-bucket",
    "key": "artifacts/abc123/entradas/deck_processado.zip"
  }
}
```

### Health Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health/live` | Liveness probe - returns 200 if service is running |
| `GET /health/ready` | Readiness probe - returns 200 if S3 is accessible |
| `GET /health/version` | Returns service version information |

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Bind address | `0.0.0.0` |
| `PORT` | Bind port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `S3_ENDPOINT_URL` | S3 endpoint (for LocalStack/MinIO) | _(empty = AWS)_ |
| `DEFAULT_DECOMP_BUCKET` | Default DECOMP bucket | `decomp-bucket` |
| `DEFAULT_NEWAVE_BUCKET` | Default NEWAVE bucket | `newave-bucket` |
| `TEMP_DIR` | Temporary directory | `/tmp/regras-operativas` |

### S3 Bucket Structure

```
s3://decomp-bucket/
├── artifacts/
│   └── <execution_hash>/
│       ├── entradas/
│       │   └── deck_processado.zip    # Input
│       └── saidas/
│           └── relato.rv0             # For prospection
└── ingest/
    └── <execution_hash>_regras.zip    # Output

s3://newave-bucket/
├── artifacts/
│   └── <execution_hash>/
│       └── entradas/
│           └── deck_processado.zip    # Input
└── ingest/
    └── <execution_hash>_regras.zip    # Output
```

### IAM Permissions

The service requires the following S3 permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::decomp-bucket",
        "arn:aws:s3:::decomp-bucket/*",
        "arn:aws:s3:::newave-bucket",
        "arn:aws:s3:::newave-bucket/*"
      ]
    }
  ]
}
```

## Development

### Project Structure

```
regras-operativas-service/
├── app/
│   ├── adapters/         # S3, DECOMP, NEWAVE repositories
│   ├── models/           # Pydantic models
│   ├── routers/          # FastAPI routers
│   ├── services/         # Unit of Work classes
│   ├── internal/         # Settings, exceptions
│   └── utils/            # Utilities (zip, temp dirs)
├── tests/
│   ├── unit/
│   └── integration/
├── deploy/               # systemd and scripts
├── main.py
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=app --cov-report=html

# Unit tests only
uv run pytest tests/unit/ -v

# Integration tests only
uv run pytest tests/integration/ -v
```

### Code Quality

```bash
# Linting
uv run ruff check app/

# Type checking
uv run mypy app/

# Format code
uv run ruff format app/
```

## Deployment

### Docker Compose (Production)

```bash
# Start with Traefik integration
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### systemd Service

```bash
# Install
sudo ./deploy/install.sh

# Status
sudo systemctl status regras-operativas

# Logs
journalctl -u regras-operativas -f

# Upgrade
sudo ./deploy/upgrade.sh

# Uninstall
sudo ./deploy/uninstall.sh
```

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment instructions.

## Migration from v1.x

See [MIGRATION.md](docs/MIGRATION.md) for migration guide from PM2/filesystem to Docker/S3.

## Related Services

- [flexibilizador-service](https://github.com/your-org/flexibilizador-service) - DECOMP flexibility service

## License

MIT License - see [LICENSE](LICENSE) file.
```

## Acceptance Criteria

- [ ] README.md rewritten with v2.0 content
- [ ] Quick start instructions work
- [ ] API reference is accurate
- [ ] Configuration documented
- [ ] Development instructions work
- [ ] All links valid
- [ ] No references to PM2 or filesystem paths

## Implementation Guide

### Step 1: Review Current README

Note any content worth preserving.

### Step 2: Write New README

Follow the structure above, adapting to actual implementation.

### Step 3: Verify Instructions

```bash
# Test quick start commands
docker compose up -d
curl http://localhost:8000/health/live
docker compose down
```

### Step 4: Check Links

Ensure all internal links work.

## Definition of Done

- [ ] README.md updated
- [ ] Instructions verified
- [ ] API examples accurate
- [ ] No legacy references
- [ ] Links working

## Effort Estimate

**Points**: 2  
**Confidence**: High  
**Rationale**: Documentation writing, clear structure provided
