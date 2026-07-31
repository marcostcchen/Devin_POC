import os
import tempfile

os.environ["FLAGS_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ADMIN = {"X-User": "ada@example.com"}
VIEWER = {"X-User": "linus@example.com"}


def test_crud_audit_and_rbac():
    with TestClient(app) as client:
        created = client.post(
            "/api/flags",
            json={"name": "smoke-flag", "description": "hi", "rollout_percentage": 100},
            headers=ADMIN,
        )
        assert created.status_code == 201, created.text
        flag_id = created.json()["id"]

        assert client.patch(f"/api/flags/{flag_id}", json={"enabled": True}, headers=VIEWER).status_code == 403

        toggled = client.patch(f"/api/flags/{flag_id}", json={"enabled": True}, headers=ADMIN)
        assert toggled.status_code == 200 and toggled.json()["enabled"] is True

        audit = client.get(f"/api/flags/{flag_id}/audit").json()
        assert [e["action"] for e in audit] == ["toggled", "created"]
        assert audit[0]["actor"] == "ada@example.com"

        evaluated = client.get("/api/evaluate/smoke-flag", params={"user_id": "u1"}).json()
        assert evaluated["enabled"] is True

        client.patch(f"/api/flags/{flag_id}", json={"rollout_percentage": 0}, headers=ADMIN)
        assert client.get("/api/evaluate/smoke-flag", params={"user_id": "u1"}).json()["enabled"] is False

        client.patch(
            f"/api/flags/{flag_id}", json={"rollout_percentage": 100, "target_team": "platform"}, headers=ADMIN
        )
        assert client.get("/api/evaluate/smoke-flag", params={"team": "web"}).json()["enabled"] is False
        assert client.get("/api/evaluate/smoke-flag", params={"team": "platform"}).json()["enabled"] is True

        assert client.delete(f"/api/flags/{flag_id}", headers=VIEWER).status_code == 403
        assert client.delete(f"/api/flags/{flag_id}", headers=ADMIN).status_code == 204
        assert client.get("/api/evaluate/smoke-flag").status_code == 404
