"""Who the server thinks is calling, and what that lets them do."""

import os
import tempfile

os.environ.setdefault("KYC_DB_PATH", os.path.join(tempfile.mkdtemp(), "auth.db"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as client:
        yield client


def test_the_caller_states_who_they_are(client):
    me = client.get("/api/me", headers={"X-User": "priya@example.com"}).json()
    assert (me["email"], me["role"]) == ("priya@example.com", "senior_reviewer")


def test_a_caller_who_says_nothing_gets_the_default_user(client):
    me = client.get("/api/me").json()
    assert (me["email"], me["role"]) == ("nora@example.com", "analyst")


def test_someone_outside_the_roster_is_rejected(client):
    assert client.get("/api/me", headers={"X-User": "zoe@example.com"}).status_code == 401


def test_the_roster_is_offered_to_the_switcher(client):
    assert client.get("/api/me").json()["users"]["priya@example.com"] == "senior_reviewer"
