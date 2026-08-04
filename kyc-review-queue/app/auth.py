"""Identity and role-based access control.

There is deliberately no authentication: this is a prototype, and login is the
part every real deployment already has. The client states who it is with an
`X-User` header and the role is looked up in the roster below, which is what
the user switcher in the UI drives.
"""

from typing import Optional

from fastapi import Header, HTTPException

#: The roster. In a real deployment this is the identity provider.
USERS = {
    "nora@example.com": "analyst",
    "omar@example.com": "analyst",
    "priya@example.com": "senior_reviewer",
}
DEFAULT_USER = "nora@example.com"


class Actor:
    def __init__(self, email: str, role: str) -> None:
        self.email = email
        self.role = role

    @property
    def is_senior(self) -> bool:
        return self.role == "senior_reviewer"


def current_actor(x_user: Optional[str] = Header(default=None)) -> Actor:
    """Resolve the acting identity from the roster."""
    email = x_user or DEFAULT_USER
    role = USERS.get(email)
    if role is None:
        raise HTTPException(status_code=401, detail=f"unknown user {email}")
    return Actor(email, role)
