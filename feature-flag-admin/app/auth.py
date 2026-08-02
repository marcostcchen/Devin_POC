"""Mocked identity and role-based access control.

There is deliberately no real authentication (out of scope for this POC). The
identity arrives in a header the server trusts, from one of two sources:

* under the POC platform, the gateway injects `X-Platform-User` /
  `X-Platform-Role` for the persona selected in its console (and strips any
  copy the browser tried to send);
* standalone, the client states who it is via `X-User` and the role is looked
  up in `config.USERS`.
"""

from typing import Optional

from fastapi import Header

from app.config import DEFAULT_USER, PLATFORM_MANAGED, ROLES, USERS
from app.errors import PermissionDenied, UnknownUser


class Actor:
    """The identity performing a request, plus its role."""

    def __init__(self, email: str, role: str, display_name: str = "") -> None:
        self.email = email
        self.role = role
        self.display_name = display_name or email

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def require_admin(self) -> None:
        """Raise `PermissionDenied` unless this actor may mutate flags."""
        if not self.is_admin:
            raise PermissionDenied("viewer role is read-only")


def current_actor(
    x_user: Optional[str] = Header(default=None),
    x_platform_user: Optional[str] = Header(default=None),
    x_platform_user_name: Optional[str] = Header(default=None),
    x_platform_role: Optional[str] = Header(default=None),
) -> Actor:
    """Resolve the acting identity from the platform or the local roster."""
    if PLATFORM_MANAGED and x_platform_user:
        # The platform owns the roster, so the email need not be in USERS; the
        # role still has to be one this app implements.
        if x_platform_role not in ROLES:
            raise UnknownUser(f"platform sent unsupported role {x_platform_role!r}")
        return Actor(x_platform_user, x_platform_role, x_platform_user_name or "")

    email = x_user or DEFAULT_USER
    role = USERS.get(email)
    if role is None:
        raise UnknownUser(f"unknown user {email}")
    return Actor(email, role)
