# TICKET-001: Create Exception Hierarchy

> **Epic**: [Epic 01: S3 Integration Layer](../../00-epic-overview.md)  
> **Sprint**: [Sprint 01](./00-sprint-overview.md)  
> **Points**: 2  
> **Dependencies**: None  
> **Blocks**: [TICKET-002](./ticket-002-implement-s3-repository.md)

## Context

### Background

The service needs a consistent exception hierarchy that maps to HTTP status codes and provides structured error responses for the API. This enables proper error handling throughout the S3 integration layer and aligns with the flexibilizador-service pattern.

### Current State

The current codebase uses `HTTPResponse` objects for error handling, which couples error handling to HTTP. We need domain-specific exceptions that can be caught and converted to HTTP responses at the router level.

## Specification

### File Location

- `app/internal/exceptions.py` (CREATE)

### Exception Hierarchy

```python
class RegrasOperativasException(Exception):
    """Base exception for all service errors."""
    error_code: str = "INTERNAL_ERROR"
    http_status: int = 500

class S3OperationError(RegrasOperativasException):
    """S3 operation failed (upload, download, list)."""
    error_code = "S3_ERROR"
    http_status = 500

class ArtifactNotFoundError(RegrasOperativasException):
    """Required S3 artifact not found."""
    error_code = "ARTIFACT_NOT_FOUND"
    http_status = 404

class ParseError(RegrasOperativasException):
    """Failed to parse NEWAVE/DECOMP files."""
    error_code = "PARSE_ERROR"
    http_status = 422

class RuleApplicationError(RegrasOperativasException):
    """Failed to apply reservoir rules."""
    error_code = "RULE_APPLICATION_ERROR"
    http_status = 500

class ValidationError(RegrasOperativasException):
    """Request validation failed."""
    error_code = "INVALID_REQUEST"
    http_status = 400

class ZipExtractionError(RegrasOperativasException):
    """Failed to extract or create zip file."""
    error_code = "ZIP_ERROR"
    http_status = 500
```

### Base Exception Implementation

```python
from typing import Any

class RegrasOperativasException(Exception):
    """
    Base exception for all regras-operativas service errors.
    
    Attributes:
        error_code: Machine-readable error code for API responses
        http_status: HTTP status code to return
        message: Human-readable error message
        details: Additional context about the error
    """
    error_code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to API response format."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details if self.details else None,
        }
```

## Acceptance Criteria

- [ ] Given a `RegrasOperativasException`, when `to_dict()` is called, then it returns a dict with `error_code`, `message`, and `details`
- [ ] Given an `ArtifactNotFoundError`, when raised, then it has `http_status = 404` and `error_code = "ARTIFACT_NOT_FOUND"`
- [ ] Given an `S3OperationError` with details, when `to_dict()` is called, then details are included in the response
- [ ] All exception classes inherit from `RegrasOperativasException`
- [ ] All exception classes have appropriate docstrings

## Implementation Guide

### Suggested Approach

1. Create `app/internal/exceptions.py`
2. Copy structure from `flexibilizador-service/app/internal/exceptions.py`
3. Rename base class from `FlexibilizadorException` to `RegrasOperativasException`
4. Add `ZipExtractionError` and `RuleApplicationError` (specific to this service)
5. Write unit tests

### Reference Implementation

Copy from: `/home/rogerio/git/flexibilizador-service/app/internal/exceptions.py`

Changes needed:
- Rename `FlexibilizadorException` → `RegrasOperativasException`
- Rename `FlexibilizationError` → `RuleApplicationError`
- Remove `NoInfeasibilitiesError` (not applicable)
- Add `ZipExtractionError`

### Key Files to Read

- `/home/rogerio/git/flexibilizador-service/app/internal/exceptions.py` - Reference implementation
- `app/internal/httpresponse.py` - Current error handling (to be replaced)

### Patterns to Follow

- Use class attributes for `error_code` and `http_status`
- Allow `details` dict for additional context
- Implement `to_dict()` for API response conversion

### Pitfalls to Avoid

- ⚠️ Don't forget to make all exceptions inherit from the base class
- ⚠️ Don't use generic `Exception` - always use specific subclass
- ⚠️ Don't put HTTP-specific logic in exceptions (just the status code)

## Testing Requirements

### Unit Tests

Create `tests/unit/test_exceptions.py`:

```python
import pytest
from app.internal.exceptions import (
    RegrasOperativasException,
    ArtifactNotFoundError,
    S3OperationError,
)

def test_base_exception_to_dict():
    exc = RegrasOperativasException("Test error", {"key": "value"})
    result = exc.to_dict()
    assert result["error_code"] == "INTERNAL_ERROR"
    assert result["message"] == "Test error"
    assert result["details"] == {"key": "value"}

def test_artifact_not_found_status():
    exc = ArtifactNotFoundError("Not found")
    assert exc.http_status == 404
    assert exc.error_code == "ARTIFACT_NOT_FOUND"

def test_s3_operation_error_with_details():
    exc = S3OperationError(
        "Upload failed",
        {"bucket": "test", "key": "path/file.zip"}
    )
    result = exc.to_dict()
    assert result["details"]["bucket"] == "test"
```

## Definition of Done

- [ ] `app/internal/exceptions.py` created
- [ ] All 7 exception classes implemented
- [ ] Unit tests written and passing
- [ ] Docstrings on all classes
- [ ] No import errors when module is loaded

## Effort Estimate

**Points**: 2  
**Confidence**: High  
**Rationale**: Direct copy from flexibilizador with minor renames
