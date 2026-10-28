def test_attendance_detail_api_exposes_review_state(client):
    created = client.post(
        "/api/v1/attendance/sessions",
        json={"name": "Detail Session"},
    )
    session_id = created.json()["id"]
    client.post(f"/api/v1/attendance/sessions/{session_id}/process")
    client.post(
        f"/api/v1/attendance/sessions/{session_id}/proposals",
        json={"proposals": [{"detection_id": "face-detail", "status": "unknown"}]},
    )

    detail = client.get(f"/api/v1/attendance/sessions/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["detections"][0]["reviewed"] is False
