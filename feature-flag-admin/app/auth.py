"""Identity and role-based access control.

There is deliberately no authentication: this is a prototype, and login is the
part every real deployment already has. The client states who it is with an
`X-User` header and the role is looked up in `config.USERS`, which is what the
user switcher in the UI drives.
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
    """Resolve the acting identity from the roster."""
    email = x_user or DEFAULT_USER
    role = USERS.get(email)
    if role is None:
        raise UnknownUser(f"unknown user {email}")
    return Actor(email, role)
