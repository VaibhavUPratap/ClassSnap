"""
Integration tests for ClassSnap health check endpoints.
"""

from fastapi import status


def test_api_v1_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "ClassSnap"
    assert data["version"] == "0.1.0"
    assert data["database_status"] == "connected"
    assert "timestamp" in data


def test_root_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_status"] == "connected"


def test_root_index_endpoint(client):
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["app"] == "ClassSnap"
    assert data["status"] == "online"
    assert data["docs_url"] == "/docs"
