import { useCallback, useEffect, useState } from "react";
import { fetchRefundHistory } from "../api/refundsApi.js";
import { useRole } from "../context/RoleContext.jsx";

/** Loads the audit trail for the currently selected refund request. */
export function useRefundHistory(refundRequestId) {
  const { actor } = useRole();
  const [auditEvents, setAuditEvents] = useState([]);
  const [historyError, setHistoryError] = useState(null);

  const reloadHistory = useCallback(async () => {
    if (!refundRequestId) {
      setAuditEvents([]);
      return;
    }

    try {
      const payload = await fetchRefundHistory(refundRequestId, actor);
      setAuditEvents(payload.auditEvents);
      setHistoryError(null);
    } catch (error) {
      setHistoryError(error.message);
    }
  }, [actor, refundRequestId]);

  useEffect(() => {
    reloadHistory();
  }, [reloadHistory]);

  return { auditEvents, historyError, reloadHistory };
}
