"""Tests for health check and root endpoints."""


def test_health_check(client):
    """Test the health check endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app" in data


def test_root_endpoint(client, api_v1_prefix):
    """Test the root API endpoint."""
    response = client.get(f"{api_v1_prefix}/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data
