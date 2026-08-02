import { Router } from "express";
import { config } from "../config/env.js";
import {
  REASON_CODES,
  ALL_REFUND_STATUSES,
} from "../constants/refundStatus.js";
import { ALL_ROLES, ROLE_LABELS } from "../constants/roles.js";
import { metricsRoutes } from "./metricsRoutes.js";
import { refundRoutes } from "./refundRoutes.js";

export const apiRoutes = Router();

apiRoutes.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

// Lets the client render statuses, reason codes and the threshold without duplicating them.
apiRoutes.get("/config", (req, res) => {
  res.json({
    approvalThresholdAmount: config.approvalThresholdAmount,
    statuses: ALL_REFUND_STATUSES,
    reasonCodes: REASON_CODES,
    roles: ALL_ROLES.map((role) => ({ value: role, label: ROLE_LABELS[role] })),
  });
});

apiRoutes.use("/refunds", refundRoutes);
apiRoutes.use("/metrics", metricsRoutes);
