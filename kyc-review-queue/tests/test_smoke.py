import os
import tempfile

os.environ["KYC_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ANALYST = {"X-User": "nora@example.com"}
SENIOR = {"X-User": "priya@example.com"}


def test_queue_decisions_audit_and_rbac():
    with TestClient(app) as client:
        cases = client.get("/api/cases", headers=ANALYST).json()
        assert 15 <= len(client.get("/api/cases", headers=SENIOR).json()) <= 20
        assert all(c["status"] != "escalated" for c in cases)
        assert [c["risk_level"] for c in cases][0] == "high"

        high = client.get("/api/cases", params={"risk_level": "high"}, headers=SENIOR).json()
        assert high and all(c["risk_level"] == "high" for c in high)

        case_id = next(c["id"] for c in cases if c["status"] == "new")

        assert client.post(
            f"/api/cases/{case_id}/decisions", json={"action": "approve", "reason": " "}, headers=ANALYST
        ).status_code == 422

        decided = client.post(
            f"/api/cases/{case_id}/decisions",
            json={"action": "approve", "reason": "documents match, low risk"},
            headers=ANALYST,
        )
        assert decided.status_code == 201, decided.text
        assert decided.json()["status_after"] == "closed"

        history = client.get(f"/api/cases/{case_id}/history", headers=ANALYST).json()
        assert history[0]["actor"] == "nora@example.com" and history[0]["action"] == "approve"
        assert history[0]["reason"] == "documents match, low risk"

        # closed cases are analyst-final; only a senior reviewer can override
        assert client.post(
            f"/api/cases/{case_id}/decisions",
            json={"action": "reject", "reason": "changed my mind"},
            headers=ANALYST,
        ).status_code == 403
        override = client.post(
            f"/api/cases/{case_id}/decisions",
            json={"action": "reject", "reason": "second look: address proof is stale"},
            headers=SENIOR,
        )
        assert override.status_code == 201 and override.json()["action"] == "override"

        # escalation moves a case out of the analyst queue entirely
        target = next(c["id"] for c in cases if c["status"] in ("new", "in_review") and c["id"] != case_id)
        client.post(
            f"/api/cases/{target}/decisions",
            json={"action": "escalate", "reason": "possible duplicate identity"},
            headers=ANALYST,
        )
        assert client.get(f"/api/cases/{target}", headers=ANALYST).status_code == 404
        assert client.get(f"/api/cases/{target}", headers=SENIOR).json()["status"] == "escalated"
        escalated = client.get("/api/cases", params={"status": "escalated"}, headers=SENIOR).json()
        assert target in [c["id"] for c in escalated]

        assert client.get("/api/audit").json()[0]["case_id"] == target
