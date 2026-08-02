import PropTypes from "prop-types";
import { EmptyState } from "../common/EmptyState.jsx";
import { RefundRow } from "./RefundRow.jsx";

export function RefundQueue({
  refundRequests,
  isLoading,
  selectedRefundId,
  onSelect,
}) {
  if (isLoading) {
    return <p className="refund-queue__loading">Loading refund requests…</p>;
  }

  if (refundRequests.length === 0) {
    return (
      <EmptyState
        title="No refund requests match these filters"
        description="Try widening the amount range or clearing the status filter."
      />
    );
  }

  return (
    <table className="refund-queue">
      <thead>
        <tr>
          <th>Customer</th>
          <th>Order ID</th>
          <th>Amount</th>
          <th>Reason code</th>
          <th>Status</th>
          <th>Requested</th>
        </tr>
      </thead>
      <tbody>
        {refundRequests.map((refundRequest) => (
          <RefundRow
            key={refundRequest.id}
            refundRequest={refundRequest}
            isSelected={refundRequest.id === selectedRefundId}
            onSelect={onSelect}
          />
        ))}
      </tbody>
    </table>
  );
}

RefundQueue.propTypes = {
  refundRequests: PropTypes.array.isRequired,
  isLoading: PropTypes.bool,
  selectedRefundId: PropTypes.number,
  onSelect: PropTypes.func.isRequired,
};
