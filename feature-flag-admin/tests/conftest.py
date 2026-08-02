"""Test fixtures: every test module gets its own throwaway SQLite file."""

import os
import tempfile

os.environ.setdefault("FLAGS_DB_PATH", os.path.join(tempfile.mkdtemp(), "test.db"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ADMIN = {"X-User": "ada@example.com"}
VIEWER = {"X-User": "linus@example.com"}


@pytest.fixture()
def client() -> TestClient:
    """A client against the real app, with the schema created and seeded."""
    with TestClient(app) as test_client:
        yield test_client
