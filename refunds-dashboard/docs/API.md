# API reference

Base URL: `http://localhost:8000` standalone, `https://refunds.<platform domain>`
on the POC platform. All responses are JSON; FastAPI errors are
`{"detail": "..."}` (a list of field errors for a 422).

## Identity headers (mocked — not authentication)

Which pair is read depends on `AUTH_MODE`; see the [project contract](../../platform/docs/project-contract.md).

| Header                   | Values                                          | Mode            |
| ------------------------ | ----------------------------------------------- | --------------- |
| `X-User`                 | an address from the local roster in `app/auth.py` | standalone      |
| `X-Auth-Request-Email`   | the caller, asserted by the proxy               | `proxy-headers` |
| `X-Auth-Request-User`    | display name                                    | `proxy-headers` |
| `X-Auth-Request-Groups`  | comma-separated groups, mapped by `AUTH_GROUP_ROLES` | `proxy-headers` |

An unknown user (standalone) or a request the proxy did not authenticate returns `401`.

## Endpoints

| Method | Route                        | Purpose                                                                          | Body / query                                                                                                                                            |
| ------ | ---------------------------- | -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET`  | `/healthz`                   | Liveness/readiness probe                                                         | —                                                                                                                                                       |
| `GET`  | `/api/me`                    | Acting identity, role, and the roster when nothing authenticates in front        | —                                                                                                                                                       |
| `GET`  | `/api/config`                | Threshold, statuses, reason codes and roles, so the UI does not duplicate them   | —                                                                                                                                                       |
| `GET`  | `/api/refunds`               | List requests, filtered and sorted                                               | Query: `status` (`pending`\|`approved`\|`denied`\|`processed`\|`all`), `min_amount`, `max_amount`, `sort_by` (`created_at`\|`amount`\|`customer_name`\|`status`), `sort_direction` (`asc`\|`desc`) |
| `POST` | `/api/refunds`               | Raise a request (either role)                                                    | `{ "customer_name": "Test Persona Zulu", "order_id": "ORD-2026-00042", "amount": 129.99, "reason_code": "damaged_item" }`                                |
| `GET`  | `/api/refunds/{id}`          | A single request                                                                 | —                                                                                                                                                       |
| `GET`  | `/api/refunds/{id}/audit`    | That request's audit trail, newest first                                         | —                                                                                                                                                       |
| `POST` | `/api/refunds/{id}/decision` | Approve or deny a **pending** request                                            | `{ "decision": "approve" \| "deny", "reason": "at least 5 characters" }`                                                                                |
| `POST` | `/api/refunds/{id}/process`  | Mocked payout: move an **approved** request to `processed` (finance only)        | `{ "reason": "at least 5 characters" }`                                                                                                                 |
| `GET`  | `/api/metrics/summary`       | Aggregates behind the dashboard cards                                            | —                                                                                                                                                       |
| `GET`  | `/api/audit?limit=`          | Global audit feed, newest first                                                  | —                                                                                                                                                       |

## Status codes

| Code  | When                                                                                                                    |
| ----- | ------------------------------------------------------------------------------------------------------------------------- |
| `200` | Successful read                                                                                                         |
| `201` | Request created, or a decision/payout recorded                                                                          |
| `400` | Unknown `status` filter                                                                                                 |
| `401` | Unknown user, or no identity asserted by the proxy                                                                      |
| `403` | A support agent deciding at/above the threshold, or anyone but finance calling `/process`                               |
| `404` | Unknown request id                                                                                                      |
| `409` | Duplicate `order_id`, deciding a request that is not pending, or paying out one that is not approved                    |
| `422` | Invalid body: missing/short reason (< 5 characters), non-positive amount, unknown reason code, non-numeric id           |

## Examples

```bash
# Pending queue, biggest first
curl "http://localhost:8000/api/refunds?status=pending&sort_by=amount&sort_direction=desc"

# Approve as a finance approver
curl -X POST http://localhost:8000/api/refunds/3/decision \
  -H 'content-type: application/json' -H 'X-User: dana@example.com' \
  -d '{"decision":"approve","reason":"photo evidence matches the damage report"}'

# Mocked payout
curl -X POST http://localhost:8000/api/refunds/3/process \
  -H 'content-type: application/json' -H 'X-User: dana@example.com' \
  -d '{"reason":"payout batch 2026-08-02"}'
```

## Response shapes

```jsonc
// GET /api/refunds
[ { "id": 3, "customer_name": "Test Persona Alpha", "order_id": "ORD-2026-10111",
    "amount": 456.37, "reason_code": "damaged_item", "status": "pending",
    "requested_by": "riley@example.com", "created_at": "2026-01-02T09:00:00+00:00",
    "updated_at": "2026-01-02T09:00:00+00:00", "requires_finance_approval": true } ]

// GET /api/refunds/{id}/audit
[ { "id": 7, "refund_request_id": 3, "order_id": "ORD-2026-10111", "action": "approved",
    "reason": "photo evidence matches the damage report", "actor": "dana@example.com",
    "actor_role": "finance_approver", "status_before": "pending", "status_after": "approved",
    "created_at": "2026-01-03T10:12:00+00:00" } ]

// GET /api/metrics/summary
{ "total_requests": 23,
  "counts_by_status": { "pending": 15, "approved": 3, "denied": 2, "processed": 3 },
  "total_refunded_amount": 626.0, "total_approved_amount": 1487.26,
  "pending_amount": 2611.44, "pending_count": 15, "average_request_amount": 208.0 }
```
