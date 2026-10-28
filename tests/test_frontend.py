def test_review_workspace_is_served(client):
    response = client.get("/review/")
    assert response.status_code == 200
    assert "ClassSnap Dashboard" in response.text
    assert 'data-section="students"' in response.text
