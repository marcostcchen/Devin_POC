export const REFUND_STATUS = {
  PENDING: "pending",
  APPROVED: "approved",
  DENIED: "denied",
  PROCESSED: "processed",
};

export const ALL_REFUND_STATUSES = Object.values(REFUND_STATUS);

export const DECISION = {
  APPROVE: "approve",
  DENY: "deny",
};

export const ALL_DECISIONS = Object.values(DECISION);

export const AUDIT_ACTION = {
  CREATED: "created",
  APPROVED: "approved",
  DENIED: "denied",
  PROCESSED: "processed",
};

export const REASON_CODES = [
  "damaged_item",
  "item_not_received",
  "wrong_item",
  "late_delivery",
  "duplicate_charge",
  "quality_issue",
  "changed_mind",
  "subscription_cancelled",
];
