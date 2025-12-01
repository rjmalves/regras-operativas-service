"""
Response models for reservoir rules API.

This module provides response models for rule application results.
"""

from pydantic import BaseModel, Field
from typing import List

from app.models.reservoirgrouprule import ReservoirGroupRule


class ReservoirRulesResponse(BaseModel):
    """
    Legacy response format with just the result list.
    
    Deprecated: Use ReservoirRulesResponseV2 for new integrations.
    """
    result: List[ReservoirGroupRule]


class ReservoirRulesResponseV2(BaseModel):
    """
    Modern response format with S3 output information.
    
    Response after applying reservoir rules to a case.
    
    Attributes:
        success: Whether the operation succeeded
        execution_hash: Hash of the destination case
        output_key: S3 key where the modified deck was uploaded
        rules_applied: List of rules that were applied
        message: Human-readable status message
    
    Example:
        {
            "success": true,
            "execution_hash": "xyz789",
            "output_key": "ingest/xyz789_regras.zip",
            "rules_applied": [...],
            "message": "Applied 5 reservoir rules"
        }
    """
    success: bool = Field(
        ...,
        description="Whether the operation succeeded",
    )
    execution_hash: str = Field(
        ...,
        description="Execution hash of the destination case",
    )
    output_key: str = Field(
        ...,
        description="S3 key of the output file",
        examples=["ingest/xyz789_regras.zip"],
    )
    rules_applied: List[ReservoirGroupRule] = Field(
        ...,
        description="Rules that were applied",
    )
    message: str = Field(
        ...,
        description="Human-readable status message",
        examples=["Applied 5 reservoir rules"],
    )
