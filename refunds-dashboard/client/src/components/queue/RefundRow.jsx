import PropTypes from "prop-types";
import { StatusBadge } from "../common/StatusBadge.jsx";
import {
  formatCurrency,
  formatDateTime,
  formatReasonCode,
} from "../../utils/formatters.js";

export function RefundRow({ refundRequest, isSelected, onSelect }) {
  return (
    <tr
      className={`refund-row${isSelected ? " refund-row--selected" : ""}`}
      onClick={() => onSelect(refundRequest.id)}
    >
      <td>{refundRequest.customerName}</td>
      <td className="refund-row__mono">{refundRequest.orderId}</td>
      <td className="refund-row__amount">
        {formatCurrency(refundRequest.amount)}
        {refundRequest.requiresFinanceApproval ? (
          <span
            className="refund-row__flag"
            title="Requires finance approver sign-off"
          >
            finance
          </span>
        ) : null}
      </td>
      <td>{formatReasonCode(refundRequest.reasonCode)}</td>
      <td>
        <StatusBadge status={refundRequest.status} />
      </td>
      <td>{formatDateTime(refundRequest.createdAt)}</td>
    </tr>
  );
}

RefundRow.propTypes = {
  refundRequest: PropTypes.object.isRequired,
  isSelected: PropTypes.bool,
  onSelect: PropTypes.func.isRequired,
};
