"""Runtime configuration, resolved once at import time from the environment."""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Writable directory for state. Set by whatever runs the container; the app
#: folder when it is run from a checkout.
DATA_DIR = os.environ.get("DATA_DIR") or BASE_DIR

#: SQLite file backing the admin panel. Overridable so tests get a scratch DB.
DB_PATH = os.environ.get("FLAGS_DB_PATH", os.path.join(DATA_DIR, "flags.db"))

#: The panel: plain HTML and JavaScript, served as-is with no build step.
STATIC_DIR = os.path.join(BASE_DIR, "static")

#: Roles this app understands. "admin" may mutate, "viewer" is read-only.
ROLES = ("admin", "viewer")

#: The roster. There is deliberately no authentication: the browser sends the
#: selected address in an `X-User` header and the server trusts it. In a real
#: deployment this is the identity provider.
USERS = {
    "ada@example.com": "admin",
    "grace@example.com": "admin",
    "linus@example.com": "viewer",
}
DEFAULT_USER = "ada@example.com"
