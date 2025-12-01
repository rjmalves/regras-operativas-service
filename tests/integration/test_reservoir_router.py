"""Integration tests for reservoir router endpoints."""

import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture
def app():
    """Create test application."""
    return create_app(debug=True)


@pytest.fixture
def client(app):
    """Create test client."""
    with TestClient(app) as client:
        yield client


class TestReservoirV1Endpoint:
    """Tests for POST /reservoir/ (V1 legacy endpoint)."""

    def test_v1_endpoint_exists(self, client):
        """Test V1 endpoint exists and requires body."""
        response = client.post("/reservoir/")
        # Should fail validation, not 404
        assert response.status_code == 422

    def test_v1_endpoint_deprecated_in_openapi(self, client):
        """Test V1 endpoint is marked deprecated in OpenAPI."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        openapi = response.json()
        
        # Find the /reservoir/ path
        reservoir_path = openapi["paths"].get("/reservoir/")
        assert reservoir_path is not None
        
        # Check deprecated flag on POST
        post_op = reservoir_path.get("post", {})
        assert post_op.get("deprecated") is True

    def test_v1_requires_sources(self, client):
        """Test V1 endpoint requires sources in request."""
        response = client.post("/reservoir/", json={
            "destination": {"id": "test", "program": "NEWAVE"},
            "rules": []
        })
        assert response.status_code == 422

    def test_v1_requires_destination(self, client):
        """Test V1 endpoint requires destination in request."""
        response = client.post("/reservoir/", json={
            "sources": [{"id": "test", "program": "DECOMP"}],
            "rules": []
        })
        assert response.status_code == 422


class TestReservoirV2Endpoint:
    """Tests for POST /reservoir/v2/ (V2 S3 endpoint)."""

    def test_v2_endpoint_exists(self, client):
        """Test V2 endpoint exists and requires body."""
        response = client.post("/reservoir/v2/")
        # Should fail validation, not 404
        assert response.status_code == 422

    def test_v2_requires_sources(self, client):
        """Test V2 endpoint requires sources array."""
        response = client.post("/reservoir/v2/", json={
            "destination": {
                "bucket": "newave-bucket",
                "execution_hash": "abc123",
                "program": "NEWAVE"
            },
            "rules": []
        })
        assert response.status_code == 422

    def test_v2_requires_destination(self, client):
        """Test V2 endpoint requires destination object."""
        response = client.post("/reservoir/v2/", json={
            "sources": [{
                "bucket": "decomp-bucket",
                "execution_hash": "abc123",
                "program": "DECOMP"
            }],
            "rules": []
        })
        assert response.status_code == 422

    def test_v2_validates_empty_sources(self, client):
        """Test V2 endpoint validates sources cannot be empty."""
        response = client.post("/reservoir/v2/", json={
            "sources": [],  # Empty - should fail
            "destination": {
                "bucket": "newave-bucket",
                "execution_hash": "abc123",
                "program": "NEWAVE"
            },
            "rules": []
        })
        assert response.status_code == 422

    def test_v2_validates_source_bucket(self, client):
        """Test V2 endpoint validates source bucket field."""
        response = client.post("/reservoir/v2/", json={
            "sources": [{
                # Missing bucket
                "execution_hash": "abc123",
                "program": "DECOMP"
            }],
            "destination": {
                "bucket": "newave-bucket",
                "execution_hash": "xyz789",
                "program": "NEWAVE"
            },
            "rules": []
        })
        assert response.status_code == 422

    def test_v2_validates_source_execution_hash(self, client):
        """Test V2 endpoint validates source execution_hash field."""
        response = client.post("/reservoir/v2/", json={
            "sources": [{
                "bucket": "decomp-bucket",
                # Missing execution_hash
                "program": "DECOMP"
            }],
            "destination": {
                "bucket": "newave-bucket",
                "execution_hash": "xyz789",
                "program": "NEWAVE"
            },
            "rules": []
        })
        assert response.status_code == 422

    def test_v2_validates_source_program(self, client):
        """Test V2 endpoint validates source program field."""
        response = client.post("/reservoir/v2/", json={
            "sources": [{
                "bucket": "decomp-bucket",
                "execution_hash": "abc123",
                "program": "INVALID"  # Invalid program
            }],
            "destination": {
                "bucket": "newave-bucket",
                "execution_hash": "xyz789",
                "program": "NEWAVE"
            },
            "rules": []
        })
        assert response.status_code == 422

    def test_v2_validates_destination_bucket(self, client):
        """Test V2 endpoint validates destination bucket field."""
        response = client.post("/reservoir/v2/", json={
            "sources": [{
                "bucket": "decomp-bucket",
                "execution_hash": "abc123",
                "program": "DECOMP"
            }],
            "destination": {
                # Missing bucket
                "execution_hash": "xyz789",
                "program": "NEWAVE"
            },
            "rules": []
        })
        assert response.status_code == 422

    def test_v2_validates_destination_execution_hash(self, client):
        """Test V2 endpoint validates destination execution_hash field."""
        response = client.post("/reservoir/v2/", json={
            "sources": [{
                "bucket": "decomp-bucket",
                "execution_hash": "abc123",
                "program": "DECOMP"
            }],
            "destination": {
                "bucket": "newave-bucket",
                # Missing execution_hash
                "program": "NEWAVE"
            },
            "rules": []
        })
        assert response.status_code == 422

    def test_v2_validates_destination_program(self, client):
        """Test V2 endpoint validates destination program field."""
        response = client.post("/reservoir/v2/", json={
            "sources": [{
                "bucket": "decomp-bucket",
                "execution_hash": "abc123",
                "program": "DECOMP"
            }],
            "destination": {
                "bucket": "newave-bucket",
                "execution_hash": "xyz789",
                "program": "INVALID"  # Invalid program
            },
            "rules": []
        })
        assert response.status_code == 422

    def test_v2_accepts_valid_programs(self, client):
        """Test V2 accepts valid program values (though may fail on S3)."""
        # Test NEWAVE program value is accepted (request validation passes)
        # May fail on S3 access later
        response = client.post("/reservoir/v2/", json={
            "sources": [{
                "bucket": "decomp-bucket",
                "execution_hash": "abc123",
                "program": "DECOMP"
            }],
            "destination": {
                "bucket": "newave-bucket",
                "execution_hash": "xyz789",
                "program": "NEWAVE"
            },
            "rules": []
        })
        # Should not be 422 (validation) - may be 500 or 404 from S3
        assert response.status_code != 422


class TestReservoirV2RulesValidation:
    """Tests for rules validation in V2 endpoint."""

    def test_v2_accepts_empty_rules(self, client):
        """Test V2 accepts empty rules array (validation passes)."""
        response = client.post("/reservoir/v2/", json={
            "sources": [{
                "bucket": "decomp-bucket",
                "execution_hash": "abc123",
                "program": "DECOMP"
            }],
            "destination": {
                "bucket": "newave-bucket",
                "execution_hash": "xyz789",
                "program": "NEWAVE"
            },
            "rules": []
        })
        # Should not be 422 (validation passes)
        assert response.status_code != 422

    def test_v2_validates_rule_reservoir_code(self, client):
        """Test V2 validates rule reservoirCode is required."""
        response = client.post("/reservoir/v2/", json={
            "sources": [{
                "bucket": "decomp-bucket",
                "execution_hash": "abc123",
                "program": "DECOMP"
            }],
            "destination": {
                "bucket": "newave-bucket",
                "execution_hash": "xyz789",
                "program": "NEWAVE"
            },
            "rules": [{
                # Missing reservoirCode
                "uheCode": 156,
                "constraintType": "QDEF",
                "month": 1
            }]
        })
        assert response.status_code == 422

    def test_v2_accepts_valid_rule(self, client):
        """Test V2 accepts valid rule structure (validation passes)."""
        response = client.post("/reservoir/v2/", json={
            "sources": [{
                "bucket": "decomp-bucket",
                "execution_hash": "abc123",
                "program": "DECOMP"
            }],
            "destination": {
                "bucket": "newave-bucket",
                "execution_hash": "xyz789",
                "program": "NEWAVE"
            },
            "rules": [{
                "reservoirCode": 156,
                "uheCode": 156,
                "constraintType": "QDEF",
                "month": 1,
                "minVolume": 0.0,
                "maxVolume": 30.0,
                "minLimit": 100.0,
                "maxLimit": 99999.0,
                "frequency": "M",
                "label": "Test Rule"
            }]
        })
        # Should not be 422 (validation passes)
        assert response.status_code != 422


class TestReservoirV2ResponseFormat:
    """Tests for V2 response format."""

    def test_v2_error_response_format(self, client):
        """Test V2 error response format includes expected fields."""
        response = client.post("/reservoir/v2/", json={
            "sources": [{
                "bucket": "decomp-bucket",
                "execution_hash": "nonexistent",
                "program": "DECOMP"
            }],
            "destination": {
                "bucket": "newave-bucket",
                "execution_hash": "dest123",
                "program": "NEWAVE"
            },
            "rules": []
        })
        
        # Should be an error (404 or 500)
        assert response.status_code in [404, 500]
        
        data = response.json()
        # Error responses should have detail field from HTTPException
        assert "detail" in data

    def test_v2_returns_json_content_type(self, client):
        """Test V2 always returns JSON content type."""
        response = client.post("/reservoir/v2/", json={
            "sources": [{
                "bucket": "decomp-bucket",
                "execution_hash": "abc123",
                "program": "DECOMP"
            }],
            "destination": {
                "bucket": "newave-bucket",
                "execution_hash": "xyz789",
                "program": "NEWAVE"
            },
            "rules": []
        })
        
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type


class TestReservoirEndpointRouting:
    """Tests for endpoint routing and paths."""

    def test_reservoir_v1_path(self, client):
        """Test /reservoir/ path works."""
        response = client.post("/reservoir/")
        # Should respond (422 for validation error, not 404)
        assert response.status_code != 404

    def test_reservoir_v2_path(self, client):
        """Test /reservoir/v2/ path works."""
        response = client.post("/reservoir/v2/")
        # Should respond (422 for validation error, not 404)
        assert response.status_code != 404

    def test_get_method_not_allowed_v1(self, client):
        """Test GET method not allowed on V1."""
        response = client.get("/reservoir/")
        assert response.status_code == 405

    def test_get_method_not_allowed_v2(self, client):
        """Test GET method not allowed on V2."""
        response = client.get("/reservoir/v2/")
        assert response.status_code == 405


class TestOpenAPIDocumentation:
    """Tests for OpenAPI documentation."""

    def test_openapi_includes_v1_endpoint(self, client):
        """Test OpenAPI includes V1 endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        openapi = response.json()
        
        assert "/reservoir/" in openapi["paths"]

    def test_openapi_includes_v2_endpoint(self, client):
        """Test OpenAPI includes V2 endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        openapi = response.json()
        
        assert "/reservoir/v2/" in openapi["paths"]

    def test_openapi_v2_has_response_models(self, client):
        """Test OpenAPI V2 endpoint has response models defined."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        openapi = response.json()
        
        v2_path = openapi["paths"].get("/reservoir/v2/", {})
        post_op = v2_path.get("post", {})
        
        # Should have responses defined
        assert "responses" in post_op
        responses = post_op["responses"]
        
        # Should have success and error responses
        assert "200" in responses
        assert "404" in responses or "422" in responses or "500" in responses

    def test_docs_endpoint_available(self, client):
        """Test /docs endpoint is available."""
        response = client.get("/docs")
        assert response.status_code == 200
