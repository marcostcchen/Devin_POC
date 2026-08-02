import PropTypes from "prop-types";
import { formatCurrency } from "../../utils/formatters.js";
import { RoleSwitcher } from "./RoleSwitcher.jsx";

export function AppHeader({ approvalThresholdAmount }) {
  return (
    <header className="app-header">
      <div>
        <h1 className="app-header__title">Refunds Dashboard</h1>
        <p className="app-header__subtitle">
          Internal tool — review, approve and track customer refund requests.
          Requests of {formatCurrency(approvalThresholdAmount)} or more need
          finance approver sign-off.
        </p>
      </div>
      <RoleSwitcher />
    </header>
  );
}

AppHeader.propTypes = { approvalThresholdAmount: PropTypes.number.isRequired };
