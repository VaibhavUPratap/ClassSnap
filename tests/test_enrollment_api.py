def test_enrollment_api_requires_consent(client):
    created = client.post(
        "/api/v1/students",
        json={
            "student_id": "ENROLL-API-1",
            "first_name": "Test",
            "last_name": "Student",
        },
    )
    assert created.status_code == 201
    student_id = created.json()["student_id"]

    response = client.post(
        f"/api/v1/students/{student_id}/enrollment",
        files={"image": ("face.jpg", b"not-an-image", "image/jpeg")},
        data={"consent_granted": "false"},
    )
    assert response.status_code == 422
    assert "consent" in response.json()["error"]["message"].lower()
