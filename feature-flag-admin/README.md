# Feature Flag Admin (POC)

Minimal internal tool for toggling features without a deploy.
FastAPI + SQLite backend, React (Vite + TypeScript) frontend.

## Run

```bash
cd feature-flag-admin
./run.sh          # venv + pip install, npm install + vite build, uvicorn on :8000
```

Then open http://localhost:8000. The DB (`flags.db`) is created and seeded with
three example flags on first start; delete it to reset. `PORT=9000 ./run.sh` to
change the port.

For frontend work, run the API and the Vite dev server side by side — the dev
server proxies `/api` to :8000 and gives you hot reload:

```bash
./.venv/bin/uvicorn app.main:app --reload   # terminal 1
cd web && npm run dev                       # terminal 2, http://localhost:5173
```

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

There is no real auth: the client sends the selected identity in an `X-User` header,
which the server trusts. That is intentional for this POC.

## The panel

A sticky top bar (identity switcher + current role), summary counts, then a two-column
workspace: the flag list on the left, the *Evaluate* panel and global activity feed in a
right-hand rail that collapses under the list on narrow screens. Each flag row has an
on/off switch, a rollout bar with the stored percentage and team, inline targeting and
description editors, and a *History* button that expands the audit trail beneath the row.
The toolbar filters by name/description and by state, and reveals the create form.

## Layout

```
app/
  main.py          FastAPI app: routers, error handling, serves web/dist
  config.py        DB path, static paths, the mocked user roster
  auth.py          Actor + X-User dependency, admin check
  models.py        Pydantic request/response schemas
  db.py            SQLite schema and connection handling
  repositories.py  All SQL for flags and audit entries
  services.py      Use cases: permissions + persistence + audit writing
  targeting.py     Pure evaluation: bucketing, team and rollout rules
  routers/         One module per resource (flags, audit, evaluation, identity)
  seed.py          Example flags for an empty database
web/src/
  api.ts           Typed fetch client (adds the X-User header)
  types.ts         Mirrors the pydantic schemas
  format.ts        Display helpers (timestamp formatting)
  index.css        Design tokens and layout
  hooks/           useAdminPanel: identity, flags, activity, error state
  components/      IdentityBar, StatsBar, ErrorBanner, FlagTable, FlagRow,
                   NewFlagForm, AuditList, EvaluatePanel
tests/             API smoke tests + unit tests for the targeting logic
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
./.venv/bin/python -m pytest tests -q     # API smoke tests + targeting unit tests
(cd web && npm run typecheck)             # TypeScript
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
