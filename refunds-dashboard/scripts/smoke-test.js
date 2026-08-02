/**
 * Smoke-level checks against a running API (npm run dev first).
 * Deliberately not a test suite: it walks the happy path plus the main
 * validation / RBAC guards and prints one line per check.
 */
const API_BASE_URL =
  process.env.SMOKE_API_BASE_URL ?? "http://localhost:4000/api";

const SUPPORT_AGENT = {
  "x-user-role": "support_agent",
  "x-user-name": "agent.smoke",
};
const FINANCE_APPROVER = {
  "x-user-role": "finance_approver",
  "x-user-name": "finance.smoke",
};

let failures = 0;

async function call(
  path,
  { method = "GET", body, headers = SUPPORT_AGENT } = {},
) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...headers },
    body: body ? JSON.stringify(body) : undefined,
  });
  return {
    status: response.status,
    payload: await response.json().catch(() => null),
  };
}

function check(description, condition, actual) {
  if (condition) {
    console.log(`PASS  ${description}`);
    return;
  }
  failures += 1;
  console.error(`FAIL  ${description} — got ${JSON.stringify(actual)}`);
}

async function run() {
  const health = await call("/health");
  check("health endpoint responds", health.status === 200, health.status);

  const queue = await call(
    "/refunds?status=pending&sortBy=amount&sortDirection=desc",
  );
  check(
    "pending queue returns rows",
    queue.payload?.refundRequests?.length > 0,
    queue.status,
  );

  const metrics = await call("/metrics/summary");
  check(
    "summary metrics include status counts",
    Boolean(metrics.payload?.metrics?.countsByStatus),
    metrics.status,
  );

  const invalidFilter = await call("/refunds?status=unknown");
  check(
    "invalid status filter is rejected with 400",
    invalidFilter.status === 400,
    invalidFilter.status,
  );

  const missing = await call("/refunds/999999");
  check(
    "unknown refund id returns 404",
    missing.status === 404,
    missing.status,
  );

  const created = await call("/refunds", {
    method: "POST",
    body: {
      customerName: "Smoke Tester",
      orderId: `ORD-SMOKE-${Date.now()}`,
      amount: 250.5,
      reasonCode: "damaged_item",
    },
  });
  check(
    "support agent can create a request",
    created.status === 201,
    created.status,
  );
  const refundId = created.payload?.refundRequest?.id;

  const emptyReason = await call(`/refunds/${refundId}/decision`, {
    method: "POST",
    body: { decision: "approve", reason: "   " },
    headers: FINANCE_APPROVER,
  });
  check(
    "empty reason is rejected with 400",
    emptyReason.status === 400,
    emptyReason.status,
  );

  const agentDecision = await call(`/refunds/${refundId}/decision`, {
    method: "POST",
    body: {
      decision: "approve",
      reason: "agent tries to approve a large refund",
    },
  });
  check(
    "threshold rule blocks the support agent with 403",
    agentDecision.status === 403,
    agentDecision.status,
  );

  const approved = await call(`/refunds/${refundId}/decision`, {
    method: "POST",
    body: {
      decision: "approve",
      reason: "photo evidence matches the damage report",
    },
    headers: FINANCE_APPROVER,
  });
  check(
    "finance approver can approve",
    approved.payload?.refundRequest?.status === "approved",
    approved.status,
  );

  const processed = await call(`/refunds/${refundId}/process`, {
    method: "POST",
    body: { reason: "mock payout executed" },
    headers: FINANCE_APPROVER,
  });
  check(
    "approved request can be processed",
    processed.payload?.refundRequest?.status === "processed",
    processed.status,
  );

  const history = await call(`/refunds/${refundId}/audit`);
  check(
    "audit trail records every step",
    history.payload?.auditEvents?.length === 3,
    history.payload?.auditEvents?.length,
  );

  console.log(
    failures === 0
      ? "\nAll smoke checks passed."
      : `\n${failures} smoke check(s) failed.`,
  );
  process.exit(failures === 0 ? 0 : 1);
}

run().catch((error) => {
  console.error("Smoke run could not complete:", error.message);
  process.exit(1);
});
