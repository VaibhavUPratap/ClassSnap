def test_attendance_session_api_lifecycle(client):
    created = client.post(
        "/api/v1/attendance/sessions",
        json={"name": "API Session", "actor": "teacher-1"},
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    processed = client.post(f"/api/v1/attendance/sessions/{session_id}/process")
    assert processed.status_code == 200
    assert processed.json()["status"] == "processing"

    proposed = client.post(
        f"/api/v1/attendance/sessions/{session_id}/proposals",
        json={
            "actor": "system",
            "proposals": [
                {
                    "detection_id": "face-api-1",
                    "status": "unknown",
                    "rejection_reason": "No confident identity",
                }
            ],
        },
    )
    assert proposed.status_code == 200
    assert proposed.json()["status"] == "review_required"

    reviewed = client.post(
        f"/api/v1/attendance/sessions/{session_id}/detections/face-api-1/review",
        json={"present": False, "actor": "teacher-1", "notes": "Not identifiable"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "reviewed_absent"

    confirmed = client.post(
        f"/api/v1/attendance/sessions/{session_id}/confirm",
        params={"actor": "teacher-1"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
