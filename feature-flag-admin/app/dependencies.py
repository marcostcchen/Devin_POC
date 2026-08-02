"""Shared FastAPI dependencies wiring requests to the service layer."""

import sqlite3

from fastapi import Depends

from app.db import get_conn
from app.services import FlagService


def get_service(conn: sqlite3.Connection = Depends(get_conn)) -> FlagService:
    """Build a `FlagService` bound to this request's connection."""
    return FlagService(conn)
