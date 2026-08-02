"""Example flags inserted on first start so the panel is never empty."""

from app.db import connect
from app.models import FlagCreate
from app.repositories import FlagRepository

EXAMPLES = [
    FlagCreate(name="new-checkout", description="Rewritten checkout flow", enabled=True),
    FlagCreate(
        name="dark-mode",
        description="Dark theme in the web app",
        enabled=False,
        rollout_percentage=50,
    ),
    FlagCreate(
        name="beta-search",
        description="Vector search on the search page",
        enabled=True,
        target_team="platform",
    ),
]


def seed_if_empty() -> None:
    """Insert `EXAMPLES` only when no flags exist; safe to call on every boot."""
    conn = connect()
    try:
        repository = FlagRepository(conn)
        if repository.list():
            return
        for example in EXAMPLES:
            repository.create(example.model_dump())
        conn.commit()
    finally:
        conn.close()
