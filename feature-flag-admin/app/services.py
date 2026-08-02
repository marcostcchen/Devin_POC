"""Use cases: permission checks, persistence and audit writing in one place.

Routers translate HTTP to these calls and nothing else, so every mutation gets
audited no matter which endpoint triggered it.
"""

import sqlite3
from typing import Optional

from app.auth import Actor
from app.models import AuditEntry, Flag, FlagCreate, FlagUpdate
from app.repositories import AuditRepository, FlagRepository


def _describe(before: Flag, changes: dict) -> list[str]:
    """Render the changed fields as `field: old -> new`, skipping no-ops."""
    details = []
    for field, new_value in changes.items():
        old_value = getattr(before, field)
        if old_value != new_value:
            details.append(f"{field}: {old_value} -> {new_value}")
    return details


class FlagService:
    """Flag CRUD with RBAC enforcement and audit logging."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.flags = FlagRepository(conn)
        self.audit = AuditRepository(conn)

    def list_flags(self) -> list[Flag]:
        return self.flags.list()

    def get_by_name(self, name: str) -> Flag:
        return self.flags.get_by_name(name)

    def create(self, payload: FlagCreate, actor: Actor) -> Flag:
        actor.require_admin()
        flag = self.flags.create(payload.model_dump())
        self.audit.record(
            flag,
            actor.email,
            "created",
            f"enabled={flag.enabled}, rollout={flag.rollout_percentage}%",
        )
        return flag

    def update(self, flag_id: int, payload: FlagUpdate, actor: Actor) -> Flag:
        """Apply the fields the client actually sent, and audit what changed.

        The action is `toggled` when the on/off switch moved and `updated`
        otherwise, so the activity feed reads the way engineers scan it.
        """
        actor.require_admin()
        before = self.flags.get(flag_id)
        changes = payload.model_dump(exclude_unset=True)
        details = _describe(before, changes)
        if not details:
            return before

        stored = {**changes}
        if "enabled" in stored:
            stored["enabled"] = int(stored["enabled"])
        after = self.flags.update(flag_id, stored)

        action = "toggled" if "enabled" in changes else "updated"
        self.audit.record(after, actor.email, action, "; ".join(details))
        return after

    def delete(self, flag_id: int, actor: Actor) -> None:
        """Delete a flag; its audit trail is intentionally left behind."""
        actor.require_admin()
        flag = self.flags.get(flag_id)
        self.audit.record(flag, actor.email, "deleted")
        self.flags.delete(flag_id)

    def history(self, flag_id: Optional[int] = None, limit: int = 100) -> list[AuditEntry]:
        return self.audit.list(flag_id=flag_id, limit=limit)
