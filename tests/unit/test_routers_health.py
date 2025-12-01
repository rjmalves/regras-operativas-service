"""Unit tests for health router."""

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


class TestLivenessEndpoint:
    """Tests for /health/live endpoint."""

    def test_liveness_returns_ok(self, client):
        """Test liveness endpoint returns ok."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_liveness_is_fast(self, client):
        """Test liveness endpoint responds quickly."""
        import time
        start = time.time()
        response = client.get("/health/live")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 0.5  # Should respond in under 500ms


class TestReadinessEndpoint:
    """Tests for /health/ready endpoint."""

    def test_readiness_structure(self, client):
        """Test readiness endpoint returns expected structure."""
        response = client.get("/health/ready")
        # May return 200 even if S3 check fails - we just check structure
        data = response.json()
        
        assert "status" in data
        assert "checks" in data
        assert data["status"] in ["ready", "not_ready"]


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_structure(self, client):
        """Test health endpoint returns expected structure."""
        response = client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "checks" in data

    def test_health_includes_version(self, client):
        """Test health endpoint includes version."""
        response = client.get("/health")
        data = response.json()
        
        assert data["version"] == "2.0.0"

    def test_health_includes_timestamp(self, client):
        """Test health endpoint includes timestamp."""
        response = client.get("/health")
        data = response.json()
        
        # Timestamp should be ISO format
        assert "timestamp" in data
        # Should be parseable as datetime
        from datetime import datetime
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
