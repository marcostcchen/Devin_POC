# KYC Review Queue (POC)

Minimal internal tool for compliance analysts to triage and decide customer
verification cases. FastAPI + SQLite + a single static HTML/JS page, no build step.

## Run

```bash
./run.sh          # creates .venv, installs deps, starts uvicorn on :8000
```

Or as the container the platform deploys:

```bash
docker build -t poc/kyc-review-queue:0.1.0 .
docker run --rm -p 8000:8000 poc/kyc-review-queue:0.1.0
```

Open http://localhost:8000. `kyc.db` (or `$DATA_DIR/kyc.db`) is created and
seeded with 18 synthetic cases on first start; `rm kyc.db` to reset.
`PORT=9000 ./run.sh` to change the port.

### On the POC platform

Deployed by [`platform/projects/kyc-review-queue.yaml`](../platform/projects/kyc-review-queue.yaml)
at its own hostname. The platform sets `$PORT` and `$DATA_DIR`; nothing else
changes, and the app behaves exactly as it does standalone. There is no platform
code in this repository.

## What it does

- **Case queue**: reference, customer, risk level (low/medium/high, pre-assigned in
  seed data) and status (new / in_review / escalated / closed). Filter by risk and
  status, sort by risk, status, creation date or name.
- **Case detail**: mocked submitted documents (filenames only, nothing is stored) and
  a decision panel — Approve / Reject / Escalate / Claim, each requiring a free-text
  reason. The API rejects a blank reason with a 422.
- **Audit trail**: every decision records actor, role, action, reason, the status
  transition and a timestamp; shown in the case's *History* panel
  (`GET /api/cases/{id}/history`) and a global feed (`GET /api/audit`).
- **RBAC**: `analyst` reviews and decides; `senior_reviewer` can additionally see
  escalated cases and override closed ones (the override is recorded as its own audit
  entry with `action=override`). Switch identity with the "Acting as" dropdown; the
  roster is hardcoded in `USERS` in `app/auth.py`.
- **Escalation path**: escalating moves the case to `escalated`, which drops it out of
  the analyst's queue and out of `GET /api/cases/{id}` for analysts (404), leaving it
  visible only to the senior reviewer — filter *Status: escalated* to work that queue.

There is no authentication: the client sends the selected identity in an
`X-User` header and the server trusts it. That is intentional for this POC — the
roles are real and enforced server-side, but who you are is not.

## Seed data

All 18 cases are fabricated (`app/seed.py`): placeholder names ("Test Persona Alpha"),
fictional countries, document numbers of the form `SYNTH-PAS-1001`, and document
filenames that point at nothing. No real customer PII, and deliberately nothing shaped
like a real SSN, passport number or address.

## API

| Method | Path | Role |
| --- | --- | --- |
| GET | `/api/me` | any |
| GET | `/api/cases?risk_level=&status=&sort=` | any (escalated hidden from analyst) |
| GET | `/api/cases/{id}` | any (404 on escalated for analyst) |
| POST | `/api/cases/{id}/decisions` | analyst; overriding a closed case requires senior |
| GET | `/api/cases/{id}/history` | any |
| GET | `/api/audit?limit=` | any |

Interactive docs at http://localhost:8000/docs.

## Tests

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/python -m pytest tests -q
```

A smoke test covering queue filtering/ordering, the required reason, the audit
trail, the analyst/senior RBAC split and the escalation path, plus tests for the
two identity modes and the group-to-role mapping.

## Out of scope (deliberately not built)

No real identity verification, document OCR or sanctions/PEP screening — `risk_level`
is a static label in the seed data, not the output of any check. No real
authentication. No real (or real-looking) customer PII. Nothing beyond a
container and a health check for deployment, no polish beyond basic usability.

## What making this production-real would take

The three mocked pillars are the real work. Risk would have to come from an actual
pipeline — a document verification/OCR vendor (Onfido, Persona, Jumio) returning
structured extraction plus tamper and liveness signals, sanctions/PEP/adverse-media
screening against a licensed list provider with ongoing rescreening and fuzzy-match
adjudication (matches are a queue of their own), and a scoring layer that turns those
signals into a risk level with a recorded, reproducible rationale rather than a
hardcoded string. The trusted `X-User` header would be replaced by SSO/OIDC with
group-derived roles, per-action authorization, and enforced maker-checker so nobody
approves their own escalation. Case data becomes regulated PII, which changes the
storage story completely: Postgres with migrations, encryption at rest, field-level
access controls, real document storage with signed short-lived URLs, retention and
deletion schedules per jurisdiction, and an append-only, tamper-evident audit log
(hash-chained or WORM) exportable for regulators — the current `decisions` table is
the right shape but is mutable and lives in a local SQLite file. Around that you would
need SLA/aging alerts on the queue, case assignment and locking so two analysts don't
work the same case, a document viewer, reviewer QA sampling and metrics, and a real
test suite (RBAC matrix, state-machine transitions, audit completeness) before any of
it could be trusted with a compliance decision.
