def test_roster_api_crud_surface(client):
    created = client.post(
        "/api/v1/students",
        params={"actor": "admin"},
        json={
            "student_id": "API24ST0001",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "has_consent": True,
        },
    )
    assert created.status_code == 201
    student = created.json()
    assert student["student_id"] == "API24ST0001"
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

    fetched = client.get("/api/v1/students/API24ST0001")
    assert fetched.status_code == 200
    assert fetched.json()["first_name"] == "Ada"


def test_roster_api_requires_usn_format(client):
    invalid = client.post(
        "/api/v1/students",
        json={
            "student_id": "STU101",
            "first_name": "Invalid",
            "last_name": "USN",
        },
    )
    assert invalid.status_code == 422
    assert "USN must use the format ENG24AM0107" in str(invalid.json())

    valid = client.post(
        "/api/v1/students",
        json={
            "student_id": "ENG24AM0107",
            "first_name": "Valid",
            "last_name": "USN",
        },
    )
    assert valid.status_code == 201


def test_roster_api_normalizes_pasted_usn(client):
    response = client.post(
        "/api/v1/students",
        json={
            "student_id": " eng24am0108 ",
            "first_name": "Pasted",
            "last_name": "USN",
        },
    )
    assert response.status_code == 201
    assert response.json()["student_id"] == "ENG24AM0108"
