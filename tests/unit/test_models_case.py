"""Unit tests for case models."""

import pytest
from pydantic import ValidationError

from app.models.case import Case, CaseReference
from app.models.program import Program


class TestCase:
    """Tests for legacy Case model."""

    def test_case_valid(self):
        """Test creating a valid Case."""
        case = Case(id="abc123", program=Program.DECOMP)
        assert case.id == "abc123"
        assert case.program == Program.DECOMP

    def test_case_serialization(self):
        """Test Case serialization."""
        case = Case(id="abc123", program=Program.NEWAVE)
        data = case.model_dump(mode="json")
        assert data["id"] == "abc123"
        assert data["program"] == "NEWAVE"


class TestCaseReference:
    """Tests for CaseReference model."""

    def test_case_reference_valid(self):
        """Test creating a valid CaseReference."""
        ref = CaseReference(
            bucket="decomp-bucket",
            execution_hash="abc123def456",
            program=Program.DECOMP,
        )
        assert ref.bucket == "decomp-bucket"
        assert ref.execution_hash == "abc123def456"
        assert ref.program == Program.DECOMP
        assert ref.output_prefix == "ingest"

    def test_case_reference_with_custom_output_prefix(self):
        """Test CaseReference with custom output prefix."""
        ref = CaseReference(
            bucket="newave-bucket",
            execution_hash="xyz789",
            program=Program.NEWAVE,
            output_prefix="custom",
        )
        assert ref.output_prefix == "custom"

    def test_case_reference_input_deck_key(self):
        """Test input_deck_key property."""
        ref = CaseReference(
            bucket="test",
            execution_hash="xyz123",
            program=Program.DECOMP,
        )
        assert ref.input_deck_key == "artifacts/xyz123/entradas/deck_processado.zip"

    def test_case_reference_get_output_key(self):
        """Test get_output_key method."""
        ref = CaseReference(
            bucket="test",
            execution_hash="abc123",
            program=Program.NEWAVE,
        )
        assert ref.get_output_key() == "ingest/abc123_regras.zip"

    def test_case_reference_get_output_key_custom_suffix(self):
        """Test get_output_key with custom suffix."""
        ref = CaseReference(
            bucket="test",
            execution_hash="abc123",
            program=Program.NEWAVE,
            output_prefix="output",
        )
        assert ref.get_output_key("_modified.zip") == "output/abc123_modified.zip"

    def test_case_reference_get_relato_key(self):
        """Test get_relato_key method."""
        ref = CaseReference(
            bucket="decomp-bucket",
            execution_hash="abc123",
            program=Program.DECOMP,
        )
        assert ref.get_relato_key("rv0") == "artifacts/abc123/saidas/relato.rv0"

    def test_case_reference_invalid_program(self):
        """Test validation error for invalid program."""
        with pytest.raises(ValidationError) as exc_info:
            CaseReference(
                bucket="test",
                execution_hash="abc",
                program="INVALID",
            )
        assert "program" in str(exc_info.value)

    def test_case_reference_empty_hash(self):
        """Test validation error for empty execution_hash."""
        with pytest.raises(ValidationError) as exc_info:
            CaseReference(
                bucket="test",
                execution_hash="",
                program=Program.DECOMP,
            )
        assert "execution_hash" in str(exc_info.value)

    def test_case_reference_missing_bucket(self):
        """Test validation error for missing bucket."""
        with pytest.raises(ValidationError):
            CaseReference(
                execution_hash="abc123",
                program=Program.DECOMP,
            )

    def test_case_reference_serialization(self):
        """Test CaseReference serialization."""
        ref = CaseReference(
            bucket="test-bucket",
            execution_hash="abc123",
            program=Program.DECOMP,
            output_prefix="custom",
        )
        data = ref.model_dump(mode="json")
        assert data["bucket"] == "test-bucket"
        assert data["execution_hash"] == "abc123"
        assert data["program"] == "DECOMP"
        assert data["output_prefix"] == "custom"

    def test_case_reference_deserialization(self):
        """Test CaseReference deserialization from dict."""
        data = {
            "bucket": "newave-bucket",
            "execution_hash": "xyz789",
            "program": "NEWAVE",
        }
        ref = CaseReference.model_validate(data)
        assert ref.bucket == "newave-bucket"
        assert ref.program == Program.NEWAVE

    def test_case_reference_json_round_trip(self):
        """Test JSON serialization round trip."""
        ref = CaseReference(
            bucket="test",
            execution_hash="abc",
            program=Program.DECOMP,
        )
        json_str = ref.model_dump_json()
        ref2 = CaseReference.model_validate_json(json_str)
        assert ref == ref2
