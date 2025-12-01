"""
Custom exceptions for the regras-operativas service.

This module defines a consistent exception hierarchy that maps to HTTP status
codes and provides structured error responses for the API.
"""

from typing import Any


class RegrasOperativasException(Exception):
    """
    Base exception for all regras-operativas service errors.

    Attributes:
        error_code: Machine-readable error code for API responses
        http_status: HTTP status code to return
        message: Human-readable error message
        details: Additional context about the error

    Example:
        >>> raise RegrasOperativasException("Something went wrong", {"key": "value"})
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


class S3OperationError(RegrasOperativasException):
    """
    Raised when an S3 operation fails.

    Examples:
        - Upload failure
        - Permission denied
        - Network timeout

    Example:
        >>> raise S3OperationError(
        ...     "Failed to upload file",
        ...     {"bucket": "my-bucket", "key": "path/to/file"}
        ... )
    """

    error_code = "S3_ERROR"
    http_status = 500


class ArtifactNotFoundError(RegrasOperativasException):
    """
    Raised when a required S3 artifact is not found.

    Examples:
        - deck_processado.zip missing
        - relato file missing

    Example:
        >>> raise ArtifactNotFoundError(
        ...     "Object not found: s3://bucket/key",
        ...     {"bucket": "decomp-bucket", "key": "artifacts/abc/file.zip"}
        ... )
    """

    error_code = "ARTIFACT_NOT_FOUND"
    http_status = 404


class ParseError(RegrasOperativasException):
    """
    Raised when a NEWAVE/DECOMP file cannot be parsed.

    Examples:
        - Invalid file format
        - Missing required sections
        - Encoding issues

    Example:
        >>> raise ParseError(
        ...     "Failed to parse dadger.rv0",
        ...     {"file": "dadger.rv0", "reason": "Invalid format"}
        ... )
    """

    error_code = "PARSE_ERROR"
    http_status = 422


class RuleApplicationError(RegrasOperativasException):
    """
    Raised when reservoir rule application fails.

    Examples:
        - Invalid constraint type
        - Processing logic error
        - Missing required data

    Example:
        >>> raise RuleApplicationError(
        ...     "Failed to apply reservoir rules",
        ...     {"rule": "QDEF", "reason": "Unknown constraint type"}
        ... )
    """

    error_code = "RULE_APPLICATION_ERROR"
    http_status = 500


class ValidationError(RegrasOperativasException):
    """
    Raised when request validation fails beyond Pydantic checks.

    Example:
        >>> raise ValidationError(
        ...     "Invalid execution hash format",
        ...     {"execution_hash": "invalid!", "expected": "alphanumeric"}
        ... )
    """

    error_code = "INVALID_REQUEST"
    http_status = 400


class ZipExtractionError(RegrasOperativasException):
    """
    Raised when zip extraction or creation fails.

    Examples:
        - Corrupted zip file
        - Invalid zip format
        - Compression failure

    Example:
        >>> raise ZipExtractionError(
        ...     "Failed to extract deck_processado.zip",
        ...     {"file": "deck_processado.zip", "reason": "Corrupted archive"}
        ... )
    """

    error_code = "ZIP_ERROR"
    http_status = 500
