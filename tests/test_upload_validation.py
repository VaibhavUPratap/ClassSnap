def test_enrollment_rejects_non_image_upload(client):
    created = client.post(
        "/api/v1/students",
        json={
            "student_id": "UPLOAD-API-1",
            "first_name": "Upload",
            "last_name": "Test",
        },
    )
    response = client.post(
        f"/api/v1/students/{created.json()['student_id']}/enrollment",
        files={"image": ("payload.txt", b"not-an-image", "text/plain")},
        data={"consent_granted": "false"},
    )
    assert response.status_code == 422
    assert "image media type" in response.json()["error"]["message"]


def test_missing_student_returns_structured_domain_error(client):
    response = client.get("/api/v1/students/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
