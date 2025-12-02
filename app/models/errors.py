"""
Error response models for API responses.

This module provides Pydantic models for structured error responses
that map to the custom exception hierarchy.
"""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """
    Detail about a specific error.

    Attributes:
        field: Field name that caused the error (for validation errors)
        message: Human-readable error message
    """

    field: str | None = Field(default=None, description="Field name (for validation)")
    message: str = Field(..., description="Error message")


class ErrorResponse(BaseModel):
    """
    Standard error response format.

    All API errors return this format for consistency.

    Attributes:
        error_code: Machine-readable error code
        message: Human-readable error message
        details: Additional error context (optional)

    Example:
        {
            "error_code": "ARTIFACT_NOT_FOUND",
            "message": "Object not found: s3://bucket/key",
            "details": {"bucket": "decomp-bucket", "key": "artifacts/abc/file.zip"}
        }
    """

    error_code: str = Field(
        ...,
        description="Machine-readable error code",
        examples=["ARTIFACT_NOT_FOUND", "VALIDATION_ERROR", "S3_ERROR"],
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional error context",
    )


class ValidationErrorResponse(BaseModel):
    """
    Validation error response with field-level details.

    Used for Pydantic validation errors.

    Attributes:
        error_code: Always "VALIDATION_ERROR"
        message: General validation message
        details: Contains list of field errors

    Example:
        {
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {
                "errors": [
                    {"field": "execution_hash", "message": "String should have at least 1 character"}
                ]
            }
        }
    """

    error_code: str = Field(
        default="VALIDATION_ERROR",
        description="Error code",
    )
    message: str = Field(
        default="Request validation failed",
        description="Error message",
    )
    details: dict[str, list[ErrorDetail]] = Field(
        ...,
        description="Validation error details",
    )
