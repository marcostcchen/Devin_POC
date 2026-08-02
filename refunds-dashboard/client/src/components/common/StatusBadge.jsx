import PropTypes from "prop-types";
import { formatStatus } from "../../utils/formatters.js";

export function StatusBadge({ status }) {
  return (
    <span className={`status-badge status-badge--${status}`}>
      {formatStatus(status)}
    </span>
  );
}

StatusBadge.propTypes = { status: PropTypes.string.isRequired };
