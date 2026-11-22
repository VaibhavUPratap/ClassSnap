def test_attendance_session_api_lifecycle(client):
    student = client.post(
        "/api/v1/students",
        json={"student_id": "API24LC0001", "first_name": "Api", "last_name": "Student"},
    )
    assert student.status_code == 201
    created = client.post(
        "/api/v1/attendance/sessions",
        json={"name": "API Session", "actor": "teacher-1", "class_at": "2026-10-28T09:30:00"},
    )
    assert created.status_code == 201
    session_id = created.json()["id"]
    assert created.json()["class_at"].startswith("2026-10-28T09:30:00")

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


def test_delete_attendance_session_removes_it_from_history(client):
    student = client.post(
        "/api/v1/students",
        json={"student_id": "API24DL0001", "first_name": "Gone", "last_name": "Soon"},
    )
    assert student.status_code == 201
    created = client.post(
        "/api/v1/attendance/sessions", json={"name": "Delete Session", "actor": "teacher-1"}
    )
    session_id = created.json()["id"]
    client.post(f"/api/v1/attendance/sessions/{session_id}/process")
    client.post(
        f"/api/v1/attendance/sessions/{session_id}/proposals",
        json={
            "actor": "system",
            "proposals": [
                {
                    "detection_id": "face-del-1",
                    "status": "matched_pending_review",
                    "student_id": student.json()["id"],
                    "similarity": 0.97,
                }
            ],
        },
    )
    confirmed = client.post(
        f"/api/v1/attendance/sessions/{session_id}/confirm", json={"actor": "teacher-1"}
    )
    assert confirmed.status_code == 200
    assert any(item["session_id"] == session_id for item in client.get("/api/v1/attendance/sessions").json())

    deleted = client.delete(
        f"/api/v1/attendance/sessions/{session_id}", params={"actor": "teacher-1"}
    )
    assert deleted.status_code == 204
    assert deleted.content == b""

    history = client.get("/api/v1/attendance/sessions").json()
    assert all(item["session_id"] != session_id for item in history)
    assert client.get(f"/api/v1/attendance/sessions/{session_id}").status_code == 404
    student_history = client.get(f"/api/v1/attendance/students/{student.json()['id']}/history")
    assert student_history.status_code == 200
    assert student_history.json()["total_sessions"] == 0

    again = client.delete(f"/api/v1/attendance/sessions/{session_id}")
    assert again.status_code == 404
