# TICKET-013: Create Error Response Models

> **Epic**: [Epic 02: API Modernization](../../00-epic-overview.md)  
> **Sprint**: [Sprint 01](./00-sprint-overview.md)  
> **Points**: 1  
> **Dependencies**: None

## Context

Create Pydantic models for structured error responses used in OpenAPI documentation.

## Specification

### File: `app/models/errors.py`

```python
from typing import Any, Optional
from pydantic import BaseModel, Field

class ErrorResponse(BaseModel):
    """
    Structured error response for API errors.
    
    Used for consistent error formatting across all endpoints.
    """
    error_code: str = Field(
        ...,
        description="Machine-readable error code",
        examples=["ARTIFACT_NOT_FOUND", "PARSE_ERROR"]
    )
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    details: Optional[dict[str, Any]] = Field(
        None,
        description="Additional error context"
    )

class ErrorCodes:
    """Error code constants."""
    INVALID_REQUEST = "INVALID_REQUEST"
    ARTIFACT_NOT_FOUND = "ARTIFACT_NOT_FOUND"
    PARSE_ERROR = "PARSE_ERROR"
    S3_ERROR = "S3_ERROR"
    RULE_APPLICATION_ERROR = "RULE_APPLICATION_ERROR"
```

## Usage in Router

```python
from app.models.errors import ErrorResponse

@router.post(
    "/",
    responses={
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        422: {"model": ErrorResponse, "description": "Parse error"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    }
)
```

## Acceptance Criteria

- [ ] `ErrorResponse` model defined with all fields
- [ ] Error codes constants available
- [ ] Model serializes to expected JSON format

## Effort: 1 point
