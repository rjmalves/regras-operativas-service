# Regras Operativas Service Modernization Plan

> **Version**: 2.0.0  
> **Target Completion**: ~4.5 weeks  
> **Status**: ✅ Complete

## Overview

Modernize regras-operativas-service from a PM2-managed, filesystem-dependent microservice to a containerized, S3-integrated service deployed via Docker Compose, aligning with the completed flexibilizador-service modernization.

## Quick Navigation

| Document | Description |
|----------|-------------|
| [00-master-plan.md](./00-master-plan.md) | Architecture, goals, S3 structure, design decisions |

### Epic 01: S3 Integration Layer (Week 1-2)

| Sprint | Focus | Tickets |
|--------|-------|---------|
| [Sprint 1](./epic-01-s3-integration/sprint-01/) | Core S3 infrastructure | 5 tickets |
| [Sprint 2](./epic-01-s3-integration/sprint-02/) | Unit of Work adaptation | 4 tickets |

### Epic 02: API Modernization (Week 2-3)

| Sprint | Focus | Tickets |
|--------|-------|---------|
| [Sprint 1](./epic-02-api-modernization/sprint-01/) | Request/Response models | 4 tickets |
| [Sprint 2](./epic-02-api-modernization/sprint-02/) | Router & Health endpoints | 4 tickets |

### Epic 03: Testing Infrastructure (Week 3-4)

| Sprint | Focus | Tickets |
|--------|-------|---------|
| [Sprint 1](./epic-03-testing/sprint-01/) | Test suite setup & coverage | 5 tickets |

### Epic 04: Docker & Deployment (Week 4)

| Sprint | Focus | Tickets |
|--------|-------|---------|
| [Sprint 1](./epic-04-docker-deployment/sprint-01/) | Containerization & systemd | 4 tickets |

### Epic 05: Documentation & Release (Week 4.5)

| Sprint | Focus | Tickets |
|--------|-------|---------|
| [Sprint 1](./epic-05-documentation/sprint-01/) | Docs, migration guide, release | 4 tickets |

## Progress Tracking

### Epic 01: S3 Integration Layer
- [x] TICKET-001: Create exception hierarchy
- [x] TICKET-002: Implement S3Repository
- [x] TICKET-003: Implement zip utilities
- [x] TICKET-004: Implement temp directory manager
- [x] TICKET-005: Create settings module with S3 config
- [x] TICKET-006: Create S3DecompUnitOfWork
- [x] TICKET-007: Create S3NewaveUnitOfWork  
- [x] TICKET-008: Adapt DECOMP repository for temp dirs
- [x] TICKET-009: Adapt NEWAVE repository for temp dirs

### Epic 02: API Modernization
- [x] TICKET-010: Create CaseReference model
- [x] TICKET-011: Update ReservoirRulesRequest model
- [x] TICKET-012: Update ReservoirRulesResponse model
- [x] TICKET-013: Create error response models
- [x] TICKET-014: Implement health router
- [x] TICKET-015: Update reservoir router for S3
- [x] TICKET-016: Create FastAPI dependency injection
- [x] TICKET-017: Update main.py application setup

### Epic 03: Testing Infrastructure
- [x] TICKET-018: Setup pytest and moto fixtures
- [x] TICKET-019: Unit tests for S3Repository
- [x] TICKET-020: Unit tests for utilities
- [x] TICKET-021: Integration tests for router
- [x] TICKET-022: Integration tests for Unit of Work

### Epic 04: Docker & Deployment
- [x] TICKET-023: Create pyproject.toml
- [x] TICKET-024: Create Dockerfile
- [x] TICKET-025: Create docker-compose files
- [x] TICKET-026: Create systemd service and deploy scripts

### Epic 05: Documentation & Release
- [x] TICKET-027: Update README.md
- [x] TICKET-028: Create MIGRATION.md
- [x] TICKET-029: Create DEPLOYMENT.md
- [x] TICKET-030: Create CHANGELOG.md and release

## AWS Resources Overview

| Resource | Purpose |
|----------|---------|
| S3 (newave-bucket) | NEWAVE artifact storage |
| S3 (decomp-bucket) | DECOMP artifact storage |
| IAM Role | S3 GetObject, PutObject, ListBucket |

## Key Differences from Flexibilizador

| Aspect | Flexibilizador | Regras Operativas |
|--------|----------------|-------------------|
| Programs | DECOMP only | NEWAVE + DECOMP |
| Input Sources | Single execution | Multiple sources (prospection) |
| File Modifications | `dadger.rvX` | `dadger.rvX`, `re.dat`, `modif.dat` |
| Data Flow | Same case | Read multiple → Write destination |

## Reference Implementation

Many components are copied/adapted from [flexibilizador-service](../../../../flexibilizador-service/):
- `app/adapters/s3_repository.py`
- `app/utils/zip_utils.py`
- `app/utils/temp_manager.py`
- `app/internal/exceptions.py`
- `Dockerfile`, `docker-compose.yml`
