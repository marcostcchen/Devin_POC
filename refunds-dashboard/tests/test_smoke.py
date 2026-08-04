import os
import tempfile

os.environ["REFUNDS_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import APPROVAL_THRESHOLD_AMOUNT  # noqa: E402
from app.main import app  # noqa: E402

AGENT = {"X-User": "riley@example.com"}
FINANCE = {"X-User": "dana@example.com"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def pending(client, *, above_threshold: bool):
    """A pending request on the side of the threshold the test needs."""
    requests = client.get("/api/refunds", params={"status": "pending"}).json()
    return next(r for r in requests if r["requires_finance_approval"] is above_threshold)


def test_the_queue_filters_and_sorts(client):
    everything = client.get("/api/refunds").json()
    assert len(everything) == 23
    by_amount = client.get(
        "/api/refunds", params={"sort_by": "amount", "sort_direction": "desc"}
    ).json()
    assert [r["amount"] for r in by_amount] == sorted(
        (r["amount"] for r in everything), reverse=True
    )
    expensive = client.get("/api/refunds", params={"min_amount": 300}).json()
    assert expensive and all(r["amount"] >= 300 for r in expensive)
    assert all(r["status"] == "denied" for r in client.get(
        "/api/refunds", params={"status": "denied"}
    ).json())
    assert client.get("/api/refunds", params={"status": "nonsense"}).status_code == 400


def test_a_support_agent_decides_below_the_threshold_only(client):
    small = pending(client, above_threshold=False)
    assert small["amount"] < APPROVAL_THRESHOLD_AMOUNT

    assert client.post(
        f"/api/refunds/{small['id']}/decision",
        json={"decision": "approve", "reason": "ok"},
        headers=AGENT,
    ).status_code == 422  # the reason is too short to be a reason

    approved = client.post(
        f"/api/refunds/{small['id']}/decision",
        json={"decision": "approve", "reason": "photo evidence matches the damage report"},
        headers=AGENT,
    )
    assert approved.status_code == 201, approved.text
    assert approved.json()["status_after"] == "approved"

    # a decided request is done: the transition is not repeatable
    assert client.post(
        f"/api/refunds/{small['id']}/decision",
        json={"decision": "deny", "reason": "changed my mind about this one"},
        headers=AGENT,
    ).status_code == 409

    big = pending(client, above_threshold=True)
    assert big["amount"] >= APPROVAL_THRESHOLD_AMOUNT
    assert client.post(
        f"/api/refunds/{big['id']}/decision",
        json={"decision": "approve", "reason": "the customer has been waiting"},
        headers=AGENT,
    ).status_code == 403
    assert client.post(
        f"/api/refunds/{big['id']}/decision",
        json={"decision": "approve", "reason": "the customer has been waiting"},
        headers=FINANCE,
    ).status_code == 201


def test_only_finance_pays_out_and_only_an_approved_request(client):
    request_id = pending(client, above_threshold=False)["id"]
    assert client.post(
        f"/api/refunds/{request_id}/process",
        json={"reason": "payout batch 2026-08-02"},
        headers=FINANCE,
    ).status_code == 409  # still pending

    client.post(
        f"/api/refunds/{request_id}/decision",
        json={"decision": "approve", "reason": "duplicate charge confirmed"},
        headers=AGENT,
    )
    assert client.post(
        f"/api/refunds/{request_id}/process",
        json={"reason": "payout batch 2026-08-02"},
        headers=AGENT,
    ).status_code == 403

    paid = client.post(
        f"/api/refunds/{request_id}/process",
        json={"reason": "payout batch 2026-08-02"},
        headers=FINANCE,
    )
    assert paid.status_code == 201
    assert paid.json()["status_after"] == "processed"
    assert client.get(f"/api/refunds/{request_id}").json()["status"] == "processed"


def test_raising_a_request_is_audited_and_the_order_is_unique(client):
    body = {
        "customer_name": "Test Persona Zulu",
        "order_id": "ORD-2026-99999",
        "amount": 129.99,
        "reason_code": "damaged_item",
    }
    created = client.post("/api/refunds", json=body, headers=AGENT)
    assert created.status_code == 201
    request_id = created.json()["id"]
    assert created.json()["status"] == "pending"
    assert created.json()["requested_by"] == "riley@example.com"

    assert client.post("/api/refunds", json=body, headers=AGENT).status_code == 409
    assert client.post(
        "/api/refunds", json={**body, "order_id": "ORD-2026-99998", "amount": -5}, headers=AGENT
    ).status_code == 422

    trail = client.get(f"/api/refunds/{request_id}/audit").json()
    assert [e["action"] for e in trail] == ["created"]
    assert trail[0]["actor"] == "riley@example.com" and trail[0]["status_after"] == "pending"
    assert client.get("/api/refunds/999999/audit").status_code == 404


def test_the_dashboard_totals_match_the_queue(client):
    metrics = client.get("/api/metrics/summary").json()
    requests = client.get("/api/refunds").json()
    assert metrics["total_requests"] == len(requests)
    assert metrics["counts_by_status"]["processed"] == sum(
        1 for r in requests if r["status"] == "processed"
    )
    assert metrics["pending_amount"] == pytest.approx(
        sum(r["amount"] for r in requests if r["status"] == "pending"), abs=0.01
    )


def test_the_global_audit_is_append_only_and_newest_first(client):
    trail = client.get("/api/audit").json()
    assert trail == sorted(trail, key=lambda e: e["id"], reverse=True)
    # every decision made above is still there, none of them rewritten
    assert {"created", "approved", "processed"} <= {e["action"] for e in trail}


def test_the_health_probe_answers(client):
    assert client.get("/healthz").json()["status"] == "ok"
