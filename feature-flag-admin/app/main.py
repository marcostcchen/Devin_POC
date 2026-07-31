import hashlib
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import get_conn, init_db
from app.models import AuditEntry, EvaluationResult, Flag, FlagCreate, FlagUpdate

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Mocked identities: no real auth is in scope for this POC. The UI sends the
# selected user via the X-User header; roles are looked up here.
USERS = {
    "ada@example.com": "admin",
    "grace@example.com": "admin",
    "linus@example.com": "viewer",
}
DEFAULT_USER = "ada@example.com"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    seed()
    yield


app = FastAPI(title="Feature Flag Admin", lifespan=lifespan)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Actor:
    def __init__(self, email: str, role: str) -> None:
        self.email = email
        self.role = role

    def require_admin(self) -> None:
        if self.role != "admin":
            raise HTTPException(status_code=403, detail="viewer role is read-only")


def current_actor(x_user: Optional[str] = Header(default=None)) -> Actor:
    email = x_user or DEFAULT_USER
    role = USERS.get(email)
    if role is None:
        raise HTTPException(status_code=401, detail=f"unknown user {email}")
    return Actor(email, role)


def record_audit(
    conn: sqlite3.Connection, flag_id: int, flag_name: str, actor: Actor, action: str, detail: str = ""
) -> None:
    conn.execute(
        "INSERT INTO audit_log (flag_id, flag_name, actor, action, detail, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (flag_id, flag_name, actor.email, action, detail, now()),
    )


def row_to_flag(row: sqlite3.Row) -> Flag:
    return Flag(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        enabled=bool(row["enabled"]),
        rollout_percentage=row["rollout_percentage"],
        target_team=row["target_team"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def fetch_flag(conn: sqlite3.Connection, flag_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM flags WHERE id = ?", (flag_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="flag not found")
    return row


def seed() -> None:
    from app.db import connect

    conn = connect()
    try:
        count = conn.execute("SELECT COUNT(*) AS c FROM flags").fetchone()["c"]
        if count:
            return
        ts = now()
        conn.executemany(
            "INSERT INTO flags (name, description, enabled, rollout_percentage, target_team,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("new-checkout", "Rewritten checkout flow", 1, 100, "", ts, ts),
                ("dark-mode", "Dark theme in the web app", 0, 50, "", ts, ts),
                ("beta-search", "Vector search on the search page", 1, 100, "platform", ts, ts),
            ],
        )
        conn.commit()
    finally:
        conn.close()


@app.get("/api/me")
def me(actor: Actor = Depends(current_actor)) -> dict:
    return {"email": actor.email, "role": actor.role, "users": USERS}


@app.get("/api/flags", response_model=list[Flag])
def list_flags(conn: sqlite3.Connection = Depends(get_conn)) -> list[Flag]:
    rows = conn.execute("SELECT * FROM flags ORDER BY name").fetchall()
    return [row_to_flag(r) for r in rows]


@app.post("/api/flags", response_model=Flag, status_code=201)
def create_flag(
    payload: FlagCreate,
    actor: Actor = Depends(current_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> Flag:
    actor.require_admin()
    ts = now()
    try:
        cur = conn.execute(
            "INSERT INTO flags (name, description, enabled, rollout_percentage, target_team,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                payload.name,
                payload.description,
                int(payload.enabled),
                payload.rollout_percentage,
                payload.target_team,
                ts,
                ts,
            ),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"flag {payload.name} already exists")
    flag_id = int(cur.lastrowid)
    record_audit(
        conn,
        flag_id,
        payload.name,
        actor,
        "created",
        f"enabled={payload.enabled}, rollout={payload.rollout_percentage}%",
    )
    return row_to_flag(fetch_flag(conn, flag_id))


@app.patch("/api/flags/{flag_id}", response_model=Flag)
def update_flag(
    flag_id: int,
    payload: FlagUpdate,
    actor: Actor = Depends(current_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> Flag:
    actor.require_admin()
    row = fetch_flag(conn, flag_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return row_to_flag(row)

    sets, values, details = [], [], []
    for field, value in changes.items():
        old = row[field]
        if field == "enabled":
            value = int(value)
            old = bool(old)
            new_display = bool(value)
        else:
            new_display = value
        sets.append(f"{field} = ?")
        values.append(value)
        if old != (bool(value) if field == "enabled" else value):
            details.append(f"{field}: {old} -> {new_display}")
    values.extend([now(), flag_id])
    conn.execute(f"UPDATE flags SET {', '.join(sets)}, updated_at = ? WHERE id = ?", values)

    if details:
        action = "toggled" if "enabled" in changes else "updated"
        record_audit(conn, flag_id, row["name"], actor, action, "; ".join(details))
    return row_to_flag(fetch_flag(conn, flag_id))


@app.delete("/api/flags/{flag_id}", status_code=204)
def delete_flag(
    flag_id: int,
    actor: Actor = Depends(current_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> None:
    actor.require_admin()
    row = fetch_flag(conn, flag_id)
    record_audit(conn, flag_id, row["name"], actor, "deleted")
    conn.execute("DELETE FROM flags WHERE id = ?", (flag_id,))


@app.get("/api/flags/{flag_id}/audit", response_model=list[AuditEntry])
def flag_audit(
    flag_id: int, conn: sqlite3.Connection = Depends(get_conn)
) -> list[AuditEntry]:
    rows = conn.execute(
        "SELECT * FROM audit_log WHERE flag_id = ? ORDER BY id DESC", (flag_id,)
    ).fetchall()
    return [AuditEntry(**dict(r)) for r in rows]


@app.get("/api/audit", response_model=list[AuditEntry])
def all_audit(
    limit: int = Query(default=100, ge=1, le=1000),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[AuditEntry]:
    rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [AuditEntry(**dict(r)) for r in rows]


def bucket_of(flag_name: str, user_id: str) -> int:
    """Stable 0-99 bucket for a (flag, user) pair, so rollouts are sticky."""
    digest = hashlib.sha256(f"{flag_name}:{user_id}".encode()).hexdigest()
    return int(digest[:8], 16) % 100


@app.get("/api/evaluate/{name}", response_model=EvaluationResult)
def evaluate(
    name: str,
    user_id: str = Query(default="anonymous"),
    team: str = Query(default=""),
    conn: sqlite3.Connection = Depends(get_conn),
) -> EvaluationResult:
    row = conn.execute("SELECT * FROM flags WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="flag not found")
    flag = row_to_flag(row)

    if not flag.enabled:
        return EvaluationResult(
            flag=name, user_id=user_id, team=team, enabled=False, reason="flag disabled"
        )
    if flag.target_team and flag.target_team != team:
        return EvaluationResult(
            flag=name,
            user_id=user_id,
            team=team,
            enabled=False,
            reason=f"targeted at team '{flag.target_team}'",
        )
    bucket = bucket_of(name, user_id)
    if bucket >= flag.rollout_percentage:
        return EvaluationResult(
            flag=name,
            user_id=user_id,
            team=team,
            enabled=False,
            reason=f"bucket {bucket} outside {flag.rollout_percentage}% rollout",
        )
    return EvaluationResult(
        flag=name,
        user_id=user_id,
        team=team,
        enabled=True,
        reason=f"bucket {bucket} within {flag.rollout_percentage}% rollout",
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
