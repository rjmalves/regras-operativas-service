"""Unit tests for error models."""

from app.models.errors import (
    ErrorDetail,
    ErrorResponse,
    ValidationErrorResponse,
)


class TestErrorDetail:
    """Tests for ErrorDetail model."""

    def test_error_detail_with_field(self):
        """Test ErrorDetail with field."""
        detail = ErrorDetail(field="execution_hash", message="Field required")
        assert detail.field == "execution_hash"
        assert detail.message == "Field required"

    def test_error_detail_without_field(self):
        """Test ErrorDetail without field."""
        detail = ErrorDetail(message="General error")
        assert detail.field is None
        assert detail.message == "General error"

    def test_error_detail_serialization(self):
        """Test ErrorDetail serialization."""
        detail = ErrorDetail(field="bucket", message="Invalid bucket name")
        data = detail.model_dump()
        assert data["field"] == "bucket"
        assert data["message"] == "Invalid bucket name"


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_error_response_basic(self):
        """Test basic ErrorResponse."""
        error = ErrorResponse(
            error_code="ARTIFACT_NOT_FOUND",
            message="Object not found",
        )
        assert error.error_code == "ARTIFACT_NOT_FOUND"
        assert error.message == "Object not found"
        assert error.details is None

    def test_error_response_with_details(self):
        """Test ErrorResponse with details."""
        error = ErrorResponse(
            error_code="S3_ERROR",
            message="Failed to download",
            details={"bucket": "test-bucket", "key": "path/to/file"},
        )
        assert error.details["bucket"] == "test-bucket"
        assert error.details["key"] == "path/to/file"

    def test_error_response_serialization(self):
        """Test ErrorResponse serialization."""
        error = ErrorResponse(
            error_code="PARSE_ERROR",
            message="Failed to parse file",
            details={"file": "dadger.rv0"},
        )
        data = error.model_dump()
        assert data["error_code"] == "PARSE_ERROR"
        assert data["message"] == "Failed to parse file"
        assert data["details"]["file"] == "dadger.rv0"

    def test_error_response_json_output(self):
        """Test ErrorResponse JSON output."""
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="An error occurred",
        )
        json_str = error.model_dump_json()
        assert '"error_code":"INTERNAL_ERROR"' in json_str


class TestValidationErrorResponse:
    """Tests for ValidationErrorResponse model."""

    def test_validation_error_response(self):
        """Test ValidationErrorResponse."""
        error = ValidationErrorResponse(
            details={
                "errors": [
                    ErrorDetail(field="execution_hash", message="Required"),
                    ErrorDetail(field="bucket", message="Invalid format"),
                ]
            }
        )
        assert error.error_code == "VALIDATION_ERROR"
        assert error.message == "Request validation failed"
        assert len(error.details["errors"]) == 2

    def test_validation_error_response_custom_message(self):
        """Test ValidationErrorResponse with custom message."""
        error = ValidationErrorResponse(
            message="Custom validation message",
            details={"errors": []},
        )
        assert error.message == "Custom validation message"

    def test_validation_error_response_serialization(self):
        """Test ValidationErrorResponse serialization."""
        error = ValidationErrorResponse(
            details={
                "errors": [
                    ErrorDetail(field="program", message="Invalid value"),
                ]
            }
        )
        data = error.model_dump()
        assert data["error_code"] == "VALIDATION_ERROR"
        assert len(data["details"]["errors"]) == 1
        assert data["details"]["errors"][0]["field"] == "program"
