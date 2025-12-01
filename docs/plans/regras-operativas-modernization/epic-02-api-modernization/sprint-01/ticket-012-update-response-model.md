# TICKET-012: Update ReservoirRulesResponse Model

> **Epic**: [Epic 02: API Modernization](../../00-epic-overview.md)  
> **Sprint**: [Sprint 01](./00-sprint-overview.md)  
> **Points**: 2  
> **Dependencies**: None

## Context

Update response model to include success status, output S3 key, and structured rules_applied.

## Specification

### File: `app/models/reservoirrulesresponse.py`

```python
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.reservoirgrouprule import ReservoirGroupRule

class ReservoirRulesResponse(BaseModel):
    """
    Response for reservoir rules application.
    
    v2.0: Includes success status and S3 output location.
    """
    success: bool = Field(..., description="Whether rules were applied successfully")
    execution_hash: str = Field(..., description="Execution identifier of destination")
    output_key: str = Field(..., description="S3 key of output zip file")
    rules_applied: List[ReservoirGroupRule] = Field(
        ..., description="Rules that were applied"
    )
    message: Optional[str] = Field(None, description="Summary message")
```

## Acceptance Criteria

- [ ] Response includes `success` boolean
- [ ] Response includes `output_key` (S3 path)
- [ ] Response includes `execution_hash`
- [ ] `rules_applied` contains applied rules
- [ ] Optional `message` for human-readable summary

## Example Response

```json
{
    "success": true,
    "execution_hash": "xyz789",
    "output_key": "ingest/xyz789_regras.zip",
    "rules_applied": [...],
    "message": "Applied 5 reservoir rules"
}
```

## Effort: 2 points
