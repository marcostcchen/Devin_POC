import {
  AUDIT_ACTION,
  REASON_CODES,
  REFUND_STATUS,
} from "../constants/refundStatus.js";
import { ROLES } from "../constants/roles.js";
import { roundToCents } from "../utils/money.js";

const CUSTOMER_FIRST_NAMES = [
  "Ada",
  "Bruno",
  "Camila",
  "Dmitri",
  "Elena",
  "Farid",
  "Greta",
  "Hana",
  "Ivan",
  "Jolene",
  "Kwame",
  "Lucia",
];

const CUSTOMER_LAST_NAMES = [
  "Almeida",
  "Bennett",
  "Costa",
  "Dubois",
  "Eriksen",
  "Fontaine",
  "Garcia",
  "Haruki",
  "Ivanova",
  "Jensen",
  "Kowalski",
  "Lindqvist",
];

const SUPPORT_AGENTS = ["agent.riley", "agent.morgan", "agent.priya"];

const SEEDED_STATUSES = [
  REFUND_STATUS.PENDING,
  REFUND_STATUS.PENDING,
  REFUND_STATUS.PENDING,
  REFUND_STATUS.PENDING,
  REFUND_STATUS.APPROVED,
  REFUND_STATUS.DENIED,
  REFUND_STATUS.PROCESSED,
];

/**
 * Deterministic PRNG (mulberry32) so the synthetic dataset is identical on every
 * fresh database — makes screenshots, demos and smoke tests reproducible.
 */
function createRandom(seed) {
  let state = seed;
  return function random() {
    state |= 0;
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pick(random, values) {
  return values[Math.floor(random() * values.length)];
}

function isoDaysAgo(days, hourOffset) {
  const date = new Date(Date.UTC(2026, 0, 1));
  date.setUTCDate(date.getUTCDate() - days);
  date.setUTCHours(hourOffset, 0, 0, 0);
  return date.toISOString();
}

function buildSyntheticRequests(count) {
  const random = createRandom(20260101);
  const requests = [];

  for (let index = 0; index < count; index += 1) {
    const status = SEEDED_STATUSES[index % SEEDED_STATUSES.length];
    const createdAt = isoDaysAgo(count - index, 9 + (index % 8));

    requests.push({
      customerName: `${pick(random, CUSTOMER_FIRST_NAMES)} ${pick(random, CUSTOMER_LAST_NAMES)}`,
      orderId: `ORD-2026-${String(1000 + index * 7).padStart(5, "0")}`,
      // Realistic-looking spread between $5 and $500.
      amount: roundToCents(5 + random() * 495),
      reasonCode: pick(random, REASON_CODES),
      status,
      requestedBy: pick(random, SUPPORT_AGENTS),
      createdAt,
    });
  }

  return requests;
}

/**
 * Inserts synthetic refund requests (and their matching audit history) the first
 * time the database is created. Existing databases are left untouched.
 */
export function seedRefundRequests(db, requestCount) {
  const { count } = db
    .prepare("SELECT COUNT(*) AS count FROM refund_requests")
    .get();
  if (count > 0) {
    return { seeded: 0, skipped: true };
  }

  const insertRequest = db.prepare(`
    INSERT INTO refund_requests
      (customer_name, order_id, amount, reason_code, status, requested_by, created_at, updated_at)
    VALUES
      (@customerName, @orderId, @amount, @reasonCode, @status, @requestedBy, @createdAt, @updatedAt)
  `);

  const insertAuditEvent = db.prepare(`
    INSERT INTO audit_events (refund_request_id, action, reason, actor_name, actor_role, created_at)
    VALUES (@refundRequestId, @action, @reason, @actorName, @actorRole, @createdAt)
  `);

  const seedAll = db.transaction((requests) => {
    for (const request of requests) {
      const { lastInsertRowid } = insertRequest.run({
        ...request,
        updatedAt: request.createdAt,
      });

      insertAuditEvent.run({
        refundRequestId: lastInsertRowid,
        action: AUDIT_ACTION.CREATED,
        reason: "Refund request opened from customer support ticket.",
        actorName: request.requestedBy,
        actorRole: ROLES.SUPPORT_AGENT,
        createdAt: request.createdAt,
      });

      if (request.status === REFUND_STATUS.PENDING) continue;

      insertAuditEvent.run({
        refundRequestId: lastInsertRowid,
        action:
          request.status === REFUND_STATUS.DENIED
            ? AUDIT_ACTION.DENIED
            : AUDIT_ACTION.APPROVED,
        reason:
          request.status === REFUND_STATUS.DENIED
            ? "Outside the 30 day return window."
            : "Evidence provided matches the reported issue.",
        actorName: "finance.dana",
        actorRole: ROLES.FINANCE_APPROVER,
        createdAt: request.createdAt,
      });

      if (request.status === REFUND_STATUS.PROCESSED) {
        insertAuditEvent.run({
          refundRequestId: lastInsertRowid,
          action: AUDIT_ACTION.PROCESSED,
          reason: "Refund marked as processed (mocked payout).",
          actorName: "finance.dana",
          actorRole: ROLES.FINANCE_APPROVER,
          createdAt: request.createdAt,
        });
      }
    }
  });

  const requests = buildSyntheticRequests(requestCount);
  seedAll(requests);

  return { seeded: requests.length, skipped: false };
}
