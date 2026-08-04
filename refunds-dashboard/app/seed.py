"""Synthetic seed data.

Everything here is fabricated by a fixed-seed PRNG, so every fresh database
looks identical: placeholder names, `ORD-2026-xxxxx` order ids and amounts
between $5 and $500. No real customer, card, payment or ledger data.
"""

import random
from datetime import datetime, timedelta, timezone

from app.config import APPROVAL_THRESHOLD_AMOUNT, SEED_REQUEST_COUNT
from app.models import REASON_CODES

NAMES = [
    "Test Persona Alpha",
    "Test Persona Bravo",
    "Test Persona Charlie",
    "Test Persona Delta",
    "Test Persona Echo",
    "Test Persona Foxtrot",
    "Test Persona Golf",
    "Test Persona Hotel",
    "Test Persona India",
    "Test Persona Juliett",
    "Test Persona Kilo",
    "Test Persona Lima",
]
AGENTS = ["riley@example.com", "sam@example.com"]
FINANCE = "dana@example.com"

# Enough of the queue is already decided that the dashboard and the audit trail
# are not empty on a fresh install.
STATUS_CYCLE = ["pending"] * 6 + ["approved", "denied", "processed"]


def seed() -> None:
    from app.db import connect

    conn = connect()
    try:
        if conn.execute("SELECT COUNT(*) AS c FROM refund_requests").fetchone()["c"]:
            return
        rng = random.Random(20260802)
        base = datetime.now(timezone.utc) - timedelta(days=SEED_REQUEST_COUNT)
        for i in range(1, SEED_REQUEST_COUNT + 1):
            status = STATUS_CYCLE[i % len(STATUS_CYCLE)]
            amount = round(rng.uniform(5, 500), 2)
            agent = AGENTS[i % len(AGENTS)]
            created = base + timedelta(days=i, minutes=i * 13)
            updated = created if status == "pending" else created + timedelta(hours=5)
            cur = conn.execute(
                "INSERT INTO refund_requests (customer_name, order_id, amount, reason_code,"
                " status, requested_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    rng.choice(NAMES),
                    f"ORD-2026-{10000 + i * 37}",
                    amount,
                    rng.choice(REASON_CODES),
                    status,
                    agent,
                    created.isoformat(timespec="seconds"),
                    updated.isoformat(timespec="seconds"),
                ),
            )
            _seed_history(conn, cur.lastrowid, status, amount, agent, created, updated)
        conn.commit()
    finally:
        conn.close()


def _seed_history(conn, request_id, status, amount, agent, created, updated) -> None:
    """The trail a request would have accumulated to reach `status`."""
    order_id = conn.execute(
        "SELECT order_id FROM refund_requests WHERE id = ?", (request_id,)
    ).fetchone()["order_id"]
    decider = FINANCE if amount >= APPROVAL_THRESHOLD_AMOUNT else agent
    decider_role = "finance_approver" if decider == FINANCE else "support_agent"
    trail = [("created", "raised from the support queue", agent, "support_agent", "", "pending")]
    if status in ("approved", "processed"):
        trail.append(("approved", "evidence matches the claim", decider, decider_role, "pending", "approved"))
    if status == "denied":
        trail.append(("denied", "outside the returns window", decider, decider_role, "pending", "denied"))
    if status == "processed":
        trail.append(("processed", "payout batch 2026-08-01", FINANCE, "finance_approver", "approved", "processed"))
    conn.executemany(
        "INSERT INTO audit_events (refund_request_id, order_id, action, reason, actor, actor_role,"
        " status_before, status_after, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                request_id,
                order_id,
                action,
                reason,
                actor,
                role,
                before,
                after,
                (created if i == 0 else updated).isoformat(timespec="seconds"),
            )
            for i, (action, reason, actor, role, before, after) in enumerate(trail)
        ],
    )
