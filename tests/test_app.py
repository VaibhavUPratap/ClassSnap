"""
Tests for ClassSnap application initialization and router setup.
"""

from fastapi.testclient import TestClient
from classsnap.main import create_app


def test_app_creation():
    app = create_app()
    assert app.title == "ClassSnap"
    assert app.version == "0.1.0"

    # Verify OpenAPI documentation registered routes
    openapi_paths = list(app.openapi()["paths"].keys())
    assert "/api/v1/health" in openapi_paths

    with TestClient(app) as client:
        res_root = client.get("/")
        assert res_root.status_code == 200
        assert res_root.json()["app"] == "ClassSnap"

        res_health = client.get("/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "healthy"
