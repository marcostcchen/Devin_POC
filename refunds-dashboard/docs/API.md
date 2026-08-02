# API reference

Base URL: `http://localhost:4000/api` (configurable via `PORT` / `VITE_API_BASE_URL`).

All responses are JSON. Errors use the shape:

```json
{
  "error": {
    "message": "Validation failed",
    "details": [{ "field": "reason", "message": "reason is required" }]
  }
}
```

## Identity headers (mocked — not authentication)

| Header        | Values                                        | Default                       |
| ------------- | --------------------------------------------- | ----------------------------- |
| `x-user-role` | `support_agent`, `finance_approver`           | `support_agent`               |
| `x-user-name` | any display name, recorded in the audit trail | `agent.demo` / `finance.demo` |

An unknown role returns `400`.

## Endpoints

| Method | Route                       | Purpose                                                                             | Expected body / query                                                                                                                                                                        |
| ------ | --------------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET`  | `/api/health`               | Liveness check                                                                      | —                                                                                                                                                                                            |
| `GET`  | `/api/config`               | Threshold amount, statuses, reason codes, roles (so the UI does not duplicate them) | —                                                                                                                                                                                            |
| `GET`  | `/api/refunds`              | List refund requests, filtered and sorted                                           | Query: `status` (`pending`\|`approved`\|`denied`\|`processed`\|`all`), `minAmount`, `maxAmount`, `sortBy` (`createdAt`\|`amount`\|`customerName`\|`status`), `sortDirection` (`asc`\|`desc`) |
| `POST` | `/api/refunds`              | Raise a new refund request (any role)                                               | `{ "customerName": "Ada Costa", "orderId": "ORD-2026-00042", "amount": 129.99, "reasonCode": "damaged_item" }`                                                                               |
| `GET`  | `/api/refunds/:id`          | Single refund request                                                               | —                                                                                                                                                                                            |
| `GET`  | `/api/refunds/:id/audit`    | Request plus its full audit trail                                                   | —                                                                                                                                                                                            |
| `POST` | `/api/refunds/:id/decision` | Approve or deny a **pending** request                                               | `{ "decision": "approve" \| "deny", "reason": "at least 5 characters" }`                                                                                                                     |
| `POST` | `/api/refunds/:id/process`  | Mocked payout: move an **approved** request to `processed` (finance approver only)  | `{ "reason": "at least 5 characters" }`                                                                                                                                                      |
| `GET`  | `/api/metrics/summary`      | Aggregate metrics for the dashboard cards                                           | —                                                                                                                                                                                            |

## Status codes

| Code  | When                                                                                                                  |
| ----- | --------------------------------------------------------------------------------------------------------------------- |
| `200` | Successful read or decision                                                                                           |
| `201` | Refund request created                                                                                                |
| `400` | Invalid query, invalid body (missing/short reason, non-numeric amount), non-numeric id, unknown role header           |
| `403` | Role is not allowed: support agent deciding a refund at/above the threshold, or anyone but finance calling `/process` |
| `404` | Unknown refund request id, or unknown route                                                                           |
| `409` | Duplicate `orderId`, deciding a request that is no longer pending, or processing a request that is not approved       |
| `500` | Unexpected server error                                                                                               |

## Examples

```bash
# Pending queue, biggest first
curl "http://localhost:4000/api/refunds?status=pending&sortBy=amount&sortDirection=desc"

# Approve as a finance approver
curl -X POST http://localhost:4000/api/refunds/3/decision \
  -H 'content-type: application/json' \
  -H 'x-user-role: finance_approver' -H 'x-user-name: finance.dana' \
  -d '{"decision":"approve","reason":"photo evidence matches the damage report"}'

# Mocked payout
curl -X POST http://localhost:4000/api/refunds/3/process \
  -H 'content-type: application/json' \
  -H 'x-user-role: finance_approver' \
  -d '{"reason":"payout batch 2026-08-02"}'
```

## Response shapes

```jsonc
// GET /api/refunds
{ "refundRequests": [ {
  "id": 3, "customerName": "Ada Costa", "orderId": "ORD-2026-01014",
  "amount": 456.37, "reasonCode": "damaged_item", "status": "pending",
  "requestedBy": "agent.riley", "createdAt": "2026-01-02T09:00:00.000Z",
  "updatedAt": "2026-01-02T09:00:00.000Z", "requiresFinanceApproval": true } ] }

// GET /api/refunds/:id/audit
{ "refundRequest": { }, "auditEvents": [ {
  "id": 7, "refundRequestId": 3, "action": "approved",
  "reason": "photo evidence matches the damage report",
  "actorName": "finance.dana", "actorRole": "finance_approver",
  "createdAt": "2026-01-03T10:12:00.000Z" } ] }

// GET /api/metrics/summary
{ "metrics": {
  "totalRequests": 23,
  "countsByStatus": { "pending": 14, "approved": 3, "denied": 3, "processed": 3 },
  "totalRefundedAmount": 626, "totalApprovedAmount": 1487.26,
  "pendingAmount": 2611.44, "averageRequestAmount": 208, "pendingCount": 14 } }
```
