import { config } from "../config/env.js";
import {
  AUDIT_ACTION,
  DECISION,
  REFUND_STATUS,
} from "../constants/refundStatus.js";
import { ROLES } from "../constants/roles.js";
import * as auditRepository from "../repositories/auditRepository.js";
import * as refundRepository from "../repositories/refundRepository.js";
import { AppError } from "../utils/AppError.js";
import { roundToCents } from "../utils/money.js";

/**
 * Threshold rule: a request at or above APPROVAL_THRESHOLD_AMOUNT can only be
 * decided by a finance approver. Below the threshold a support agent may also
 * decide, which is what makes the threshold meaningful rather than decorative.
 */
export function requiresFinanceApproval(amount) {
  return amount >= config.approvalThresholdAmount;
}

function decorate(refundRequest) {
  return {
    ...refundRequest,
    requiresFinanceApproval: requiresFinanceApproval(refundRequest.amount),
  };
}

function assertCanDecide(refundRequest, actor) {
  if (actor.role === ROLES.FINANCE_APPROVER) return;

  if (requiresFinanceApproval(refundRequest.amount)) {
    throw AppError.forbidden(
      `Refunds of $${config.approvalThresholdAmount} or more require a finance approver sign-off.`,
    );
  }
}

export function listRefundRequests(filters) {
  return refundRepository.listRefundRequests(filters).map(decorate);
}

export function getRefundRequest(id) {
  const refundRequest = refundRepository.getRefundRequestById(id);
  if (!refundRequest) {
    throw AppError.notFound(`Refund request ${id} was not found`);
  }
  return decorate(refundRequest);
}

export function getRefundRequestHistory(id) {
  const refundRequest = getRefundRequest(id);
  return {
    refundRequest,
    auditEvents: auditRepository.listAuditEventsForRequest(refundRequest.id),
  };
}

export function createRefundRequest(
  { customerName, orderId, amount, reasonCode },
  actor,
) {
  if (refundRepository.getRefundRequestByOrderId(orderId)) {
    throw AppError.conflict(
      `A refund request already exists for order ${orderId}`,
    );
  }

  const createdAt = new Date().toISOString();
  const refundRequest = refundRepository.insertRefundRequest({
    customerName,
    orderId,
    amount: roundToCents(amount),
    reasonCode,
    requestedBy: actor.name,
    status: REFUND_STATUS.PENDING,
    createdAt,
  });

  auditRepository.appendAuditEvent({
    refundRequestId: refundRequest.id,
    action: AUDIT_ACTION.CREATED,
    reason: `Refund request opened for ${reasonCode}.`,
    actorName: actor.name,
    actorRole: actor.role,
    createdAt,
  });

  return decorate(refundRequest);
}

export function decideRefundRequest(id, { decision, reason }, actor) {
  const refundRequest = getRefundRequest(id);

  if (refundRequest.status !== REFUND_STATUS.PENDING) {
    throw AppError.conflict(
      `Refund request ${id} is "${refundRequest.status}" and can no longer be approved or denied`,
    );
  }

  assertCanDecide(refundRequest, actor);

  const nextStatus =
    decision === DECISION.APPROVE
      ? REFUND_STATUS.APPROVED
      : REFUND_STATUS.DENIED;
  const decidedAt = new Date().toISOString();
  const updated = refundRepository.updateRefundRequestStatus(
    id,
    nextStatus,
    decidedAt,
  );

  auditRepository.appendAuditEvent({
    refundRequestId: id,
    action:
      decision === DECISION.APPROVE
        ? AUDIT_ACTION.APPROVED
        : AUDIT_ACTION.DENIED,
    reason,
    actorName: actor.name,
    actorRole: actor.role,
    createdAt: decidedAt,
  });

  return decorate(updated);
}

/**
 * Mocked payout: flips an approved request to "processed" and records who did it.
 * No payment processor is contacted and no money moves.
 */
export function processRefundRequest(id, { reason }, actor) {
  const refundRequest = getRefundRequest(id);

  if (refundRequest.status !== REFUND_STATUS.APPROVED) {
    throw AppError.conflict(
      `Only approved refund requests can be processed (request ${id} is "${refundRequest.status}")`,
    );
  }

  const processedAt = new Date().toISOString();
  const updated = refundRepository.updateRefundRequestStatus(
    id,
    REFUND_STATUS.PROCESSED,
    processedAt,
  );

  auditRepository.appendAuditEvent({
    refundRequestId: id,
    action: AUDIT_ACTION.PROCESSED,
    reason,
    actorName: actor.name,
    actorRole: actor.role,
    createdAt: processedAt,
  });

  return decorate(updated);
}
