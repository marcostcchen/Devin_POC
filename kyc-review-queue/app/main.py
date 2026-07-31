import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import connect, get_conn, init_db
from app.models import CaseDetail, CaseDocument, CaseEvent, CaseSummary, DecisionRequest
from app.seed import seed

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

ANALYST = "analyst"
SENIOR = "senior_reviewer"

# Mocked identities: no real auth is in scope for this POC. The UI sends the selected
# user via the X-User header; roles are looked up here. `.test` is a reserved TLD, so
# these addresses cannot belong to anyone.
USERS = {
    "ilva.analyst@compliance.test": ANALYST,
    "toren.analyst@compliance.test": ANALYST,
    "neris.senior@compliance.test": SENIOR,
}
DEFAULT_USER = "ilva.analyst@compliance.test"

RISK_ORDER = "CASE risk_level WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END"
STATUS_ORDER = "CASE status WHEN 'escalated' THEN 0 WHEN 'in_review' THEN 1 WHEN 'new' THEN 2 ELSE 3 END"
SORTS = {
    "risk": f"{RISK_ORDER}, submitted_at",
    "status": f"{STATUS_ORDER}, {RISK_ORDER}",
    "oldest": "submitted_at",
    "newest": "submitted_at DESC",
}

app = FastAPI(title="KYC Review Queue")


@app.on_event("startup")
def startup() -> None:
    init_db()
    seed(connect)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Actor:
    def __init__(self, email: str, role: str) -> None:
        self.email = email
        self.role = role

    @property
    def is_senior(self) -> bool:
        return self.role == SENIOR


def current_actor(x_user: Optional[str] = Header(default=None)) -> Actor:
    email = x_user or DEFAULT_USER
    role = USERS.get(email)
    if role is None:
        raise HTTPException(status_code=401, detail=f"unknown user {email}")
    return Actor(email, role)


def record_event(
    conn: sqlite3.Connection, case_id: int, reference: str, actor: Actor, action: str, reason: str = ""
) -> None:
    conn.execute(
        "INSERT INTO case_events (case_id, case_reference, actor, actor_role, action, reason, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (case_id, reference, actor.email, actor.role, action, reason, now()),
    )


def fetch_case(conn: sqlite3.Connection, case_id: int, actor: Actor) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="case not found")
    # Escalated cases live in a queue only senior reviewers can see, so an analyst gets
    # the same answer as for a case that does not exist.
    if row["status"] == "escalated" and not actor.is_senior:
        raise HTTPException(status_code=404, detail="case not found")
    return row


def to_summary(row: sqlite3.Row) -> CaseSummary:
    return CaseSummary(**{k: row[k] for k in CaseSummary.model_fields})


@app.get("/api/me")
def me(actor: Actor = Depends(current_actor)) -> dict:
    return {"email": actor.email, "role": actor.role, "users": USERS}


@app.get("/api/cases", response_model=list[CaseSummary])
def list_cases(
    risk: Optional[str] = Query(default=None, description="low | medium | high"),
    status: Optional[str] = Query(default=None, description="new | in_review | escalated | closed"),
    sort: str = Query(default="risk"),
    actor: Actor = Depends(current_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[CaseSummary]:
    if sort not in SORTS:
        raise HTTPException(status_code=400, detail=f"sort must be one of {', '.join(SORTS)}")
    where, params = [], []
    if risk:
        where.append("risk_level = ?")
        params.append(risk)
    if status:
        where.append("status = ?")
        params.append(status)
    if not actor.is_senior:
        where.append("status != 'escalated'")
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    rows = conn.execute(f"SELECT * FROM cases {clause} ORDER BY {SORTS[sort]}", params).fetchall()
    return [to_summary(r) for r in rows]


def build_detail(conn: sqlite3.Connection, row: sqlite3.Row) -> CaseDetail:
    case_id = row["id"]
    documents = conn.execute(
        "SELECT * FROM case_documents WHERE case_id = ? ORDER BY id", (case_id,)
    ).fetchall()
    history = conn.execute(
        "SELECT * FROM case_events WHERE case_id = ? ORDER BY id DESC", (case_id,)
    ).fetchall()
    return CaseDetail(
        **to_summary(row).model_dump(),
        document_number=row["document_number"],
        documents=[CaseDocument(**dict(d)) for d in documents],
        history=[CaseEvent(**dict(e)) for e in history],
    )


@app.get("/api/cases/{case_id}", response_model=CaseDetail)
def get_case(
    case_id: int,
    actor: Actor = Depends(current_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> CaseDetail:
    return build_detail(conn, fetch_case(conn, case_id, actor))


@app.post("/api/cases/{case_id}/claim", response_model=CaseSummary)
def claim_case(
    case_id: int,
    actor: Actor = Depends(current_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> CaseSummary:
    row = fetch_case(conn, case_id, actor)
    if row["status"] != "new":
        raise HTTPException(status_code=409, detail=f"case is already {row['status']}")
    conn.execute("UPDATE cases SET status = 'in_review', updated_at = ? WHERE id = ?", (now(), case_id))
    record_event(conn, case_id, row["reference"], actor, "in_review", "picked up for review")
    return to_summary(conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone())


@app.post("/api/cases/{case_id}/decision", response_model=CaseDetail)
def decide(
    case_id: int,
    payload: DecisionRequest,
    actor: Actor = Depends(current_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> CaseDetail:
    row = fetch_case(conn, case_id, actor)
    if row["status"] == "closed" and not actor.is_senior:
        raise HTTPException(status_code=403, detail="only a senior reviewer can override a closed case")
    if payload.decision == "escalate" and row["status"] == "escalated":
        raise HTTPException(status_code=409, detail="case is already escalated")

    overriding = row["status"] in ("escalated", "closed")
    if payload.decision == "escalate":
        status, outcome, action = "escalated", "", "escalated"
    else:
        status = "closed"
        outcome = "approved" if payload.decision == "approve" else "rejected"
        action = f"override_{outcome}" if overriding else outcome

    conn.execute(
        "UPDATE cases SET status = ?, outcome = ?, updated_at = ? WHERE id = ?",
        (status, outcome, now(), case_id),
    )
    record_event(conn, case_id, row["reference"], actor, action, payload.reason)
    # Returned even when the case just left the caller's queue (an analyst escalating),
    # so the UI can show the resulting state and history once.
    return build_detail(conn, conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone())


@app.get("/api/cases/{case_id}/history", response_model=list[CaseEvent])
def case_history(
    case_id: int,
    actor: Actor = Depends(current_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[CaseEvent]:
    fetch_case(conn, case_id, actor)
    rows = conn.execute("SELECT * FROM case_events WHERE case_id = ? ORDER BY id DESC", (case_id,)).fetchall()
    return [CaseEvent(**dict(r)) for r in rows]


@app.get("/api/audit", response_model=list[CaseEvent])
def audit(
    limit: int = Query(default=25, ge=1, le=500),
    actor: Actor = Depends(current_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[CaseEvent]:
    visible = "" if actor.is_senior else (
        " WHERE case_id IN (SELECT id FROM cases WHERE status != 'escalated')"
    )
    rows = conn.execute(
        f"SELECT * FROM case_events{visible} ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [CaseEvent(**dict(r)) for r in rows]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
