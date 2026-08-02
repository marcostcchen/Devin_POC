import PropTypes from "prop-types";
import { useRefundHistory } from "../../hooks/useRefundHistory.js";
import {
  formatCurrency,
  formatDateTime,
  formatReasonCode,
} from "../../utils/formatters.js";
import { EmptyState } from "../common/EmptyState.jsx";
import { ErrorBanner } from "../common/ErrorBanner.jsx";
import { StatusBadge } from "../common/StatusBadge.jsx";
import { AuditTrail } from "./AuditTrail.jsx";
import { DecisionForm } from "./DecisionForm.jsx";

export function RefundDetailPanel({ refundRequest, onDecisionRecorded }) {
  const { auditEvents, historyError, reloadHistory } = useRefundHistory(
    refundRequest?.id,
  );

  if (!refundRequest) {
    return (
      <aside className="panel detail-panel">
        <EmptyState
          title="Select a refund request"
          description="Pick a row in the queue to review its details and history."
        />
      </aside>
    );
  }

  const handleDecisionRecorded = async () => {
    await onDecisionRecorded();
    await reloadHistory();
  };

  return (
    <aside className="panel detail-panel">
      <header className="detail-panel__header">
        <div>
          <h2 className="panel__title">{refundRequest.customerName}</h2>
          <p className="detail-panel__order">{refundRequest.orderId}</p>
        </div>
        <StatusBadge status={refundRequest.status} />
      </header>

      <dl className="detail-panel__facts">
        <div>
          <dt>Amount</dt>
          <dd>{formatCurrency(refundRequest.amount)}</dd>
        </div>
        <div>
          <dt>Reason code</dt>
          <dd>{formatReasonCode(refundRequest.reasonCode)}</dd>
        </div>
        <div>
          <dt>Requested by</dt>
          <dd>{refundRequest.requestedBy}</dd>
        </div>
        <div>
          <dt>Requested at</dt>
          <dd>{formatDateTime(refundRequest.createdAt)}</dd>
        </div>
        <div>
          <dt>Finance sign-off</dt>
          <dd>
            {refundRequest.requiresFinanceApproval
              ? "Required"
              : "Not required"}
          </dd>
        </div>
      </dl>

      <DecisionForm
        refundRequest={refundRequest}
        onDecisionRecorded={handleDecisionRecorded}
      />

      <section className="detail-panel__history">
        <h3 className="panel__title">Audit trail</h3>
        <ErrorBanner message={historyError} />
        <AuditTrail auditEvents={auditEvents} />
      </section>
    </aside>
  );
}

RefundDetailPanel.propTypes = {
  refundRequest: PropTypes.object,
  onDecisionRecorded: PropTypes.func.isRequired,
};
