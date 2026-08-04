"""Who the server thinks is calling, and what that lets them do."""


def test_the_caller_states_who_they_are(client):
    me = client.get("/api/me", headers={"X-User": "linus@example.com"}).json()
    assert (me["email"], me["role"]) == ("linus@example.com", "viewer")


def test_a_caller_who_says_nothing_gets_the_default_user(client):
    me = client.get("/api/me").json()
    assert (me["email"], me["role"]) == ("ada@example.com", "admin")


def test_someone_outside_the_roster_is_rejected(client):
    assert client.get("/api/me", headers={"X-User": "zoe@example.com"}).status_code == 401


def test_a_viewer_cannot_write(client):
    response = client.post(
        "/api/flags", json={"name": "from-a-viewer"}, headers={"X-User": "linus@example.com"}
    )
    assert response.status_code == 403
