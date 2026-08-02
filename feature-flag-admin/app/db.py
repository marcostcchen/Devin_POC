"""SQLite connection handling and schema.

FastAPI can run the two halves of a sync generator dependency on different
threadpool threads, so connections must not be pinned to their creating thread
(`check_same_thread=False`). A single process-wide lock serializes request
handling instead, which is plenty for an internal admin panel.
"""

import sqlite3
import threading
from typing import Iterator

from app.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 0,
    rollout_percentage INTEGER NOT NULL DEFAULT 100,
    target_team TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- flag_id is deliberately not a foreign key, and flag_name is copied in:
    -- audit history outlives the flag it describes.
    flag_id INTEGER NOT NULL,
    flag_name TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_flag_id ON audit_log(flag_id);
"""

_lock = threading.Lock()


def connect() -> sqlite3.Connection:
    """Open a row-dict connection to the configured database file."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_conn() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency yielding a connection; commits on success."""
    with _lock:
        conn = connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db() -> None:
    """Create tables and indexes if they do not exist yet."""
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
