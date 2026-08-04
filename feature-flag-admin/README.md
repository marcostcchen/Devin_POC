# Feature Flag Admin (POC)

Minimal internal tool for toggling features without a deploy. FastAPI + SQLite,
with a plain HTML/JavaScript panel served from `static/` — no build step.

## Run

```bash
cd feature-flag-admin
./run.sh          # venv + pip install, uvicorn on :8000
```

Or as the container the platform deploys:

```bash
docker build -t poc/feature-flag-admin:0.1.0 .
docker run --rm -p 8000:8000 poc/feature-flag-admin:0.1.0
```

The DB (`flags.db`, or `$DATA_DIR/flags.db`) is created and seeded with three
example flags on first start; delete it to reset. `PORT=9000 ./run.sh` to change
the port.

### On the POC platform

Deployed by [`platform/projects/feature-flag-admin.yaml`](../platform/projects/feature-flag-admin.yaml)
at its own hostname. The platform sets `$PORT` and `$DATA_DIR`; nothing else
changes, and the app behaves exactly as it does standalone. There is no platform
code in this repository.

## What it does

- **CRUD for flags**: name, description, enabled/disabled. Create, edit, delete in the UI.
- **Audit log**: every create/toggle/update/delete records actor + timestamp + what
  changed (`enabled: False -> True`). Per-flag via the *History* button
  (`GET /api/flags/{id}/audit`), plus a global recent-activity feed (`GET /api/audit`).
  Entries outlive the flag they describe.
- **RBAC**: `admin` may mutate, `viewer` is read-only — mutating controls are disabled
  and the API returns 403. Switch identity with the "Acting as" dropdown.
- **Targeting**: per-flag rollout percentage and optional target team.
  `GET /api/evaluate/{name}?user_id=...&team=...` returns the resolved value plus a
  reason. Bucketing is `sha256(flag:user_id) % 100`, so a user's assignment is sticky
  across evaluations and independent per flag. The *Evaluate* panel exercises this.

There is no authentication: the client sends the selected identity in an
`X-User` header and the server trusts it. That is intentional for this POC — the
roles are real and enforced server-side, but who you are is not.

## The panel

A header with the identity switcher and current role, summary counts, then a
toolbar that filters by name/description and by state and reveals the create
form. The flag list gives each flag an on/off button, a rollout bar, the target
team, and a *History* button that expands its audit trail beneath the row;
clicking the description, the rollout *edit* button or the team cell edits that
field. A right-hand rail holds the *Evaluate* panel and the global activity
feed, and drops under the list on narrow screens. For a viewer every mutating
control is disabled, and the API refuses the call anyway.

## Layout

```
app/
  main.py          FastAPI app: routers, error handling, serves static/
  config.py        DB path, static paths, roles, the user roster
  auth.py          Actor resolution from the roster, admin check
  models.py        Pydantic request/response schemas
  db.py            SQLite schema and connection handling
  repositories.py  All SQL for flags and audit entries
  services.py      Use cases: permissions + persistence + audit writing
  targeting.py     Pure evaluation: bucketing, team and rollout rules
  routers/         One module per resource (flags, audit, evaluation, identity)
  seed.py          Example flags for an empty database
static/            The panel: index.html and app.js, no build step
tests/             API smoke tests, identity mapping, targeting unit tests
Dockerfile         Non-root, read-only root filesystem, $PORT, $DATA_DIR
```

## API

| Method | Path | Role |
| --- | --- | --- |
| GET | `/api/me` | any |
| GET | `/api/flags` | any |
| POST | `/api/flags` | admin |
| PATCH | `/api/flags/{id}` | admin |
| DELETE | `/api/flags/{id}` | admin |
| GET | `/api/flags/{id}/audit` | any |
| GET | `/api/audit?limit=` | any |
| GET | `/api/evaluate/{name}?user_id=&team=` | any |

Interactive docs at http://localhost:8000/docs.

## Tests

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/python -m pytest tests -q
```

## What I'd build next

With more time the priority would be turning this from an admin UI into something
services can safely depend on: a real identity layer (OIDC/SSO with group-derived
roles instead of the trusted `X-User` header), a versioned read path for SDKs —
either a cached `/api/flags/evaluate-batch` endpoint or a streaming/etag-based
config document so clients don't hammer SQLite per evaluation — and a richer
targeting model (ordered rules over arbitrary user attributes, with an explicit
allow/deny list layered above the percentage rollout, plus a dry-run "who would
this affect?" preview). Operationally I'd add Postgres and Alembic migrations,
per-flag change approval and scheduled/temporary flags with automatic expiry so
stale flags get cleaned up, an audit log export, and enough tests (component
tests for the React panel, rollout distribution properties, RBAC matrix, API
contract) to refactor safely.
