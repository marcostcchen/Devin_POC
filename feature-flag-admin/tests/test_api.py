"""Smoke tests over the HTTP API: CRUD, audit trail, RBAC and evaluation."""

from fastapi.testclient import TestClient

from tests.conftest import ADMIN, VIEWER


def create_flag(client: TestClient, name: str, **fields) -> int:
    response = client.post("/api/flags", json={"name": name, **fields}, headers=ADMIN)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_crud_and_audit_trail(client: TestClient):
    flag_id = create_flag(client, "smoke-flag", description="hi")

    toggled = client.patch(f"/api/flags/{flag_id}", json={"enabled": True}, headers=ADMIN)
    assert toggled.status_code == 200 and toggled.json()["enabled"] is True

    audit = client.get(f"/api/flags/{flag_id}/audit").json()
    assert [entry["action"] for entry in audit] == ["toggled", "created"]
    assert audit[0]["actor"] == "ada@example.com"
    assert audit[0]["detail"] == "enabled: False -> True"

    assert client.delete(f"/api/flags/{flag_id}", headers=ADMIN).status_code == 204
    # History outlives the flag it describes.
    assert [e["action"] for e in client.get(f"/api/flags/{flag_id}/audit").json()][0] == "deleted"


def test_viewer_is_read_only(client: TestClient):
    flag_id = create_flag(client, "rbac-flag")

    assert client.get("/api/flags", headers=VIEWER).status_code == 200
    assert client.patch(f"/api/flags/{flag_id}", json={"enabled": True}, headers=VIEWER).status_code == 403
    assert client.delete(f"/api/flags/{flag_id}", headers=VIEWER).status_code == 403


def test_rejects_duplicate_names_and_bad_rollout(client: TestClient):
    create_flag(client, "unique-flag")

    duplicate = client.post("/api/flags", json={"name": "unique-flag"}, headers=ADMIN)
    assert duplicate.status_code == 409

    invalid = client.post(
        "/api/flags", json={"name": "bad-rollout", "rollout_percentage": 150}, headers=ADMIN
    )
    assert invalid.status_code == 422


def test_evaluation_reflects_targeting(client: TestClient):
    flag_id = create_flag(client, "eval-flag", enabled=True)

    assert client.get("/api/evaluate/eval-flag", params={"user_id": "u1"}).json()["enabled"] is True

    client.patch(f"/api/flags/{flag_id}", json={"rollout_percentage": 0}, headers=ADMIN)
    assert client.get("/api/evaluate/eval-flag", params={"user_id": "u1"}).json()["enabled"] is False

    client.patch(
        f"/api/flags/{flag_id}",
        json={"rollout_percentage": 100, "target_team": "platform"},
        headers=ADMIN,
    )
    assert client.get("/api/evaluate/eval-flag", params={"team": "web"}).json()["enabled"] is False
    assert client.get("/api/evaluate/eval-flag", params={"team": "platform"}).json()["enabled"] is True

    assert client.get("/api/evaluate/missing-flag").status_code == 404


def test_identity_lists_the_switcher_roster(client: TestClient):
    body = client.get("/api/me", headers=VIEWER).json()
    assert body["role"] == "viewer"
    assert body["users"]["ada@example.com"] == "admin"

    assert client.get("/api/me", headers={"X-User": "nobody@example.com"}).status_code == 401
