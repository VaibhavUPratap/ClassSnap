def test_review_workspace_is_served(client):
    response = client.get("/review/")
    assert response.status_code == 200
    assert '<div id="root"></div>' in response.text
    assert 'src="/review/assets/' in response.text
