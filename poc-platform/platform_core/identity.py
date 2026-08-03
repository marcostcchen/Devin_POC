"""Mocked single sign-on.

One persona is chosen in the console and forwarded to every prototype, so a
reviewer switches identity once instead of three times. The forwarded headers
are the entire authentication story: any client that can reach a prototype
directly can set them itself. That is deliberate, and documented.
"""

from typing import Optional

from pydantic import BaseModel

from platform_core.config import Principal
from platform_core.manifest import Manifest

#: Cookie the console uses to remember the selected persona.
SESSION_COOKIE = "poc_platform_principal"

USER_HEADER = "X-Platform-User"
USER_NAME_HEADER = "X-Platform-User-Name"
ROLE_HEADER = "X-Platform-Role"
PLATFORM_ROLE_HEADER = "X-Platform-Platform-Role"
BASE_PATH_HEADER = "X-Platform-Base-Path"
REQUEST_ID_HEADER = "X-Platform-Request-Id"

#: Headers a prototype must never accept from a client: the gateway overwrites
#: them so a browser cannot spoof a persona the console did not select.
MANAGED_HEADERS = (
    USER_HEADER,
    USER_NAME_HEADER,
    ROLE_HEADER,
    PLATFORM_ROLE_HEADER,
    BASE_PATH_HEADER,
)


class ResolvedIdentity(BaseModel):
    """A persona seen through the lens of one prototype."""

    email: str
    display_name: str
    title: str
    platform_role: str
    app_id: str
    app_role: str


class IdentityService:
    """Resolves personas and turns them into the headers prototypes trust."""

    def __init__(self, principals: list[Principal], default_email: str) -> None:
        self._by_email = {p.email: p for p in principals}
        if default_email not in self._by_email:
            raise ValueError(f"default_principal {default_email!r} is not in principals")
        self._default_email = default_email

    @property
    def principals(self) -> list[Principal]:
        return list(self._by_email.values())

    @property
    def default(self) -> Principal:
        return self._by_email[self._default_email]

    def get(self, email: Optional[str]) -> Principal:
        """Resolve an email to a persona, falling back to the default."""
        if email is None:
            return self.default
        return self._by_email.get(email, self.default)

    def knows(self, email: str) -> bool:
        return email in self._by_email

    def resolve(self, principal: Principal, manifest: Manifest) -> ResolvedIdentity:
        """Map a persona onto the roles a specific prototype understands."""
        role = principal.app_roles.get(manifest.id, manifest.identity.default_role)
        if role not in manifest.identity.roles:
            # The app renamed or dropped a role; degrade to its least-privileged
            # default rather than sending something it will reject.
            role = manifest.identity.default_role
        return ResolvedIdentity(
            email=principal.email,
            display_name=principal.display_name,
            title=principal.title,
            platform_role=principal.platform_role,
            app_id=manifest.id,
            app_role=role,
        )

    def headers_for(
        self, principal: Principal, manifest: Manifest, request_id: str
    ) -> dict[str, str]:
        """Identity headers injected into every proxied request."""
        identity = self.resolve(principal, manifest)
        return {
            USER_HEADER: identity.email,
            USER_NAME_HEADER: identity.display_name,
            ROLE_HEADER: identity.app_role,
            PLATFORM_ROLE_HEADER: identity.platform_role,
            BASE_PATH_HEADER: manifest.base_path,
            REQUEST_ID_HEADER: request_id,
        }

    def unknown_roles(self, manifests: dict[str, Manifest]) -> list[str]:
        """Config drift: personas mapped to roles a prototype does not declare."""
        problems = []
        for principal in self.principals:
            for app_id, role in principal.app_roles.items():
                manifest = manifests.get(app_id)
                if manifest is None:
                    problems.append(f"{principal.email}: unknown app {app_id!r}")
                elif role not in manifest.identity.roles:
                    problems.append(
                        f"{principal.email}: role {role!r} is not declared by {app_id}"
                    )
        return problems
