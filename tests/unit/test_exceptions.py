"""Unit tests for the exception hierarchy."""

import pytest
from app.internal.exceptions import (
    RegrasOperativasException,
    S3OperationError,
    ArtifactNotFoundError,
    ParseError,
    RuleApplicationError,
    ValidationError,
    ZipExtractionError,
)


class TestRegrasOperativasException:
    """Tests for the base exception class."""

    def test_to_dict_basic(self):
        """Test to_dict with minimal parameters."""
        exc = RegrasOperativasException("Test error")
        result = exc.to_dict()
        assert result["error_code"] == "INTERNAL_ERROR"
        assert result["message"] == "Test error"
        assert result["details"] is None

    def test_to_dict_with_details(self):
        """Test to_dict with details."""
        exc = RegrasOperativasException("Test error", {"key": "value"})
        result = exc.to_dict()
        assert result["error_code"] == "INTERNAL_ERROR"
        assert result["message"] == "Test error"
        assert result["details"] == {"key": "value"}

    def test_default_http_status(self):
        """Test default http_status is 500."""
        exc = RegrasOperativasException("Test error")
        assert exc.http_status == 500

    def test_str_representation(self):
        """Test string representation."""
        exc = RegrasOperativasException("Test error message")
        assert str(exc) == "Test error message"


class TestS3OperationError:
    """Tests for S3OperationError."""

    def test_error_code(self):
        """Test error code."""
        exc = S3OperationError("Upload failed")
        assert exc.error_code == "S3_ERROR"

    def test_http_status(self):
        """Test http status."""
        exc = S3OperationError("Upload failed")
        assert exc.http_status == 500

    def test_to_dict_with_details(self):
        """Test to_dict with S3 details."""
        exc = S3OperationError(
            "Upload failed",
            {"bucket": "test-bucket", "key": "path/file.zip"},
        )
        result = exc.to_dict()
        assert result["error_code"] == "S3_ERROR"
        assert result["details"]["bucket"] == "test-bucket"
        assert result["details"]["key"] == "path/file.zip"


class TestArtifactNotFoundError:
    """Tests for ArtifactNotFoundError."""

    def test_error_code(self):
        """Test error code."""
        exc = ArtifactNotFoundError("Not found")
        assert exc.error_code == "ARTIFACT_NOT_FOUND"

    def test_http_status(self):
        """Test http status is 404."""
        exc = ArtifactNotFoundError("Not found")
        assert exc.http_status == 404

    def test_to_dict(self):
        """Test to_dict output."""
        exc = ArtifactNotFoundError(
            "Object not found: s3://bucket/key",
            {"bucket": "decomp-bucket", "key": "artifacts/abc123/deck.zip"},
        )
        result = exc.to_dict()
        assert result["error_code"] == "ARTIFACT_NOT_FOUND"
        assert result["message"] == "Object not found: s3://bucket/key"


class TestParseError:
    """Tests for ParseError."""

    def test_error_code(self):
        """Test error code."""
        exc = ParseError("Parse failed")
        assert exc.error_code == "PARSE_ERROR"

    def test_http_status(self):
        """Test http status is 422."""
        exc = ParseError("Parse failed")
        assert exc.http_status == 422

    def test_to_dict_with_file_details(self):
        """Test to_dict with file parsing details."""
        exc = ParseError(
            "Failed to parse dadger.rv0",
            {"file": "dadger.rv0", "reason": "Invalid format"},
        )
        result = exc.to_dict()
        assert result["details"]["file"] == "dadger.rv0"


class TestRuleApplicationError:
    """Tests for RuleApplicationError."""

    def test_error_code(self):
        """Test error code."""
        exc = RuleApplicationError("Rule application failed")
        assert exc.error_code == "RULE_APPLICATION_ERROR"

    def test_http_status(self):
        """Test http status is 500."""
        exc = RuleApplicationError("Rule application failed")
        assert exc.http_status == 500

    def test_to_dict_with_rule_details(self):
        """Test to_dict with rule details."""
        exc = RuleApplicationError(
            "Failed to apply reservoir rules",
            {"rule": "QDEF", "reason": "Unknown constraint type"},
        )
        result = exc.to_dict()
        assert result["details"]["rule"] == "QDEF"


class TestValidationError:
    """Tests for ValidationError."""

    def test_error_code(self):
        """Test error code."""
        exc = ValidationError("Invalid input")
        assert exc.error_code == "INVALID_REQUEST"

    def test_http_status(self):
        """Test http status is 400."""
        exc = ValidationError("Invalid input")
        assert exc.http_status == 400


class TestZipExtractionError:
    """Tests for ZipExtractionError."""

    def test_error_code(self):
        """Test error code."""
        exc = ZipExtractionError("Extraction failed")
        assert exc.error_code == "ZIP_ERROR"

    def test_http_status(self):
        """Test http status is 500."""
        exc = ZipExtractionError("Extraction failed")
        assert exc.http_status == 500

    def test_to_dict_with_details(self):
        """Test to_dict with zip details."""
        exc = ZipExtractionError(
            "Failed to extract deck_processado.zip",
            {"file": "deck_processado.zip", "reason": "Corrupted archive"},
        )
        result = exc.to_dict()
        assert result["details"]["file"] == "deck_processado.zip"


class TestExceptionInheritance:
    """Tests to verify all exceptions inherit from base class."""

    @pytest.mark.parametrize(
        "exc_class",
        [
            S3OperationError,
            ArtifactNotFoundError,
            ParseError,
            RuleApplicationError,
            ValidationError,
            ZipExtractionError,
        ],
    )
    def test_inherits_from_base(self, exc_class):
        """Test all exceptions inherit from RegrasOperativasException."""
        exc = exc_class("Test")
        assert isinstance(exc, RegrasOperativasException)

    @pytest.mark.parametrize(
        "exc_class",
        [
            S3OperationError,
            ArtifactNotFoundError,
            ParseError,
            RuleApplicationError,
            ValidationError,
            ZipExtractionError,
        ],
    )
    def test_has_to_dict_method(self, exc_class):
        """Test all exceptions have to_dict method."""
        exc = exc_class("Test")
        result = exc.to_dict()
        assert "error_code" in result
        assert "message" in result
        assert "details" in result
