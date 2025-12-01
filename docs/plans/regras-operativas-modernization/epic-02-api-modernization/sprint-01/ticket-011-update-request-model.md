# TICKET-011: Update ReservoirRulesRequest Model

> **Epic**: [Epic 02: API Modernization](../../00-epic-overview.md)  
> **Sprint**: [Sprint 01](./00-sprint-overview.md)  
> **Points**: 2  
> **Dependencies**: [TICKET-010](./ticket-010-create-case-reference-model.md)

## Context

Update the request model to use `CaseReference` instead of base62-encoded `id` fields.

## Specification

### File: `app/models/reservoirrulesrequest.py`

```python
from typing import List
from pydantic import BaseModel, Field
from app.models.case import CaseReference
from app.models.reservoirrule import ReservoirRule

class ReservoirRulesRequest(BaseModel):
    """
    Request for applying reservoir operation rules.
    
    v2.0: Uses S3 bucket + execution_hash instead of base62 paths.
    """
    sources: List[CaseReference] = Field(
        ...,
        description="Source cases for prospection (reservoir storage)",
        min_length=1
    )
    destination: CaseReference = Field(
        ...,
        description="Destination case to modify"
    )
    rules: List[ReservoirRule] = Field(
        ...,
        description="Reservoir rules to apply",
        min_length=1
    )
```

## Acceptance Criteria

- [ ] `sources` accepts list of `CaseReference` objects
- [ ] `destination` accepts single `CaseReference`
- [ ] `rules` unchanged (list of `ReservoirRule`)
- [ ] Validation requires at least one source and one rule
- [ ] Old `id` field removed

## Testing

```python
def test_request_with_s3_references():
    request = ReservoirRulesRequest(
        sources=[CaseReference(bucket="decomp-bucket", execution_hash="src1", program="DECOMP")],
        destination=CaseReference(bucket="newave-bucket", execution_hash="dst1", program="NEWAVE"),
        rules=[ReservoirRule(...)]
    )
    assert len(request.sources) == 1
```

## Effort: 2 points
