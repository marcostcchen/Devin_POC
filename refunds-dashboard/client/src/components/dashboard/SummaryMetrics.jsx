import PropTypes from "prop-types";
import { formatCurrency } from "../../utils/formatters.js";
import { MetricCard } from "./MetricCard.jsx";

export function SummaryMetrics({ metrics }) {
  if (!metrics) {
    return (
      <section className="summary-metrics summary-metrics--loading">
        Loading metrics…
      </section>
    );
  }

  const { countsByStatus } = metrics;

  return (
    <section className="summary-metrics" aria-label="Summary metrics">
      <MetricCard
        label="Total refunded (processed)"
        value={formatCurrency(metrics.totalRefundedAmount)}
        hint={`${countsByStatus.processed} processed requests`}
      />
      <MetricCard
        label="Approved awaiting payout"
        value={formatCurrency(
          metrics.totalApprovedAmount - metrics.totalRefundedAmount,
        )}
        hint={`${countsByStatus.approved} approved requests`}
      />
      <MetricCard
        label="Pending review"
        value={countsByStatus.pending}
        hint={`${formatCurrency(metrics.pendingAmount)} awaiting a decision`}
      />
      <MetricCard
        label="Denied"
        value={countsByStatus.denied}
        hint="Closed without payout"
      />
      <MetricCard
        label="Average request"
        value={formatCurrency(metrics.averageRequestAmount)}
        hint={`Across ${metrics.totalRequests} requests`}
      />
    </section>
  );
}

SummaryMetrics.propTypes = {
  metrics: PropTypes.shape({
    totalRefundedAmount: PropTypes.number.isRequired,
    totalApprovedAmount: PropTypes.number.isRequired,
    pendingAmount: PropTypes.number.isRequired,
    averageRequestAmount: PropTypes.number.isRequired,
    totalRequests: PropTypes.number.isRequired,
    countsByStatus: PropTypes.object.isRequired,
  }),
};
