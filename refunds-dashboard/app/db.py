import os
import sqlite3
import threading
from typing import Iterator

# $DATA_DIR is the one writable path the app is given wherever it runs; from a
# checkout it falls back to the app folder.
_DEFAULT_DIR = os.environ.get("DATA_DIR") or os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.environ.get("REFUNDS_DB_PATH", os.path.join(_DEFAULT_DIR, "refunds.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS refund_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    order_id TEXT NOT NULL UNIQUE,
    -- REAL, not integer cents: a prototype shortcut, listed in the README
    amount REAL NOT NULL,
    reason_code TEXT NOT NULL,
    status TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- deliberately not a foreign key: the audit trail outlives the row it describes
    refund_request_id INTEGER NOT NULL,
    order_id TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    actor TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    status_before TEXT NOT NULL,
    status_after TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_events_request ON audit_events(refund_request_id);
"""


# FastAPI runs sync generator dependencies across threadpool threads (the setup and
# teardown halves can land on different threads), so connections must not be pinned to
# the creating thread. A single lock serializes request handling instead.
_lock = threading.Lock()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_conn() -> Iterator[sqlite3.Connection]:
    with _lock:
        conn = connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
