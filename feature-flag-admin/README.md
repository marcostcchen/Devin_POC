# Feature Flag Admin (POC)

Minimal internal tool for toggling features without a deploy. FastAPI + SQLite +
a single static HTML/JS page, no build step.

## Run

```bash
cd feature-flag-admin
./run.sh          # creates .venv, installs deps, starts uvicorn on :8000
```

Then open http://localhost:8000. The DB (`flags.db`) is created and seeded with
three example flags on first start. `PORT=9000 ./run.sh` to change the port.

## What it does

- **CRUD for flags**: name, description, enabled/disabled. Create/edit/delete in the UI.
- **Audit log**: every create/toggle/update/delete records actor + timestamp + what
  changed. Per-flag via the *History* button (`GET /api/flags/{id}/audit`), and a
  global recent-activity feed (`GET /api/audit`).
- **RBAC**: `admin` can mutate, `viewer` is read-only (mutating buttons are disabled
  and the API returns 403). Switch identity with the "Acting as" dropdown; users and
  roles are hardcoded in `USERS` in `app/main.py`.
- **Targeting**: per-flag rollout percentage and optional target team.
  `GET /api/evaluate/{name}?user_id=...&team=...` returns the resolved value plus a
  reason. Bucketing is `sha256(flag:user_id) % 100`, so a user's assignment is
  sticky across evaluations and independent per flag. The *Evaluate* panel in the UI
  exercises this.

There is no real auth: the client sends the selected identity in an `X-User` header,
which the server trusts. That is intentional for this POC.

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
./.venv/bin/python -m pytest tests -q
```

One smoke test covering CRUD, audit ordering, RBAC denial, and targeting.

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
stale flags get cleaned up, an audit log export, and enough tests (rollout
distribution properties, RBAC matrix, API contract) to refactor safely.
