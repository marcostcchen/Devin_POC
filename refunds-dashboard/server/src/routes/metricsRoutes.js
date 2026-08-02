import { Router } from "express";
import { getSummaryMetrics } from "../services/metricsService.js";
import { asyncHandler } from "../utils/asyncHandler.js";

export const metricsRoutes = Router();

metricsRoutes.get(
  "/summary",
  asyncHandler((req, res) => {
    res.json({ metrics: getSummaryMetrics() });
  }),
);
