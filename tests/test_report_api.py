def test_report_endpoint_rejects_unconfirmed_session(client):
    created = client.post(
        "/api/v1/attendance/sessions",
        json={"name": "Unconfirmed Report"},
    )
    response = client.get(f"/api/v1/attendance/sessions/{created.json()['id']}/report")
    assert response.status_code == 422
    assert "confirmed" in response.json()["error"]["message"]
