import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.auth import PROXY_AUTH, ROLES, USERS, Actor, current_actor
from app.config import APPROVAL_THRESHOLD_AMOUNT, SEED_REQUEST_COUNT
from app.db import get_conn, init_db
from app.models import (
    REASON_CODES,
    STATUSES,
    AuditEvent,
    DecisionCreate,
    Metrics,
    ProcessCreate,
    RefundRequest,
    RefundRequestCreate,
)
from app.seed import seed

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

SORT_COLUMNS = {
    "created_at": "created_at, id",
    "amount": "amount",
    "customer_name": "customer_name",
    "status": "CASE status WHEN 'pending' THEN 0 WHEN 'approved' THEN 1"
    " WHEN 'denied' THEN 2 ELSE 3 END, id",
}

app = FastAPI(title="Refunds Dashboard")


@app.on_event("startup")
def startup() -> None:
    init_db()
    seed()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def needs_finance(amount: float) -> bool:
    """The threshold rule: at or above the limit, only finance may decide."""
    return amount >= APPROVAL_THRESHOLD_AMOUNT


def row_to_request(row: sqlite3.Row) -> RefundRequest:
    return RefundRequest(
        **dict(row), requires_finance_approval=needs_finance(row["amount"])
    )


def fetch_request(conn: sqlite3.Connection, request_id: int) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM refund_requests WHERE id = ?", (request_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="refund request not found")
    return row


