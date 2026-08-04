# Refunds Dashboard (POC)

Internal tool for support and finance staff to review, approve and track customer
refund requests. FastAPI + SQLite + a single static HTML/JS page, no build step —
the same stack as the other projects in this repository.

> Rebuilt on FastAPI from the original React + Express prototype's README and
> [`docs/API.md`](docs/API.md). The behaviour is the same; the payloads are now
> `snake_case` and health lives at `/healthz`, as the
> [project contract](../platform/docs/project-contract.md) requires.

## Run

```bash
./run.sh          # creates .venv, installs deps, starts uvicorn on :8000
```

Or as the container the platform deploys:

```bash
docker build -t poc/refunds-dashboard:0.1.0 .
docker run --rm -p 8000:8000 poc/refunds-dashboard:0.1.0
```

Open http://localhost:8000. `refunds.db` (or `$DATA_DIR/refunds.db`) is created and
seeded with 23 synthetic requests on first start; `rm refunds.db` to reset.
`PORT=9000 ./run.sh` to change the port.

### On the POC platform

Deployed by [`platform/projects/refunds-dashboard.yaml`](../platform/projects/refunds-dashboard.yaml)
at its own hostname. The platform sets `AUTH_MODE=proxy-headers`, so the acting
user comes from the `X-Auth-Request-*` headers the ingress injects and
`AUTH_GROUP_ROLES` maps the caller's directory groups onto `support_agent` or
`finance_approver`. Standalone, nothing changes here — the local roster and the
`X-User` header come back. There is no platform code in this repository.

## What it does

- **Requests queue**: customer, order id, amount, reason code and status
  (pending / approved / denied / processed). Filter by status and amount range,
  sort by date, amount, customer or status.
- **Summary dashboard**: total refunded (processed), approved awaiting payout,
  pending count and value, denied count and the average request amount.
- **Decision flow**: approve or deny a pending request with a **required** reason
  of at least 5 characters (422 otherwise). An approved request moves to
  `processed` through a mocked payout — no money moves anywhere.
- **Threshold rule**: requests at or above `APPROVAL_THRESHOLD_AMOUNT` (default
  $200) need a finance approver, whoever raised them; a support agent deciding
  one gets a 403. The queue marks those rows *finance*.
- **RBAC**: `support_agent` raises requests and decides small ones;
  `finance_approver` decides anything and is the only role that can pay out.
  Switch identity with the "Acting as" dropdown; the standalone roster is
  hardcoded in `USERS` in `app/auth.py`.
- **Audit trail**: every create, approve, deny and payout appends an event with
  actor, role, reason, the status transition and a timestamp — per request
  (`GET /api/refunds/{id}/audit`) and as a global feed (`GET /api/audit`).

There is no real auth: standalone, the client sends the selected identity in an
`X-User` header and the server trusts it; behind a proxy it trusts the proxy's
`X-Auth-Request-*` headers instead. That is intentional for this POC.

## Seed data

All 23 requests are fabricated (`app/seed.py`) by a fixed-seed PRNG, so every
fresh database looks identical: placeholder names ("Test Persona Alpha"),
`ORD-2026-xxxxx` order ids, amounts between $5 and $500 and reason codes from a
fixed list. Decided rows get the audit history they would have accumulated, so
the trail is not empty on a fresh install. No real customer, card or payment data.

## Configuration

| Variable                    | Default             | Purpose                                            |
| --------------------------- | ------------------- | -------------------------------------------------- |
| `PORT`                      | `8000`              | Port uvicorn listens on                            |
| `DATA_DIR`                  | the app folder      | Writable directory for the SQLite file             |
| `REFUNDS_DB_PATH`           | `$DATA_DIR/refunds.db` | SQLite file                                     |
| `APPROVAL_THRESHOLD_AMOUNT` | `200`               | Amount at/above which finance sign-off is required |
| `SEED_REQUEST_COUNT`        | `23`                | Synthetic requests generated on first start        |
| `AUTH_MODE`                 | `local`             | `proxy-headers` when something authenticates in front |
| `AUTH_DEFAULT_ROLE`         | `support_agent`     | Role for a caller holding none of the mapped groups |
| `AUTH_GROUP_ROLES`          | empty               | `group:role,...`, most privileged first            |

## API

| Method | Path | Role |
| --- | --- | --- |
| GET | `/api/me` | any |
| GET | `/api/config` | any |
| GET | `/api/refunds?status=&min_amount=&max_amount=&sort_by=&sort_direction=` | any |
| POST | `/api/refunds` | any |
| GET | `/api/refunds/{id}` | any |
| GET | `/api/refunds/{id}/audit` | any |
| POST | `/api/refunds/{id}/decision` | support agent below the threshold, finance for anything |
| POST | `/api/refunds/{id}/process` | finance approver |
| GET | `/api/metrics/summary` | any |
| GET | `/api/audit?limit=` | any |

Full request/response shapes in [`docs/API.md`](docs/API.md); interactive docs at
http://localhost:8000/docs.

## Tests

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/python -m pytest tests -q
```

Smoke tests covering queue filtering/sorting, the required reason, the threshold
rule, the payout restriction, duplicate orders, dashboard totals and the
append-only audit trail, plus tests for the two identity modes and the
group-to-role mapping.

## Out of scope (deliberately not built)

- **No payment processor integration.** "Mark as processed" only flips the status
  and writes an audit event. No Stripe (or any other) call, no money movement.
- **No financial reconciliation.** Nothing is matched against a ledger, bank feed
  or accounting system, and there is no double-entry bookkeeping.
- **No real authentication.** Identity is a trusted header, from the platform's
  mocked SSO or the local roster.
- **No real customer or payment data.** Everything is synthetic.
- Other gaps: no pagination (the queue loads every matching row), no soft delete
  or edit of requests, no currency other than USD, and amounts are stored as
  SQLite `REAL` rather than integer cents.

## What making this production-real would take

Making this real starts at the money boundary: the mocked `process` action would
be replaced by an idempotent payment-processor integration (e.g. Stripe refunds)
keyed on the original charge, with retries, webhook-driven status reconciliation
and a queue/worker so a failed or pending payout can never be silently lost —
which in turn means storing amounts as integer cents with an explicit currency
and a real state machine for partial refunds, chargebacks and reversals. Around
that, reconciliation would need to match every payout against the ledger and the
processor's settlement reports, with a daily exception report for mismatches.
Compliance drives the rest: real authentication and SSO with server-enforced
roles instead of trusted headers, dollar-amount approval limits and segregation
of duties (the requester cannot approve their own refund), a tamper-evident,
immutable and retained audit log (append-only storage, hash chaining or WORM,
7-year retention is typical for financial records) capturing before/after values,
plus PII handling, encryption at rest, and access logging on customer data.
Operationally it would need Postgres instead of SQLite, migrations, pagination
and indexing for large queues, structured logging/metrics/alerting, rate limits,
and a real test suite (unit, integration and end-to-end) gated in CI.
