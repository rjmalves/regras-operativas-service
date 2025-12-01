"""Unit tests for request/response models."""

import pytest
from pydantic import ValidationError

from app.models.case import CaseReference
from app.models.program import Program
from app.models.reservoirrule import ReservoirRule
from app.models.reservoirgrouprule import ReservoirGroupRule
from app.models.reservoirrulesrequest import (
    ReservoirRulesRequest,
    ReservoirRulesRequestV2,
)
from app.models.reservoirrulesresponse import (
    ReservoirRulesResponse,
    ReservoirRulesResponseV2,
)


class TestReservoirRulesRequestV2:
    """Tests for ReservoirRulesRequestV2 model."""

    @pytest.fixture
    def sample_rule(self):
        """Create a sample rule."""
        return ReservoirRule(
            reservoirCode=156,
            uheCode=156,
            constraintType="QDEF",
            month=1,
            minVolume=0.0,
            maxVolume=30.0,
            minLimit=100.0,
            maxLimit=99999.0,
            frequency="M",
            label="Restricao",
        )

    @pytest.fixture
    def sample_source(self):
        """Create a sample source reference."""
        return CaseReference(
            bucket="decomp-bucket",
            execution_hash="source123",
            program=Program.DECOMP,
        )

    @pytest.fixture
    def sample_destination(self):
        """Create a sample destination reference."""
        return CaseReference(
            bucket="newave-bucket",
            execution_hash="dest456",
            program=Program.NEWAVE,
            output_prefix="ingest",
        )

    def test_request_v2_valid(self, sample_source, sample_destination, sample_rule):
        """Test creating a valid V2 request."""
        request = ReservoirRulesRequestV2(
            sources=[sample_source],
            destination=sample_destination,
            rules=[sample_rule],
        )
        assert len(request.sources) == 1
        assert request.destination.bucket == "newave-bucket"
        assert len(request.rules) == 1

    def test_request_v2_multiple_sources(self, sample_destination, sample_rule):
        """Test V2 request with multiple sources."""
        sources = [
            CaseReference(bucket="decomp-bucket", execution_hash=f"src{i}", program=Program.DECOMP)
            for i in range(3)
        ]
        request = ReservoirRulesRequestV2(
            sources=sources,
            destination=sample_destination,
            rules=[sample_rule],
        )
        assert len(request.sources) == 3

    def test_request_v2_empty_sources(self, sample_destination, sample_rule):
        """Test V2 request fails with empty sources."""
        with pytest.raises(ValidationError) as exc_info:
            ReservoirRulesRequestV2(
                sources=[],
                destination=sample_destination,
                rules=[sample_rule],
            )
        assert "sources" in str(exc_info.value)

    def test_request_v2_serialization(self, sample_source, sample_destination, sample_rule):
        """Test V2 request serialization."""
        request = ReservoirRulesRequestV2(
            sources=[sample_source],
            destination=sample_destination,
            rules=[sample_rule],
        )
        data = request.model_dump()
        
        assert data["sources"][0]["bucket"] == "decomp-bucket"
        assert data["destination"]["execution_hash"] == "dest456"
        assert data["rules"][0]["constraintType"] == "QDEF"

    def test_request_v2_json_deserialization(self):
        """Test V2 request JSON deserialization."""
        json_data = {
            "sources": [
                {
                    "bucket": "decomp-bucket",
                    "execution_hash": "abc123",
                    "program": "DECOMP",
                }
            ],
            "destination": {
                "bucket": "newave-bucket",
                "execution_hash": "xyz789",
                "program": "NEWAVE",
                "output_prefix": "custom",
            },
            "rules": [
                {
                    "reservoirCode": 100,
                    "uheCode": 100,
                    "constraintType": "QTUR",
                    "month": 2,
                    "minVolume": 10.0,
                    "maxVolume": 50.0,
                    "minLimit": None,
                    "maxLimit": None,
                    "frequency": "D",
                    "label": None,
                }
            ],
        }
        request = ReservoirRulesRequestV2.model_validate(json_data)
        
        assert request.sources[0].program == Program.DECOMP
        assert request.destination.output_prefix == "custom"
        assert request.rules[0].constraintType == "QTUR"


