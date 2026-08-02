"""Runtime configuration, resolved once at import time from the environment."""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: SQLite file backing the admin panel. Overridable so tests get a scratch DB.
DB_PATH = os.environ.get("FLAGS_DB_PATH", os.path.join(BASE_DIR, "flags.db"))

#: Vite build output. Absent until `npm run build` (or `run.sh`) has run.
WEB_DIST_DIR = os.path.join(BASE_DIR, "web", "dist")

#: Identities the panel can act as. No real auth is in scope for this POC: the
#: browser sends the selected address in an `X-User` header and the server
#: trusts it. Roles are "admin" (may mutate) and "viewer" (read-only).
USERS = {
    "ada@example.com": "admin",
    "grace@example.com": "admin",
    "linus@example.com": "viewer",
}
DEFAULT_USER = "ada@example.com"
