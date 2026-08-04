import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.auth import USERS, Actor, current_actor
from app.db import get_conn, init_db
from app.models import Case, DecisionCreate, DecisionEntry
from app.seed import seed

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# action -> status the case ends up in
OUTCOMES = {"claim": "in_review", "approve": "closed", "reject": "closed", "escalate": "escalated"}

app = FastAPI(title="KYC Review Queue")


@app.on_event("startup")
def startup() -> None:
    init_db()
    seed()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def row_to_case(row: sqlite3.Row) -> Case:
    return Case(
        id=row["id"],
        reference=row["reference"],
        customer_name=row["customer_name"],
        country=row["country"],
        document_type=row["document_type"],
        document_number=row["document_number"],
        risk_level=row["risk_level"],
        status=row["status"],
        documents=[d for d in row["documents"].split("|") if d],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def fetch_case(conn: sqlite3.Connection, case_id: int, actor: Actor) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="case not found")
    if row["status"] == "escalated" and not actor.is_senior:
        # Escalated cases leave the analyst queue entirely, so a 404 keeps their
        # existence out of the analyst's view rather than just blocking the action.
        raise HTTPException(status_code=404, detail="case not found")
    return row


@app.get("/healthz")
def healthz() -> dict:
    """Readiness probe, polled by whatever is running the app."""
    return {"status": "ok", "app": "kyc-review-queue"}


@app.get("/api/me")
def me(actor: Actor = Depends(current_actor)) -> dict:
    return {
        "email": actor.email,
        "role": actor.role,
        # The roster the UI's switcher renders.
        "users": USERS,
    }


@app.get("/api/cases", response_model=list[Case])
def list_cases(
    risk_level: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    sort: str = Query(default="risk", pattern="^(risk|created|name|status)$"),
    actor: Actor = Depends(current_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[Case]:
    where, params = [], []
    if risk_level:
        where.append("risk_level = ?")
        params.append(risk_level)
    if status:
        where.append("status = ?")
        params.append(status)
    if not actor.is_senior:
        where.append("status != 'escalated'")
    order = {
        # highest risk and least-progressed cases first: that is the work queue order
        "risk": "CASE risk_level WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id",
        "status": "CASE status WHEN 'new' THEN 0 WHEN 'in_review' THEN 1"
        " WHEN 'escalated' THEN 2 ELSE 3 END, id",
        "created": "created_at, id",
        "name": "customer_name",
    }[sort]
    sql = "SELECT * FROM cases"
    if where:
        sql += " WHERE " + " AND ".join(where)
    rows = conn.execute(f"{sql} ORDER BY {order}", params).fetchall()
    return [row_to_case(r) for r in rows]


@app.get("/api/cases/{case_id}", response_model=Case)
def get_case(
    case_id: int,
    actor: Actor = Depends(current_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> Case:
    return row_to_case(fetch_case(conn, case_id, actor))


@app.post("/api/cases/{case_id}/decisions", response_model=DecisionEntry, status_code=201)
def decide(
    case_id: int,
    payload: DecisionCreate,
    actor: Actor = Depends(current_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> DecisionEntry:
    row = fetch_case(conn, case_id, actor)
    status_before = row["status"]
    if status_before == "closed" and not actor.is_senior:
        raise HTTPException(
            status_code=403, detail="only a senior reviewer can override a closed case"
        )
    if payload.action == "escalate" and status_before == "escalated":
        raise HTTPException(status_code=409, detail="case is already escalated")

    status_after = OUTCOMES[payload.action]
    ts = now()
    conn.execute(
        "UPDATE cases SET status = ?, updated_at = ? WHERE id = ?", (status_after, ts, case_id)
    )
    cur = conn.execute(
        "INSERT INTO decisions (case_id, case_reference, actor, actor_role, action, reason,"
        " status_before, status_after, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            case_id,
            row["reference"],
            actor.email,
            actor.role,
            "override" if status_before == "closed" and payload.action != "claim" else payload.action,
            payload.reason,
            status_before,
            status_after,
            ts,
        ),
    )
    entry = conn.execute("SELECT * FROM decisions WHERE id = ?", (cur.lastrowid,)).fetchone()
    return DecisionEntry(**dict(entry))


@app.get("/api/cases/{case_id}/history", response_model=list[DecisionEntry])
def case_history(
    case_id: int,
    actor: Actor = Depends(current_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[DecisionEntry]:
    fetch_case(conn, case_id, actor)
    rows = conn.execute(
        "SELECT * FROM decisions WHERE case_id = ? ORDER BY id DESC", (case_id,)
    ).fetchall()
    return [DecisionEntry(**dict(r)) for r in rows]


@app.get("/api/audit", response_model=list[DecisionEntry])
def audit(
    limit: int = Query(default=50, ge=1, le=1000),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[DecisionEntry]:
    rows = conn.execute("SELECT * FROM decisions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [DecisionEntry(**dict(r)) for r in rows]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
