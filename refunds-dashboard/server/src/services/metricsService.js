import {
  ALL_REFUND_STATUSES,
  REFUND_STATUS,
} from "../constants/refundStatus.js";
import * as refundRepository from "../repositories/refundRepository.js";
import { roundToCents } from "../utils/money.js";

/** Aggregate figures rendered by the summary cards at the top of the dashboard. */
export function getSummaryMetrics() {
  const aggregates = refundRepository.getAmountAggregates();

  const countsByStatus = Object.fromEntries(
    ALL_REFUND_STATUSES.map((status) => [status, 0]),
  );
  for (const { status, count } of refundRepository.getStatusCounts()) {
    countsByStatus[status] = count;
  }

  return {
    totalRequests: aggregates.totalRequests,
    countsByStatus,
    // "Refunded" only counts money that actually left the (mock) payout flow.
    totalRefundedAmount: roundToCents(aggregates.totalProcessedAmount),
    totalApprovedAmount: roundToCents(aggregates.totalApprovedAmount),
    pendingAmount: roundToCents(aggregates.pendingAmount),
    averageRequestAmount: roundToCents(aggregates.averageAmount),
    pendingCount: countsByStatus[REFUND_STATUS.PENDING],
  };
}