class TestReservoirRulesResponseV2:
    """Tests for ReservoirRulesResponseV2 model."""

    @pytest.fixture
    def sample_group_rule(self):
        """Create a sample group rule."""
        return ReservoirGroupRule(
            reservoirCodes=[156, 157],
            uheCode=156,
            constraintType="QDEF",
            month=1,
            minVolume=0.0,
            maxVolume=30.0,
            minLimit=100.0,
            maxLimit=99999.0,
            frequency="M",
            label="Restricao",
        )

    def test_response_v2_success(self, sample_group_rule):
        """Test successful V2 response."""
        response = ReservoirRulesResponseV2(
            success=True,
            execution_hash="xyz789",
            output_key="ingest/xyz789_regras.zip",
            rules_applied=[sample_group_rule],
            message="Applied 1 reservoir rule",
        )
        assert response.success is True
        assert response.execution_hash == "xyz789"
        assert response.output_key == "ingest/xyz789_regras.zip"
        assert len(response.rules_applied) == 1

    def test_response_v2_failure(self):
        """Test failed V2 response."""
        response = ReservoirRulesResponseV2(
            success=False,
            execution_hash="xyz789",
            output_key="",
            rules_applied=[],
            message="No rules were applied",
        )
        assert response.success is False
        assert response.rules_applied == []

    def test_response_v2_serialization(self, sample_group_rule):
        """Test V2 response serialization."""
        response = ReservoirRulesResponseV2(
            success=True,
            execution_hash="abc123",
            output_key="ingest/abc123_regras.zip",
            rules_applied=[sample_group_rule],
            message="Success",
        )
        data = response.model_dump()
        
        assert data["success"] is True
        assert data["output_key"] == "ingest/abc123_regras.zip"
        assert len(data["rules_applied"]) == 1
        assert data["rules_applied"][0]["reservoirCodes"] == [156, 157]

    def test_response_v2_json_output(self, sample_group_rule):
        """Test V2 response JSON output."""
        response = ReservoirRulesResponseV2(
            success=True,
            execution_hash="test",
            output_key="ingest/test_regras.zip",
            rules_applied=[sample_group_rule],
            message="Done",
        )
        json_str = response.model_dump_json()
        
        assert '"success":true' in json_str
        assert '"output_key":"ingest/test_regras.zip"' in json_str


class TestLegacyModels:
    """Tests to ensure legacy models still work."""

    def test_legacy_request_still_works(self):
        """Test that legacy ReservoirRulesRequest still works."""
        from app.models.case import Case
        
        request = ReservoirRulesRequest(
            sources=[Case(id="base62encoded", program=Program.DECOMP)],
            destination=Case(id="anotherbase62", program=Program.NEWAVE),
            rules=[
                ReservoirRule(
                    reservoirCode=1,
                    uheCode=1,
                    constraintType="QDEF",
                    month=1,
                    minVolume=0.0,
                    maxVolume=100.0,
                    minLimit=0.0,
                    maxLimit=1000.0,
                    frequency="M",
                    label=None,
                )
            ],
        )
        assert len(request.sources) == 1
        assert request.destination.id == "anotherbase62"

    def test_legacy_response_still_works(self):
        """Test that legacy ReservoirRulesResponse still works."""
        response = ReservoirRulesResponse(
            result=[
                ReservoirGroupRule(
                    reservoirCodes=[1, 2],
                    uheCode=1,
                    constraintType="QDEF",
                    month=1,
                    minVolume=0.0,
                    maxVolume=100.0,
                    minLimit=0.0,
                    maxLimit=1000.0,
                    frequency="M",
                    label=None,
                )
            ]
        )
        assert len(response.result) == 1
