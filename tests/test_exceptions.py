"""
Tests for ClassSnap custom exception handling.
"""

from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from classsnap.exceptions import (
    ClassSnapError,
    ResourceNotFoundError,
    ValidationError,
    classsnap_exception_handler,
    generic_exception_handler,
)


def test_custom_exception_handling():
    test_app = FastAPI()
    test_app.add_exception_handler(ClassSnapError, classsnap_exception_handler)
    test_app.add_exception_handler(Exception, generic_exception_handler)

    @test_app.get("/trigger-not-found")
    def trigger_not_found():
        raise ResourceNotFoundError(resource_type="Student", identifier="ST-999")

    @test_app.get("/trigger-validation")
    def trigger_validation():
        raise ValidationError(message="Student ID format is invalid", details={"field": "student_id"})

    @test_app.get("/trigger-unhandled")
    def trigger_unhandled():
        raise RuntimeError("Unexpected failure")

    with TestClient(test_app, raise_server_exceptions=False) as client:
        # Not found test
        res_nf = client.get("/trigger-not-found")
        assert res_nf.status_code == status.HTTP_404_NOT_FOUND
        data_nf = res_nf.json()
        assert data_nf["error"]["code"] == "RESOURCE_NOT_FOUND"
        assert "ST-999" in data_nf["error"]["message"]

        # Validation test
        res_val = client.get("/trigger-validation")
        assert res_val.status_code == 422
        data_val = res_val.json()
        assert data_val["error"]["code"] == "VALIDATION_ERROR"

        # Unhandled 500 test
        res_500 = client.get("/trigger-unhandled")
        assert res_500.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data_500 = res_500.json()
        assert data_500["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "server error" in data_500["error"]["message"].lower()
