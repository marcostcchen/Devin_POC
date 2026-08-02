import {
  ALL_DECISIONS,
  ALL_REFUND_STATUSES,
  REASON_CODES,
} from "../constants/refundStatus.js";

const MIN_REASON_LENGTH = 5;
const MAX_REASON_LENGTH = 500;
const MIN_AMOUNT = 0.01;
const MAX_AMOUNT = 10000;

function parseOptionalNumber(raw, field, errors) {
  if (raw === undefined || raw === "") return undefined;

  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed < 0) {
    errors.push({ field, message: `${field} must be a non-negative number` });
    return undefined;
  }
  return parsed;
}

/** Validates the query string of GET /api/refunds (filtering + sorting). */
export function parseRefundQuery(query) {
  const errors = [];
  const status =
    query.status && query.status !== "all" ? String(query.status) : undefined;

  if (status && !ALL_REFUND_STATUSES.includes(status)) {
    errors.push({
      field: "status",
      message: `status must be one of: ${ALL_REFUND_STATUSES.join(", ")}`,
    });
  }

  const minAmount = parseOptionalNumber(query.minAmount, "minAmount", errors);
  const maxAmount = parseOptionalNumber(query.maxAmount, "maxAmount", errors);

  if (
    minAmount !== undefined &&
    maxAmount !== undefined &&
    minAmount > maxAmount
  ) {
    errors.push({
      field: "minAmount",
      message: "minAmount cannot be greater than maxAmount",
    });
  }

  const sortBy = query.sortBy ? String(query.sortBy) : "createdAt";
  if (!["amount", "createdAt", "customerName", "status"].includes(sortBy)) {
    errors.push({
      field: "sortBy",
      message: "sortBy must be one of: amount, createdAt, customerName, status",
    });
  }

  const sortDirection = query.sortDirection
    ? String(query.sortDirection)
    : "desc";
  if (!["asc", "desc"].includes(sortDirection)) {
    errors.push({
      field: "sortDirection",
      message: 'sortDirection must be "asc" or "desc"',
    });
  }

  return {
    errors,
    value: { status, minAmount, maxAmount, sortBy, sortDirection },
  };
}

/** Validates the body of POST /api/refunds/:id/decision and /process. */
export function parseDecisionPayload(body, { requireDecision = true } = {}) {
  const errors = [];
  const payload = body ?? {};

  let decision;
  if (requireDecision) {
    decision =
      typeof payload.decision === "string" ? payload.decision.trim() : "";
    if (!ALL_DECISIONS.includes(decision)) {
      errors.push({
        field: "decision",
        message: `decision must be one of: ${ALL_DECISIONS.join(", ")}`,
      });
    }
  }

  const reason =
    typeof payload.reason === "string" ? payload.reason.trim() : "";
  if (reason.length === 0) {
    errors.push({ field: "reason", message: "reason is required" });
  } else if (reason.length < MIN_REASON_LENGTH) {
    errors.push({
      field: "reason",
      message: `reason must be at least ${MIN_REASON_LENGTH} characters`,
    });
  } else if (reason.length > MAX_REASON_LENGTH) {
    errors.push({
      field: "reason",
      message: `reason must be at most ${MAX_REASON_LENGTH} characters`,
    });
  }

  return { errors, value: { decision, reason } };
}

/** Validates the body of POST /api/refunds (support agents raising a request). */
export function parseCreateRefundPayload(body) {
  const errors = [];
  const payload = body ?? {};

  const customerName =
    typeof payload.customerName === "string" ? payload.customerName.trim() : "";
  if (customerName.length < 2) {
    errors.push({
      field: "customerName",
      message: "customerName must be at least 2 characters",
    });
  }

  const orderId =
    typeof payload.orderId === "string" ? payload.orderId.trim() : "";
  if (!/^[A-Za-z0-9-]{4,32}$/.test(orderId)) {
    errors.push({
      field: "orderId",
      message: "orderId must be 4-32 characters (letters, digits or dashes)",
    });
  }

  const amount = Number(payload.amount);
  if (!Number.isFinite(amount)) {
    errors.push({ field: "amount", message: "amount must be numeric" });
  } else if (amount < MIN_AMOUNT || amount > MAX_AMOUNT) {
    errors.push({
      field: "amount",
      message: `amount must be between ${MIN_AMOUNT} and ${MAX_AMOUNT}`,
    });
  }

  const reasonCode =
    typeof payload.reasonCode === "string" ? payload.reasonCode.trim() : "";
  if (!REASON_CODES.includes(reasonCode)) {
    errors.push({
      field: "reasonCode",
      message: `reasonCode must be one of: ${REASON_CODES.join(", ")}`,
    });
  }

  return { errors, value: { customerName, orderId, amount, reasonCode } };
}
