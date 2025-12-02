"""
Health check endpoints for container orchestration and monitoring.

Provides:
- /health/live - Liveness probe (returns immediately)
- /health/ready - Readiness probe (checks dependencies)
- /health - Full health status with version
"""

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.adapters.s3_repository import get_s3_repository
from app.internal.settings import Settings

router = APIRouter(tags=["Health"])

# Version should match the service version
SERVICE_VERSION = "2.0.0"


class LivenessResponse(BaseModel):
    """Response for liveness probe."""

    status: str = Field(default="ok", description="Service status")


class ReadinessResponse(BaseModel):
    """Response for readiness probe."""

    status: str = Field(..., description="Ready or not_ready")
    checks: dict[str, str] = Field(..., description="Individual check results")


class HealthResponse(BaseModel):
    """Full health response with version and checks."""

    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(..., description="Health check timestamp")
    checks: dict[str, str] = Field(..., description="Individual check results")


@router.get(
    "/health/live",
    response_model=LivenessResponse,
    summary="Liveness probe",
    description="Simple liveness check for Kubernetes/Docker. Returns immediately.",
)
async def liveness() -> LivenessResponse:
    """
    Liveness probe - returns immediately to indicate the process is alive.

    Used by container orchestrators to determine if the container should
    be restarted.
    """
    return LivenessResponse(status="ok")


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Check if the service is ready to receive traffic.",
)
async def readiness() -> ReadinessResponse:
    """
    Readiness probe - checks S3 connectivity.

    Used by container orchestrators to determine if the service
    should receive traffic.
    """
    checks: dict[str, str] = {}

    # Check S3 connectivity by attempting to list a bucket
    try:
        s3_repo = get_s3_repository()
        # Just try to check if any object exists (will return False if none, but won't error)
        await s3_repo.object_exists(
            Settings.default_decomp_bucket, "_health_check_probe"
        )
        checks["s3"] = "ok"
    except Exception as e:
        checks["s3"] = f"error: {type(e).__name__}"

    # Determine overall status
    all_ok = all(v == "ok" for v in checks.values())
    status = "ready" if all_ok else "not_ready"

    return ReadinessResponse(status=status, checks=checks)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Full health check",
    description="Comprehensive health status with version and all checks.",
)
async def health() -> HealthResponse:
    """
    Full health check with version and dependency status.

    Returns detailed information about the service health,
    useful for monitoring and diagnostics.
    """
    # Get readiness checks
    readiness_result = await readiness()

    # Determine overall status
    status = "healthy" if readiness_result.status == "ready" else "unhealthy"

    return HealthResponse(
        status=status,
        version=SERVICE_VERSION,
        timestamp=datetime.now(UTC),
        checks=readiness_result.checks,
    )
