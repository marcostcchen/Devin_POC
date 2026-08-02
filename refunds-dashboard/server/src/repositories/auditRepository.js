import { getDatabase } from "../db/index.js";

function toAuditEvent(row) {
  return {
    id: row.id,
    refundRequestId: row.refund_request_id,
    action: row.action,
    reason: row.reason,
    actorName: row.actor_name,
    actorRole: row.actor_role,
    createdAt: row.created_at,
  };
}

export function appendAuditEvent({
  refundRequestId,
  action,
  reason,
  actorName,
  actorRole,
  createdAt,
}) {
  const { lastInsertRowid } = getDatabase()
    .prepare(
      `INSERT INTO audit_events (refund_request_id, action, reason, actor_name, actor_role, created_at)
       VALUES (@refundRequestId, @action, @reason, @actorName, @actorRole, @createdAt)`,
    )
    .run({ refundRequestId, action, reason, actorName, actorRole, createdAt });

  return Number(lastInsertRowid);
}

export function listAuditEventsForRequest(refundRequestId) {
  return getDatabase()
    .prepare(
      "SELECT * FROM audit_events WHERE refund_request_id = ? ORDER BY created_at ASC, id ASC",
    )
    .all(refundRequestId)
    .map(toAuditEvent);
}
