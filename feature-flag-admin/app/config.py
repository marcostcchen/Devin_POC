"""Runtime configuration, resolved once at import time from the environment."""

import os
from typing import Dict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Writable directory for state. Set by whatever runs the container; the app
#: folder when it is run from a checkout.
DATA_DIR = os.environ.get("DATA_DIR") or BASE_DIR

#: SQLite file backing the admin panel. Overridable so tests get a scratch DB.
DB_PATH = os.environ.get("FLAGS_DB_PATH", os.path.join(DATA_DIR, "flags.db"))

#: Vite build output. Absent until `npm run build` (or `run.sh`) has run.
WEB_DIST_DIR = os.path.join(BASE_DIR, "web", "dist")

#: Roles this app understands. "admin" may mutate, "viewer" is read-only.
ROLES = ("admin", "viewer")

#: `proxy-headers` when something in front of the app has authenticated the
#: caller and asserts them in `X-Auth-Request-*` headers - a reverse proxy, an
#: OIDC proxy, or the POC platform's ingress. Anything else means "nobody is
#: authenticating me", and the local roster below is used instead.
AUTH_MODE = os.environ.get("AUTH_MODE", "local")
PROXY_AUTH = AUTH_MODE == "proxy-headers"

#: Role for an authenticated caller who holds none of the mapped groups.
DEFAULT_ROLE = os.environ.get("AUTH_DEFAULT_ROLE", "viewer")


def _parse_group_roles(value: str) -> Dict[str, str]:
    """Read `group:role,group:role` into a mapping, most privileged first."""
    pairs = (item.split(":", 1) for item in value.split(",") if ":" in item)
    return {group.strip(): role.strip() for group, role in pairs}


#: Directory group -> role, in precedence order: the first group the caller
#: holds decides. Empty when nothing authenticates in front of the app.
GROUP_ROLES = _parse_group_roles(os.environ.get("AUTH_GROUP_ROLES", ""))

#: The local roster, used only when no proxy is authenticating: the browser
#: sends the selected address in an `X-User` header and the server trusts it.
USERS = {
    "ada@example.com": "admin",
    "grace@example.com": "admin",
    "linus@example.com": "viewer",
}
DEFAULT_USER = "ada@example.com"
