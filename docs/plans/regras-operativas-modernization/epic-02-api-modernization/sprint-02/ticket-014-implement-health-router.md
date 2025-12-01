# TICKET-014: Implement Health Router

> **Epic**: [Epic 02: API Modernization](../../00-epic-overview.md)  
> **Sprint**: [Sprint 02](./00-sprint-overview.md)  
> **Points**: 2  
> **Dependencies**: None  
> **Blocks**: [TICKET-017](./ticket-017-update-main-app.md)

## Context

Add health check endpoints for container orchestration and monitoring.

## Specification

### File: `app/routers/health.py`

```python
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])

class LivenessResponse(BaseModel):
    status: str = "ok"

class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    checks: dict[str, str]

@router.get("/health/live", response_model=LivenessResponse)
async def liveness():
    """Liveness probe - returns immediately."""
    return LivenessResponse()

@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness():
    """Readiness probe - checks S3 connectivity."""
    checks = {}
    try:
        s3 = get_s3_repository()
        await s3.object_exists(Settings.default_decomp_bucket, "test")
        checks["s3_decomp"] = "ok"
    except Exception:
        checks["s3_decomp"] = "error"
    
    status = "ready" if all(v == "ok" for v in checks.values()) else "not_ready"
    return ReadinessResponse(status=status, checks=checks)

@router.get("/health", response_model=HealthResponse)
async def health():
    """Full health status with version."""
    readiness = await readiness()
    return HealthResponse(
        status="healthy" if readiness.status == "ready" else "unhealthy",
        version="2.0.0",
        timestamp=datetime.utcnow(),
        checks=readiness.checks
    )
```

## Acceptance Criteria

- [ ] `GET /health/live` returns 200 immediately
- [ ] `GET /health/ready` checks S3 connectivity
- [ ] `GET /health` returns version and full status
- [ ] Failed S3 check returns "not_ready"

## Reference

Copy from: `/home/rogerio/git/flexibilizador-service/app/routers/health.py`

## Effort: 2 points
