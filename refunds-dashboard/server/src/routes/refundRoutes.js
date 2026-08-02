import { Router } from "express";
import { ROLES } from "../constants/roles.js";
import { requireRole } from "../middleware/requireRole.js";
import { validateNumericId } from "../middleware/validateNumericId.js";
import * as refundService from "../services/refundService.js";
import { AppError } from "../utils/AppError.js";
import { asyncHandler } from "../utils/asyncHandler.js";
import {
  parseCreateRefundPayload,
  parseDecisionPayload,
  parseRefundQuery,
} from "../validation/refundValidation.js";

export const refundRoutes = Router();

function rejectInvalidPayload(errors) {
  if (errors.length > 0) {
    throw AppError.badRequest("Validation failed", errors);
  }
}

refundRoutes.get(
  "/",
  asyncHandler((req, res) => {
    const { errors, value } = parseRefundQuery(req.query);
    rejectInvalidPayload(errors);

    res.json({ refundRequests: refundService.listRefundRequests(value) });
  }),
);

refundRoutes.post(
  "/",
  asyncHandler((req, res) => {
    const { errors, value } = parseCreateRefundPayload(req.body);
    rejectInvalidPayload(errors);

    res
      .status(201)
      .json({
        refundRequest: refundService.createRefundRequest(value, req.actor),
      });
  }),
);

refundRoutes.get(
  "/:id",
  validateNumericId,
  asyncHandler((req, res) => {
    res.json({
      refundRequest: refundService.getRefundRequest(req.refundRequestId),
    });
  }),
);

refundRoutes.get(
  "/:id/audit",
  validateNumericId,
  asyncHandler((req, res) => {
    const { refundRequest, auditEvents } =
      refundService.getRefundRequestHistory(req.refundRequestId);
    res.json({ refundRequest, auditEvents });
  }),
);

refundRoutes.post(
  "/:id/decision",
  validateNumericId,
  asyncHandler((req, res) => {
    const { errors, value } = parseDecisionPayload(req.body);
    rejectInvalidPayload(errors);

    res.json({
      refundRequest: refundService.decideRefundRequest(
        req.refundRequestId,
        value,
        req.actor,
      ),
    });
  }),
);

refundRoutes.post(
  "/:id/process",
  validateNumericId,
  requireRole(ROLES.FINANCE_APPROVER),
  asyncHandler((req, res) => {
    const { errors, value } = parseDecisionPayload(req.body, {
      requireDecision: false,
    });
    rejectInvalidPayload(errors);

    res.json({
      refundRequest: refundService.processRefundRequest(
        req.refundRequestId,
        value,
        req.actor,
      ),
    });
  }),
);
