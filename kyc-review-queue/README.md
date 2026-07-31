# KYC Review Queue (POC)

Minimal internal tool for compliance analysts to review and decide on customer
verification cases. FastAPI + SQLite + a single static HTML/JS page, no build step.

## Run

```bash
./run.sh          # creates .venv, installs deps, starts uvicorn on :8100
```

Then open http://localhost:8100. `kyc.db` is created on first start and seeded with 18
synthetic cases; `rm kyc.db` to reset. `PORT=9000 ./run.sh` to change the port.

## Seed data is fake, on purpose

Every case in `app/seed.py` is fabricated: invented names, `SYNTH-CUST-…` /
`SYNTH-DOC-…` identifiers, invented jurisdictions, `@compliance.test` reviewer
addresses (`.test` is a reserved TLD), and placeholder document *filenames* with no
files behind them. Risk levels and the "mock screening" notes are pre-assigned labels —
nothing is screened against anything. There is no real or real-looking PII: no SSNs,
no addresses, no dates of birth.

## What it does

- **Case queue** — pending cases with customer, risk level (low/medium/high) and status
  (new / in_review / escalated / closed). Filter by risk and status, sort by risk,
  status, or submission date.
- **Case detail** — mocked submitted documents (filenames only) plus a decision panel:
  Approve / Reject / Escalate with a required free-text reason. `new` cases can be
  claimed ("Start review") which moves them to `in_review`.
- **Audit trail** — every claim and decision writes an immutable `case_events` row
  (actor, role, action, reason, timestamp), shown in the case's History and in a global
  recent-activity feed. Nothing is ever updated in place.
- **RBAC** — `analyst` reviews and decides; `senior_reviewer` additionally sees the
  escalated queue and can override an already-closed or escalated case (recorded as
  `override_approved` / `override_rejected`). Switch identity with the "Acting as"
  dropdown; users and roles are hardcoded in `USERS` in `app/main.py`.
- **Escalation path** — an Escalate decision moves the case into a separate queue that
  only senior reviewers can see. For analysts the case disappears from the queue and
  `GET /api/cases/{id}` returns 404, so the escalated queue is not merely hidden in the UI.

There is no real auth: the client sends the selected identity in an `X-User` header,
which the server trusts. That is intentional for this POC.

## API

| Method | Path | Role |
| --- | --- | --- |
| GET | `/api/me` | any |
| GET | `/api/cases?risk=&status=&sort=` | any (analysts never see escalated) |
| GET | `/api/cases/{id}` | any (404 for analysts if escalated) |
| POST | `/api/cases/{id}/claim` | any |
| POST | `/api/cases/{id}/decision` | analyst; overrides on closed cases are senior-only |
| GET | `/api/cases/{id}/history` | any |
| GET | `/api/audit?limit=` | any |

Interactive docs at http://localhost:8100/docs.

## Tests

```bash
./.venv/bin/pip install pytest
./.venv/bin/python -m pytest tests -q
```

One smoke test covering queue filtering/sorting, claim, decisions, the required-reason
rule, audit ordering, escalation visibility, and senior override.

## Explicitly out of scope

Not attempted here, by instruction: real identity verification, document OCR and
sanctions/PEP screening (risk labels are seed data, not checks); real authentication;
any real or real-looking customer PII; deployment config; UI polish and tests beyond
smoke level.

## What making this production-real would take

The gap is mostly the parts that are mocked here. Decisions would have to hang off real
verification evidence rather than seed labels: document capture and storage in an
encrypted, access-logged store with OCR/MRZ extraction and tamper/liveness checks, plus
an integration with a screening vendor for sanctions/PEP/adverse-media, run
continuously rather than once, with match scores, fuzzy-name handling and a
four-eyes disposition flow for hits — and the risk level becomes a computed, versioned
score whose inputs are reproducible at the time of decision rather than a static
string. That in turn forces real authentication and authorisation (SSO/OIDC with
group-derived roles and MFA, replacing the trusted `X-User` header), real segregation of
duties (an analyst must not be able to override their own decision), and an audit trail
that regulators will accept: append-only, tamper-evident, exportable, retained for the
statutory period alongside a documented data-retention/erasure policy, since real cases
carry PII under GDPR and the equivalent local regimes. Operationally it needs Postgres
with migrations, per-case locking so two analysts cannot decide the same case, SLA
timers and queue assignment, case reopening on new information, and enough test
coverage (RBAC matrix, decision state machine, audit completeness) to change any of the
above safely.