def record(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    actor: Actor,
    action: str,
    reason: str,
    status_after: str,
) -> AuditEvent:
    """Move a request to `status_after` and append the matching audit event."""
    ts = now()
    conn.execute(
        "UPDATE refund_requests SET status = ?, updated_at = ? WHERE id = ?",
        (status_after, ts, row["id"]),
    )
    cur = conn.execute(
        "INSERT INTO audit_events (refund_request_id, order_id, action, reason, actor,"
        " actor_role, status_before, status_after, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            row["id"],
            row["order_id"],
            action,
            reason,
            actor.email,
            actor.role,
            row["status"],
            status_after,
            ts,
        ),
    )
    entry = conn.execute(
        "SELECT * FROM audit_events WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return AuditEvent(**dict(entry))


@app.get("/healthz")
def healthz() -> dict:
    """Readiness probe, polled by whatever is running the app."""
    return {"status": "ok", "app": "refunds-dashboard", "proxy_auth": PROXY_AUTH}


@app.get("/api/me")
def me(actor: Actor = Depends(current_actor)) -> dict:
    return {
        "email": actor.email,
        "role": actor.role,
        "display_name": actor.display_name,
        # Behind a proxy the identity is not ours to change, so the local
        # switcher has nothing to offer.
        "users": {} if PROXY_AUTH else USERS,
        "proxy_auth": PROXY_AUTH,
    }


@app.get("/api/config")
def config() -> dict:
    """What the UI would otherwise have to duplicate."""
    return {
        "approval_threshold_amount": APPROVAL_THRESHOLD_AMOUNT,
        "statuses": STATUSES,
        "reason_codes": REASON_CODES,
        "roles": list(ROLES),
        "seed_request_count": SEED_REQUEST_COUNT,
    }


@app.get("/api/refunds", response_model=list[RefundRequest])
def list_requests(
    status: Optional[str] = Query(default=None),
    min_amount: Optional[float] = Query(default=None, ge=0),
    max_amount: Optional[float] = Query(default=None, ge=0),
    sort_by: str = Query(default="created_at", pattern="^(created_at|amount|customer_name|status)$"),
    sort_direction: str = Query(default="desc", pattern="^(asc|desc)$"),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[RefundRequest]:
    where, params = [], []
    if status and status != "all":
        if status not in STATUSES:
            raise HTTPException(status_code=400, detail=f"unknown status {status}")
        where.append("status = ?")
        params.append(status)
    if min_amount is not None:
        where.append("amount >= ?")
        params.append(min_amount)
    if max_amount is not None:
        where.append("amount <= ?")
        params.append(max_amount)
    sql = "SELECT * FROM refund_requests"
    if where:
        sql += " WHERE " + " AND ".join(where)
    order = SORT_COLUMNS[sort_by]
    rows = conn.execute(f"{sql} ORDER BY {order} {sort_direction.upper()}", params).fetchall()
    return [row_to_request(r) for r in rows]


@app.post("/api/refunds", response_model=RefundRequest, status_code=201)
def create_request(
    payload: RefundRequestCreate,
    actor: Actor = Depends(current_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> RefundRequest:
    """Raising a request is open to both roles; deciding it is not."""
    ts = now()
    try:
        cur = conn.execute(
            "INSERT INTO refund_requests (customer_name, order_id, amount, reason_code,"
            " status, requested_by, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)",
            (
                payload.customer_name,
                payload.order_id,
                payload.amount,
                payload.reason_code,
                actor.email,
                ts,
                ts,
            ),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409, detail=f"order {payload.order_id} already has a refund request"
        )
    row = conn.execute(
        "SELECT * FROM refund_requests WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    conn.execute(
        "INSERT INTO audit_events (refund_request_id, order_id, action, reason, actor,"
        " actor_role, status_before, status_after, created_at)"
        " VALUES (?, ?, 'created', ?, ?, ?, '', 'pending', ?)",
        (
            row["id"],
            row["order_id"],
            f"refund requested: {payload.reason_code}",
            actor.email,
            actor.role,
            ts,
        ),
    )
    return row_to_request(row)


@app.get("/api/refunds/{request_id}", response_model=RefundRequest)
def get_request(
    request_id: int, conn: sqlite3.Connection = Depends(get_conn)
) -> RefundRequest:
    return row_to_request(fetch_request(conn, request_id))


@app.get("/api/refunds/{request_id}/audit", response_model=list[AuditEvent])
def request_audit(
    request_id: int, conn: sqlite3.Connection = Depends(get_conn)
) -> list[AuditEvent]:
    fetch_request(conn, request_id)
    rows = conn.execute(
        "SELECT * FROM audit_events WHERE refund_request_id = ? ORDER BY id DESC", (request_id,)
    ).fetchall()
    return [AuditEvent(**dict(r)) for r in rows]


@app.post("/api/refunds/{request_id}/decision", response_model=AuditEvent, status_code=201)
def decide(
    request_id: int,
    payload: DecisionCreate,
    actor: Actor = Depends(current_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> AuditEvent:
    row = fetch_request(conn, request_id)
    if row["status"] != "pending":
        raise HTTPException(
            status_code=409, detail=f"request is {row['status']}, only a pending one can be decided"
        )
    if needs_finance(row["amount"]) and not actor.is_finance:
        raise HTTPException(
            status_code=403,
            detail=f"refunds of ${APPROVAL_THRESHOLD_AMOUNT:.2f} or more need a finance approver",
        )
    status_after = "approved" if payload.decision == "approve" else "denied"
    return record(conn, row, actor, status_after, payload.reason, status_after)


@app.post("/api/refunds/{request_id}/process", response_model=AuditEvent, status_code=201)
def process(
    request_id: int,
    payload: ProcessCreate,
    actor: Actor = Depends(current_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> AuditEvent:
    """The mocked payout: it moves money nowhere, it only closes the loop."""
    if not actor.is_finance:
        raise HTTPException(status_code=403, detail="only a finance approver can process a payout")
    row = fetch_request(conn, request_id)
    if row["status"] != "approved":
        raise HTTPException(
            status_code=409, detail=f"request is {row['status']}, only an approved one can be paid out"
        )
    return record(conn, row, actor, "processed", payload.reason, "processed")


@app.get("/api/metrics/summary", response_model=Metrics)
def metrics(conn: sqlite3.Connection = Depends(get_conn)) -> Metrics:
    rows = conn.execute("SELECT status, amount FROM refund_requests").fetchall()
    counts = {status: 0 for status in STATUSES}
    totals = dict(counts)
    for row in rows:
        counts[row["status"]] += 1
        totals[row["status"]] += row["amount"]
    amounts = [row["amount"] for row in rows]
    return Metrics(
        total_requests=len(rows),
        counts_by_status=counts,
        total_refunded_amount=round(totals["processed"], 2),
        total_approved_amount=round(totals["approved"], 2),
        pending_amount=round(totals["pending"], 2),
        pending_count=counts["pending"],
        average_request_amount=round(sum(amounts) / len(amounts), 2) if amounts else 0.0,
    )


@app.get("/api/audit", response_model=list[AuditEvent])
def audit(
    limit: int = Query(default=50, ge=1, le=1000),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[AuditEvent]:
    rows = conn.execute(
        "SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [AuditEvent(**dict(r)) for r in rows]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
