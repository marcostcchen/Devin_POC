import { useCallback, useEffect, useState } from "react";
import { fetchRefundRequests, fetchSummaryMetrics } from "../api/refundsApi.js";
import { useRole } from "../context/RoleContext.jsx";

/**
 * Single source of truth for the queue and the summary cards: both are refetched
 * together so the metrics never disagree with the rows on screen.
 */
export function useRefundsData(filters) {
  const { actor } = useRole();
  const [refundRequests, setRefundRequests] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const { status, minAmount, maxAmount, sortBy, sortDirection } = filters;

  const reload = useCallback(async () => {
    setIsLoading(true);
    try {
      const [refundsPayload, metricsPayload] = await Promise.all([
        fetchRefundRequests(
          { status, minAmount, maxAmount, sortBy, sortDirection },
          actor,
        ),
        fetchSummaryMetrics(actor),
      ]);
      setRefundRequests(refundsPayload.refundRequests);
      setMetrics(metricsPayload.metrics);
      setLoadError(null);
    } catch (error) {
      setLoadError(error.message);
    } finally {
      setIsLoading(false);
    }
  }, [actor, status, minAmount, maxAmount, sortBy, sortDirection]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { refundRequests, metrics, isLoading, loadError, reload };
}
