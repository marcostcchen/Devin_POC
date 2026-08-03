"""Runtime configuration, resolved once at import time from the environment."""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Set by the POC platform when it supervises this app. See ../poc.yaml and
#: ../poc-platform/docs/platform-contract.md; empty when running standalone.
PLATFORM_MANAGED = os.environ.get("PLATFORM_MANAGED") == "1"
PLATFORM_BASE_PATH = os.environ.get("PLATFORM_BASE_PATH", "").rstrip("/")
PLATFORM_DATA_DIR = os.environ.get("PLATFORM_DATA_DIR", "")
PLATFORM_GATEWAY_URL = os.environ.get("PLATFORM_GATEWAY_URL", "")

#: SQLite file backing the admin panel. Overridable so tests get a scratch DB;
#: under the platform it lives in the platform's disposable state directory.
DB_PATH = os.environ.get(
    "FLAGS_DB_PATH", os.path.join(PLATFORM_DATA_DIR or BASE_DIR, "flags.db")
)

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

#: Roles this app understands, mirrored in `poc.yaml` so the platform can map
#: its personas onto them.
ROLES = ("admin", "viewer")
DEFAULT_ROLE = "viewer"
