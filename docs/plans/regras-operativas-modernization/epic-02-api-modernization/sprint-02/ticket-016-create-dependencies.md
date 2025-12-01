# TICKET-016: Create FastAPI Dependencies

> **Epic**: [Epic 02: API Modernization](../../00-epic-overview.md)  
> **Sprint**: [Sprint 02](./00-sprint-overview.md)  
> **Points**: 2  
> **Dependencies**: [TICKET-002](../../epic-01-s3-integration/sprint-01/ticket-002-implement-s3-repository.md)

## Context

Create FastAPI dependency injection for S3Repository to enable testing and proper lifecycle.

## Specification

### File: `app/internal/dependencies.py`

```python
from app.adapters.s3_repository import S3Repository, get_s3_repository

def get_s3_repo() -> S3Repository:
    """
    FastAPI dependency for S3Repository.
    
    Returns singleton S3Repository instance.
    Can be overridden in tests.
    """
    return get_s3_repository()
```

### Usage in Tests

```python
from fastapi.testclient import TestClient
from app.internal.dependencies import get_s3_repo

def test_with_mock_s3(mock_s3_repo):
    app.dependency_overrides[get_s3_repo] = lambda: mock_s3_repo
    client = TestClient(app)
    # ...
    app.dependency_overrides.clear()
```

## Acceptance Criteria

- [ ] `get_s3_repo` dependency available
- [ ] Returns singleton from s3_repository module
- [ ] Can be overridden for testing

## Remove Deprecated

- Remove `uriParser` dependency (no longer needed)
- Remove base62 related code

## Effort: 2 points
