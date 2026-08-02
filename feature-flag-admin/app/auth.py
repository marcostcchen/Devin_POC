"""Mocked identity and role-based access control.

There is deliberately no real authentication (out of scope for this POC): the
client states who it is via the `X-User` header and the server looks the role
up in `config.USERS`.
"""

from typing import Optional

from fastapi import Header

from app.config import DEFAULT_USER, USERS
from app.errors import PermissionDenied, UnknownUser


class Actor:
    """The identity performing a request, plus its role."""

    def __init__(self, email: str, role: str) -> None:
        self.email = email
        self.role = role

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def require_admin(self) -> None:
        """Raise `PermissionDenied` unless this actor may mutate flags."""
        if not self.is_admin:
            raise PermissionDenied("viewer role is read-only")


def current_actor(x_user: Optional[str] = Header(default=None)) -> Actor:
    """FastAPI dependency resolving the `X-User` header to an `Actor`."""
    email = x_user or DEFAULT_USER
    role = USERS.get(email)
    if role is None:
        raise UnknownUser(f"unknown user {email}")
    return Actor(email, role)
