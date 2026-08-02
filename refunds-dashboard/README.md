# Refunds Dashboard

Internal tool for support and finance staff to review, approve and track customer
refund requests. It ships with synthetic seed data — there is no real customer,
payment or ledger data anywhere in this prototype.

- **Frontend:** React 18 + Vite
- **Backend:** Node.js + Express
- **Storage:** SQLite (`better-sqlite3`), file created on first start

## What the app does

| Capability        | Notes                                                                                                                                                                            |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Requests queue    | Pending/approved/denied/processed requests with customer, order ID, amount, reason code and status. Filter by status and amount range, sort by amount, date, customer or status. |
| Summary dashboard | Total refunded (processed), approved awaiting payout, pending count and value, denied count, average request amount.                                                             |
| Decision flow     | Approve / deny with a **required** free-text reason (validated client- and server-side). Approved requests move to `processed` through a mocked payout action.                   |
| Audit trail       | Every create/approve/deny/process writes an append-only audit event with actor, role, reason and timestamp; shown in the request detail panel.                                   |
| RBAC (mocked)     | Support agent: view + raise requests, decide small refunds. Finance approver: decide anything, and the only role that can process a payout.                                      |
| Threshold rule    | Requests **at or above `APPROVAL_THRESHOLD_AMOUNT` (default $200)** require finance approver sign-off, even when a support agent raised them.                                    |

## Running it locally

Requires Node.js 20+.

```bash
cd refunds-dashboard
npm install          # root tooling (concurrently, prettier)
npm run setup        # installs server + client deps and creates both .env files
npm run dev          # starts the API (:4000) and the Vite dev server (:5173)
```

Then open <http://localhost:5173>.

For a single-process run — client built and served by the API, the same way the
platform starts it — use `./run.sh` and open <http://localhost:4000>.

### Under the POC platform

This app is also a platform prototype ([`poc.yaml`](poc.yaml)): start it from the
[platform console](../poc-platform/) and it is served at `/apps/refunds-dashboard/`,
the persona selected there becomes the acting user (the role switcher turns into a
read-only label), and the SQLite file moves to the platform's disposable state
directory. Standalone, nothing changes.

Prefer one terminal per service? Run these instead of `npm run dev`:

```bash
npm run dev:server   # http://localhost:4000
npm run dev:client   # http://localhost:5173
```

The SQLite file is created at `server/data/refunds.db` on first start and seeded
with 23 synthetic refund requests. Delete the file to regenerate the dataset.

Other useful commands:

```bash
npm run lint         # ESLint (server + client)
npm run format       # Prettier (defaults, no custom rules)
npm run smoke        # smoke-level API checks against a running server
```

## Configuration

Both services read a `.env` file (created from `.env.example` by `npm run setup`).
Nothing below is hardcoded in the source.

**`server/.env`**

| Variable                    | Default                 | Purpose                                            |
| --------------------------- | ----------------------- | -------------------------------------------------- |
| `PORT`                      | `4000`                  | Express port                                       |
| `CLIENT_ORIGIN`             | `http://localhost:5173` | Allowed CORS origin                                |
| `DATABASE_PATH`             | `./data/refunds.db`     | SQLite file, relative to `server/`                 |
| `APPROVAL_THRESHOLD_AMOUNT` | `200`                   | Amount at/above which finance sign-off is required |
| `SEED_REQUEST_COUNT`        | `23`                    | Synthetic requests generated on first start        |

**`client/.env`**

| Variable            | Default                     | Purpose              |
| ------------------- | --------------------------- | -------------------- |
| `VITE_PORT`         | `5173`                      | Vite dev server port |
| `VITE_API_BASE_URL` | `http://localhost:4000/api` | Backend base URL     |

## Folder structure at a glance

```
refunds-dashboard/
├── package.json            # root scripts: setup, dev (both services), lint, format, smoke
├── scripts/
│   ├── init-env.js         # copies .env.example -> .env for both services
│   └── smoke-test.js       # smoke-level API checks (not a test suite)
├── docs/
│   └── API.md              # API reference
├── server/
│   └── src/
│       ├── index.js            # entrypoint: init db, start http server
│       ├── app.js              # express app wiring
│       ├── config/env.js       # .env loading + typed config object
│       ├── constants/          # roles, statuses, reason codes
│       ├── db/                 # connection, schema, synthetic seed data
│       ├── repositories/       # SQL only (refund requests, audit events)
│       ├── services/           # business rules (RBAC, threshold, transitions, metrics)
│       ├── routes/             # HTTP layer: /api/refunds, /api/metrics, /api/config
│       ├── middleware/         # mocked actor, role guard, id validation, error handler
│       ├── validation/         # request payload / query validation
│       └── utils/              # AppError, asyncHandler, money rounding
└── client/
    └── src/
        ├── App.jsx             # page composition
        ├── api/                # fetch wrapper + endpoint functions
        ├── context/            # mocked role/actor context
        ├── hooks/              # data loading (queue + metrics, history, config)
        ├── components/
        │   ├── layout/         # header, role switcher
        │   ├── dashboard/      # summary metric cards
        │   ├── queue/          # filters, table, rows, new-request form
        │   ├── detail/         # detail panel, decision form, audit trail
        │   └── common/         # status badge, error banner, empty state
        ├── utils/              # formatters, client-side validation
        └── styles/global.css
```

Layering rule of thumb on the backend: **routes** validate and shape HTTP,
**services** own business rules, **repositories** own SQL. Routes never touch the
database directly.

## API reference

See [`docs/API.md`](docs/API.md) for the full table of endpoints, request bodies
and status codes.

## Seed data

`server/src/db/seed.js` generates 23 fake requests on first start using a
deterministic PRNG (fixed seed), so every fresh database looks identical:
synthetic names, `ORD-2026-xxxxx` order IDs, amounts between $5 and $500 and
reason codes from a fixed list. Approved/denied/processed rows also get matching
audit history so the trail is not empty on a fresh install.

## Known limitations / out of scope

These were intentionally **not** built:

- **No payment processor integration.** "Mark as processed" only flips the status
  and writes an audit event. No Stripe (or any other) call, no money movement.
- **No financial reconciliation.** Nothing is matched against a ledger, bank feed
  or accounting system, and there is no double-entry bookkeeping.
- **No real authentication.** The role switcher is a UI mock that sets
  `x-user-role` / `x-user-name` headers; the server trusts them blindly. Anyone
  can call the API as any role.
- **No real customer or payment data.** All data is synthetic; there are no card
  numbers, emails or addresses, even fictionalized ones.
- **No test suite.** `npm run smoke` covers a happy path plus the main validation
  and RBAC guards; there are no unit tests and no CI.
- Other gaps: no pagination (the queue loads every matching row), no server-side
  concurrency control beyond status checks, no soft delete or edit of requests,
  no currency handling other than USD, and amounts are stored as SQLite `REAL`
  rather than integer cents.

## What it would take to make this production-real

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
