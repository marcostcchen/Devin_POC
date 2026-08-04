"""Identity and role-based access control.

There is deliberately no real authentication (out of scope for this POC). The
identity arrives in a header the server trusts, from one of two sources:

* behind an authenticating proxy (`AUTH_MODE=proxy-headers`) the caller and
  their directory groups arrive as `X-Auth-Request-*`, and the groups are
  mapped to this app's roles by `AUTH_GROUP_ROLES`. The proxy overwrites these
  headers on every request, so a browser cannot set them itself;
* standalone, the client states who it is via `X-User` and the role is looked
  up in `config.USERS`.

Nothing here knows what the proxy is. On the POC platform it is the ingress
calling the portal; in front of a real deployment it would be oauth2-proxy.
"""

from typing import Optional

from fastapi import Header

from app.config import DEFAULT_ROLE, DEFAULT_USER, GROUP_ROLES, PROXY_AUTH, ROLES, USERS
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


def role_for_groups(groups: str) -> str:
    """First mapped group wins; an unmapped caller gets the least privilege."""
    held = {group.strip() for group in groups.split(",") if group.strip()}
    for group, role in GROUP_ROLES.items():
        if group in held and role in ROLES:
            return role
    return DEFAULT_ROLE if DEFAULT_ROLE in ROLES else ROLES[-1]


def current_actor(
    x_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_groups: Optional[str] = Header(default=None),
) -> Actor:
    """Resolve the acting identity from the proxy or the local roster."""
    if PROXY_AUTH:
        if not x_auth_request_email:
            raise UnknownUser("no identity was asserted by the authenticating proxy")
        return Actor(
            x_auth_request_email,
            role_for_groups(x_auth_request_groups or ""),
            x_auth_request_user or "",
        )

    email = x_user or DEFAULT_USER
    role = USERS.get(email)
    if role is None:
        raise UnknownUser(f"unknown user {email}")
    return Actor(email, role)
