# Epic 02: API Modernization

> **Duration**: 1.5 weeks (2 sprints)  
> **Status**: ✅ Complete  
> **Dependencies**: [Epic 01: S3 Integration Layer](../epic-01-s3-integration/00-epic-overview.md) ✅

## Summary

Modernize the API contract to use S3 references (bucket + execution_hash) instead of base62-encoded filesystem paths. Add health endpoints and structured error responses.

## Scope

### Included

- ✅ CaseReference model with S3 fields
- ✅ Updated request/response models (V2)
- ✅ Error response models
- ✅ Health check endpoints (`/health/live`, `/health/ready`)
- ✅ Updated reservoir router using S3 Unit of Work
- ✅ FastAPI dependency injection for S3Repository
- ✅ Updated application setup

### Excluded

- Testing infrastructure (Epic 03)
- Docker containerization (Epic 04)

## API Changes Summary

| Aspect | v1.x (Current) | v2.0 (Target) |
|--------|----------------|---------------|
| Input | `id` (base62) | `bucket` + `execution_hash` |
| Response | `{"result": [...]}` | `{"success": true, "output_key": "...", ...}` |
| Errors | Plain text | Structured JSON with error_code |
| Health | None | `/health/live`, `/health/ready` |
| Port | 5054 | 8000 |

## Acceptance Criteria

- [x] Request accepts `bucket` and `execution_hash` instead of `id` (V2 model)
- [x] Response includes `success`, `output_key`, `rules_applied` (V2 model)
- [x] Error responses have `error_code`, `message`, `details`
- [x] `/health/live` returns 200 immediately
- [x] `/health/ready` checks S3 connectivity
- [x] V1 endpoint preserved as deprecated for backward compatibility
- [x] OpenAPI docs reflect new contract

## Sprints

| Sprint | Focus | Duration | Status |
|--------|-------|----------|--------|
| [Sprint 1](./sprint-01/) | Request/Response models, error models | 0.75 week | ✅ Complete |
| [Sprint 2](./sprint-02/) | Router update, health endpoints | 0.75 week | ✅ Complete |

## Files Created/Modified

| File | Action | Description | Status |
|------|--------|-------------|--------|
| `app/models/case.py` | MODIFY | CaseReference model | ✅ Done |
| `app/models/errors.py` | CREATE | Error response models | ✅ Done |
| `app/models/reservoirrulesrequest.py` | MODIFY | S3 fields (V2) | ✅ Done |
| `app/models/reservoirrulesresponse.py` | MODIFY | Add output_key (V2) | ✅ Done |
| `app/routers/health.py` | CREATE | Health endpoints | ✅ Done |
| `app/routers/reservoir.py` | MODIFY | S3 workflow (V1 + V2) | ✅ Done |
| `app/services/unitofwork.py` | MODIFY | Sync wrapper classes | ✅ Done |
| `app/internal/dependencies.py` | MODIFY | S3 repo injection | ✅ Done |
| `main.py` | MODIFY | Include health router | ✅ Done |

## Routes Exposed

```
GET  /health/live      - Liveness probe
GET  /health/ready     - Readiness probe  
GET  /health           - Full health status
POST /reservoir/       - V1 (legacy, deprecated)
POST /reservoir/v2/    - V2 (S3-based)
```

## Test Results

- All 146 tests passing
- Unit tests for models, exceptions, and health router
- Integration tests for S3 unit of work

## Definition of Done

- [x] All acceptance criteria met
- [x] OpenAPI docs updated
- [x] Unit tests for all models (35+ tests)
- [x] V1 endpoint preserved for backward compatibility
- [x] All tests passing (146 total)
