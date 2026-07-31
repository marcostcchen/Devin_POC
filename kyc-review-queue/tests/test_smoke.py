import os
import tempfile

os.environ["KYC_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seed import CASE_COUNT  # noqa: E402

ANALYST = {"X-User": "ilva.analyst@compliance.test"}
SENIOR = {"X-User": "neris.senior@compliance.test"}


def first_id(client, headers, **params):
    cases = client.get("/api/cases", params=params, headers=headers).json()
    assert cases, f"no case matched {params}"
    return cases[0]["id"]


def test_queue_filters_decisions_audit_and_rbac():
    with TestClient(app) as client:
        seniors_view = client.get("/api/cases", headers=SENIOR).json()
        assert len(seniors_view) == CASE_COUNT
        assert [c["risk_level"] for c in seniors_view] == sorted(
            (c["risk_level"] for c in seniors_view), key=["high", "medium", "low"].index
        )

        escalated = [c for c in seniors_view if c["status"] == "escalated"]
        assert escalated, "seed data should contain escalated cases"

        # Analysts do not see the escalated queue at all.
        analyst_view = client.get("/api/cases", headers=ANALYST).json()
        assert len(analyst_view) == CASE_COUNT - len(escalated)
        assert client.get(f"/api/cases/{escalated[0]['id']}", headers=ANALYST).status_code == 404

        assert {c["risk_level"] for c in client.get("/api/cases", params={"risk": "high"}, headers=ANALYST).json()} == {"high"}
        assert {c["status"] for c in client.get("/api/cases", params={"status": "new"}, headers=ANALYST).json()} == {"new"}

        case_id = first_id(client, ANALYST, status="new")
        assert client.post(f"/api/cases/{case_id}/claim", headers=ANALYST).json()["status"] == "in_review"

        detail = client.get(f"/api/cases/{case_id}", headers=ANALYST).json()
        assert detail["documents"], "cases carry placeholder documents"

        # A decision without a reason is rejected.
        assert client.post(
            f"/api/cases/{case_id}/decision", json={"decision": "approve", "reason": "  "}, headers=ANALYST
        ).status_code == 422

        approved = client.post(
            f"/api/cases/{case_id}/decision",
            json={"decision": "approve", "reason": "documents match, mock screening clean"},
            headers=ANALYST,
        ).json()
        assert (approved["status"], approved["outcome"]) == ("closed", "approved")
        assert [e["action"] for e in approved["history"]][:3] == ["approved", "in_review", "submitted"]
        assert approved["history"][0]["actor"] == ANALYST["X-User"]
        assert approved["history"][0]["reason"] == "documents match, mock screening clean"

        # Only a senior reviewer can override a closed case.
        assert client.post(
            f"/api/cases/{case_id}/decision", json={"decision": "reject", "reason": "changed my mind"}, headers=ANALYST
        ).status_code == 403
        overridden = client.post(
            f"/api/cases/{case_id}/decision",
            json={"decision": "reject", "reason": "source of funds unresolved"},
            headers=SENIOR,
        ).json()
        assert overridden["outcome"] == "rejected"
        assert overridden["history"][0]["action"] == "override_rejected"

        # Escalation moves a case out of the analyst queue and into the senior one.
        to_escalate = first_id(client, ANALYST, status="new")
        client.post(
            f"/api/cases/{to_escalate}/decision",
            json={"decision": "escalate", "reason": "ownership structure unclear"},
            headers=ANALYST,
        )
        assert client.get(f"/api/cases/{to_escalate}", headers=ANALYST).status_code == 404
        senior_detail = client.get(f"/api/cases/{to_escalate}", headers=SENIOR).json()
        assert senior_detail["status"] == "escalated"
        assert client.post(
            f"/api/cases/{to_escalate}/decision",
            json={"decision": "approve", "reason": "registry extract checks out"},
            headers=SENIOR,
        ).json()["history"][0]["action"] == "override_approved"

        assert client.get("/api/cases", headers={"X-User": "nobody@compliance.test"}).status_code == 401
