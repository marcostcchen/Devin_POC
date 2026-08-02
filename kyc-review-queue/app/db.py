import os
import sqlite3
import threading
from typing import Iterator

DB_PATH = os.environ.get(
    "KYC_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "kyc.db")
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference TEXT NOT NULL UNIQUE,
    customer_name TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT '',
    document_type TEXT NOT NULL DEFAULT '',
    document_number TEXT NOT NULL DEFAULT '',
    risk_level TEXT NOT NULL,
    status TEXT NOT NULL,
    documents TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- deliberately not a foreign key: the audit trail outlives the case it describes
    case_id INTEGER NOT NULL,
    case_reference TEXT NOT NULL,
    actor TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    status_before TEXT NOT NULL,
    status_after TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_decisions_case_id ON decisions(case_id);
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
