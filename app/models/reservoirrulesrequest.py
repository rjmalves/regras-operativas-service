"""
Request models for reservoir rules API.

This module provides request models supporting both legacy (base62)
and modern (S3) case references.
"""

from pydantic import BaseModel, Field
from typing import List

from app.models.case import Case, CaseReference
from app.models.reservoirrule import ReservoirRule


class ReservoirRulesRequest(BaseModel):
    """
    Legacy request format using base62-encoded paths.
    
    Deprecated: Use ReservoirRulesRequestV2 for new integrations.
    """
    sources: List[Case]
    destination: Case
    rules: List[ReservoirRule]


class ReservoirRulesRequestV2(BaseModel):
    """
    Modern request format using S3 references.
    
    Request body for applying reservoir rules to a case stored in S3.
    
    Attributes:
        sources: List of source cases for reservoir storage prospection
        destination: Destination case to apply rules to
        rules: List of reservoir rules to apply
    
    Example:
        {
            "sources": [
                {
                    "bucket": "decomp-bucket",
                    "execution_hash": "abc123",
                    "program": "DECOMP"
                }
            ],
            "destination": {
                "bucket": "newave-bucket",
                "execution_hash": "xyz789",
                "program": "NEWAVE",
                "output_prefix": "ingest"
            },
            "rules": [
                {
                    "reservoirCode": 156,
                    "uheCode": 156,
                    "constraintType": "QDEF",
                    "month": 1,
                    "minVolume": 0.0,
                    "maxVolume": 30.0,
                    "minLimit": 100.0,
                    "maxLimit": 99999.0,
                    "frequency": "M",
                    "label": "Restricao"
                }
            ]
        }
    """
    sources: List[CaseReference] = Field(
        ...,
        description="Source cases for reservoir storage prospection",
        min_length=1,
    )
    destination: CaseReference = Field(
        ...,
        description="Destination case to modify",
    )
    rules: List[ReservoirRule] = Field(
        ...,
        description="Reservoir rules to apply",
    )
