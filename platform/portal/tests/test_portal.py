"""The portal's two jobs: the auth subrequest, and the catalog page."""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

CATALOG = {
    "platform": {"name": "POC Platform", "domain": "poc.test", "environment": "poc"},
    "principals": [
        {"email": "ada@example.com", "display_name": "Ada Lovelace", "groups": ["kyc-seniors"]},
        {"email": "mira@example.com", "display_name": "Mira Osei", "groups": []},
    ],
    "projects": [
        {
            "id": "kyc-review-queue",
            "name": "KYC Review Queue",
            "summary": "Case triage.",
            "owner": "Compliance",
            "stage": "poc",
            "url": "http://kyc.poc.test",
            "namespace": "poc-kyc-review-queue",
            "roles": ["analyst", "senior_reviewer"],
            "default_role": "analyst",
            "group_roles": {"kyc-seniors": "senior_reviewer", "kyc-analysts": "analyst"},
            "capabilities": ["Queue"],
            "limitations": ["Mocked identity"],
        }
    ],
    "guardrails": {"allowed": [], "not_allowed": []},
}


@pytest.fixture(scope="module")
def client():
    directory = tempfile.mkdtemp()
    path = Path(directory) / "platform.json"
    path.write_text(json.dumps(CATALOG), encoding="utf-8")
    os.environ["PORTAL_CONFIG"] = str(path)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app.main import app

    # The session cookie is set for the parent domain, so the client has to be
    # on a host under it for the browser half of the contract to hold.
    with TestClient(app, base_url="http://portal.poc.test") as test_client:
        yield test_client


def test_an_anonymous_request_is_not_authenticated(client):
    assert client.get("/auth").status_code == 401


def test_signing_in_makes_the_subrequest_assert_the_persona(client):
    client.post("/login", data={"email": "ada@example.com"}, follow_redirects=False)
    response = client.get("/auth")
    assert response.status_code == 202
    assert response.headers["X-Auth-Request-Email"] == "ada@example.com"
    assert response.headers["X-Auth-Request-User"] == "Ada Lovelace"
    assert response.headers["X-Auth-Request-Groups"] == "kyc-seniors"


def test_a_second_browser_does_not_inherit_the_signed_in_persona(client):
    client.post("/login", data={"email": "ada@example.com"}, follow_redirects=False)
    other_browser = TestClient(client.app, base_url="http://portal.poc.test")
    assert other_browser.get("/auth").status_code == 401


def test_an_unknown_persona_cannot_be_asserted(client):
    response = client.post(
        "/login", data={"email": "attacker@example.com"}, follow_redirects=False
    )
    assert response.headers["location"] == "/login"


def test_the_sign_in_page_offers_the_directory(client):
    body = client.get("/login").text
    assert "Ada Lovelace" in body and "kyc-seniors" in body


def test_the_catalog_shows_the_role_each_persona_holds(client):
    client.post("/login", data={"email": "ada@example.com"}, follow_redirects=False)
    assert "senior_reviewer" in client.get("/").text
    client.post("/login", data={"email": "mira@example.com"}, follow_redirects=False)
    # No mapped group, so the project's least privileged role.
    assert "analyst" in client.get("/").text


def test_signing_out_stops_the_assertion(client):
    client.post("/login", data={"email": "ada@example.com"}, follow_redirects=False)
    client.post("/logout", follow_redirects=False)
    assert client.get("/auth").status_code == 401
