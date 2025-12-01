# TICKET-010: Create CaseReference Model

> **Epic**: [Epic 02: API Modernization](../../00-epic-overview.md)  
> **Sprint**: [Sprint 01](./00-sprint-overview.md)  
> **Points**: 2  
> **Dependencies**: None  
> **Blocks**: [TICKET-011](./ticket-011-update-request-model.md)

## Context

### Background

The API needs a model to represent references to cases stored in S3. This replaces the base62-encoded filesystem path with explicit bucket and execution_hash fields.

### Current State

Cases are referenced by base62-encoded paths in the `Case` model:
```python
class Case(BaseModel):
    id: str  # base62 encoded path
    program: str
```

## Specification

### File Location

- `app/models/case.py` (MODIFY or CREATE)

### Model Definition

```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class Program(str, Enum):
    """Supported program types."""
    NEWAVE = "NEWAVE"
    DECOMP = "DECOMP"

class CaseReference(BaseModel):
    """
    Reference to a case stored in S3.
    
    Replaces the base62-encoded filesystem path with explicit
    S3 bucket and execution hash.
    
    Attributes:
        bucket: S3 bucket name containing the case artifacts
        execution_hash: Unique identifier for the execution
        program: Program type (NEWAVE or DECOMP)
        output_prefix: S3 prefix for output files (default: "ingest")
    
    Example:
        {
            "bucket": "decomp-bucket",
            "execution_hash": "abc123def456",
            "program": "DECOMP",
            "output_prefix": "ingest"
        }
    """
    bucket: str = Field(
        ...,
        description="S3 bucket name",
        examples=["decomp-bucket", "newave-bucket"]
    )
    execution_hash: str = Field(
        ...,
        description="Unique execution identifier",
        min_length=1,
        examples=["abc123def456"]
    )
    program: Program = Field(
        ...,
        description="Program type"
    )
    output_prefix: str = Field(
        default="ingest",
        description="S3 prefix for output files"
    )
    
    @property
    def input_deck_key(self) -> str:
        """S3 key for input deck zip."""
        return f"artifacts/{self.execution_hash}/entradas/deck_processado.zip"
    
    @property
    def output_key(self, suffix: str = "_regras.zip") -> str:
        """S3 key for output zip."""
        return f"{self.output_prefix}/{self.execution_hash}{suffix}"
```

### Validation

- `bucket`: Non-empty string
- `execution_hash`: Non-empty string, min length 1
- `program`: Must be "NEWAVE" or "DECOMP"
- `output_prefix`: Default "ingest", can be overridden

## Acceptance Criteria

- [ ] Given valid JSON, when parsed to CaseReference, then all fields populated
- [ ] Given invalid program, when parsed, then validation error raised
- [ ] Given empty execution_hash, when parsed, then validation error raised
- [ ] `input_deck_key` property returns correct S3 key pattern
- [ ] Default `output_prefix` is "ingest"
- [ ] Model serializes to JSON correctly

## Implementation Guide

### Suggested Approach

1. Update `app/models/case.py`
2. Keep existing `Case` class (for backward compatibility comment)
3. Add `CaseReference` class
4. Ensure `Program` enum exists (may already be in `program.py`)
5. Write unit tests

### Key Files to Read

- `app/models/case.py` - Current implementation
- `app/models/program.py` - Program enum (if exists)

### Pydantic v2 Notes

```python
from pydantic import BaseModel, Field

# Field validation
execution_hash: str = Field(..., min_length=1)

# Examples for OpenAPI docs
bucket: str = Field(..., examples=["decomp-bucket"])
```

## Testing Requirements

### Unit Tests

Create `tests/unit/test_models_case.py`:

```python
import pytest
from pydantic import ValidationError
from app.models.case import CaseReference, Program

def test_case_reference_valid():
    ref = CaseReference(
        bucket="decomp-bucket",
        execution_hash="abc123",
        program=Program.DECOMP
    )
    
    assert ref.bucket == "decomp-bucket"
    assert ref.execution_hash == "abc123"
    assert ref.program == Program.DECOMP
    assert ref.output_prefix == "ingest"

def test_case_reference_input_key():
    ref = CaseReference(
        bucket="test", execution_hash="xyz", program=Program.DECOMP
    )
    
    assert ref.input_deck_key == "artifacts/xyz/entradas/deck_processado.zip"

def test_case_reference_invalid_program():
    with pytest.raises(ValidationError):
        CaseReference(
            bucket="test",
            execution_hash="abc",
            program="INVALID"
        )

def test_case_reference_empty_hash():
    with pytest.raises(ValidationError):
        CaseReference(
            bucket="test",
            execution_hash="",
            program=Program.DECOMP
        )

def test_case_reference_serialization():
    ref = CaseReference(
        bucket="test",
        execution_hash="abc",
        program=Program.DECOMP
    )
    
    data = ref.model_dump()
    assert data["bucket"] == "test"
    assert data["program"] == "DECOMP"
```

## Definition of Done

- [ ] `CaseReference` model implemented
- [ ] `Program` enum available
- [ ] Pydantic validation works
- [ ] Properties return correct S3 keys
- [ ] Unit tests passing
- [ ] Docstrings complete

## Effort Estimate

**Points**: 2  
**Confidence**: High  
**Rationale**: Simple Pydantic model
