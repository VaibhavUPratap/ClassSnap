def test_roster_api_crud_surface(client):
    created = client.post(
        "/api/v1/students",
        params={"actor": "admin"},
        json={
            "student_id": "API-STU-1",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "has_consent": True,
        },
    )
    assert created.status_code == 201
    student = created.json()
    assert student["student_id"] == "API-STU-1"
    assert student["enrolled_templates_count"] == 0

    listed = client.get("/api/v1/students", params={"active_only": True})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [student["id"]]

    updated = client.patch(
        f"/api/v1/students/{student['id']}",
        json={"last_name": "Byron"},
    )
    assert updated.status_code == 200
    assert updated.json()["last_name"] == "Byron"

    fetched = client.get("/api/v1/students/API-STU-1")
    assert fetched.status_code == 200
    assert fetched.json()["first_name"] == "Ada"
