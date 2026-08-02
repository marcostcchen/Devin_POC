"""SQL access for flags and audit entries.

This is the only layer that knows about tables and columns; everything above it
works with the pydantic models in `app.models`.
"""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from app.errors import DuplicateFlag, FlagNotFound
from app.models import AuditEntry, Flag

FLAG_COLUMNS = ("name", "description", "enabled", "rollout_percentage", "target_team")


def now() -> str:
    """Current UTC timestamp, second precision, as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _to_flag(row: sqlite3.Row) -> Flag:
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


class FlagRepository:
    """CRUD over the `flags` table."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list(self) -> list[Flag]:
        rows = self._conn.execute("SELECT * FROM flags ORDER BY name").fetchall()
        return [_to_flag(row) for row in rows]

    def get(self, flag_id: int) -> Flag:
        row = self._conn.execute("SELECT * FROM flags WHERE id = ?", (flag_id,)).fetchone()
        if row is None:
            raise FlagNotFound("flag not found")
        return _to_flag(row)

    def get_by_name(self, name: str) -> Flag:
        row = self._conn.execute("SELECT * FROM flags WHERE name = ?", (name,)).fetchone()
        if row is None:
            raise FlagNotFound("flag not found")
        return _to_flag(row)

    def create(self, values: Mapping[str, Any]) -> Flag:
        """Insert a flag. Raises `DuplicateFlag` if the name is taken."""
        timestamp = now()
        columns = ", ".join([*FLAG_COLUMNS, "created_at", "updated_at"])
        placeholders = ", ".join(["?"] * (len(FLAG_COLUMNS) + 2))
        row = [*(values[column] for column in FLAG_COLUMNS), timestamp, timestamp]
        try:
            cursor = self._conn.execute(
                f"INSERT INTO flags ({columns}) VALUES ({placeholders})", row
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateFlag(f"flag {values['name']} already exists") from exc
        return self.get(int(cursor.lastrowid))

    def update(self, flag_id: int, changes: Mapping[str, Any]) -> Flag:
        """Apply a partial update; `changes` keys must be flag columns."""
        if not changes:
            return self.get(flag_id)
        assignments = ", ".join(f"{column} = ?" for column in changes)
        values = [*changes.values(), now(), flag_id]
        self._conn.execute(
            f"UPDATE flags SET {assignments}, updated_at = ? WHERE id = ?", values
        )
        return self.get(flag_id)

    def delete(self, flag_id: int) -> None:
        self._conn.execute("DELETE FROM flags WHERE id = ?", (flag_id,))


class AuditRepository:
    """Append-only access to the `audit_log` table."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def record(self, flag: Flag, actor_email: str, action: str, detail: str = "") -> None:
        self._conn.execute(
            "INSERT INTO audit_log (flag_id, flag_name, actor, action, detail, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (flag.id, flag.name, actor_email, action, detail, now()),
        )

    def list(self, flag_id: Optional[int] = None, limit: int = 100) -> list[AuditEntry]:
        """Newest-first entries, optionally restricted to a single flag."""
        if flag_id is None:
            rows = self._conn.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM audit_log WHERE flag_id = ? ORDER BY id DESC LIMIT ?",
                (flag_id, limit),
            ).fetchall()
        return [AuditEntry(**dict(row)) for row in rows]
