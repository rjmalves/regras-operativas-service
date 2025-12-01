# Epic 04: Docker & Deployment

> **Duration**: 0.5 week (1 sprint)  
> **Status**: ✅ Complete  
> **Dependencies**: [Epic 01-03](../epic-01-s3-integration/00-epic-overview.md) ✅

## Summary

Containerize the service with Docker and set up production deployment with systemd integration.

## Scope

### Included

- ✅ pyproject.toml creation (replace requirements.txt)
- ✅ Multi-stage Dockerfile with uv
- ✅ docker-compose.yml for production
- ✅ docker-compose.dev.yml for development
- ✅ systemd service and deploy scripts

### Excluded

- Kubernetes manifests
- CI/CD pipeline setup

## Files Created

| File | Description |
|------|-------------|
| `pyproject.toml` | Modern Python packaging with pytest/ruff/mypy config |
| `Dockerfile` | Multi-stage build with uv, non-root user |
| `docker-compose.yml` | Production compose with Traefik labels |
| `docker-compose.dev.yml` | Dev compose with LocalStack S3 |
| `.dockerignore` | Build context exclusions |
| `deploy/regras-operativas.service` | systemd unit file |
| `deploy/install.sh` | Installation script |
| `deploy/uninstall.sh` | Uninstallation script |

## Acceptance Criteria

- [x] Docker configuration files created
- [x] pyproject.toml with modern tooling config
- [x] Multi-stage Dockerfile with health checks
- [x] Traefik labels configured
- [x] systemd service and deploy scripts

## Sprint

| Sprint | Focus | Tickets |
|--------|-------|---------|
| [Sprint 1](./sprint-01/) | Containerization and deployment | 4 tickets ✅ |

## Definition of Done

- [x] Docker files created
- [x] Health checks configured
- [x] Deploy scripts work
