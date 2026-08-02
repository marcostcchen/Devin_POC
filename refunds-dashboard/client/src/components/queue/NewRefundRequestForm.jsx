import { useState } from "react";
import PropTypes from "prop-types";
import { createRefundRequest } from "../../api/refundsApi.js";
import { useRole } from "../../context/RoleContext.jsx";
import { validateNewRefundRequest } from "../../utils/decisionValidation.js";
import { formatReasonCode } from "../../utils/formatters.js";
import { ErrorBanner } from "../common/ErrorBanner.jsx";

const EMPTY_FORM = {
  customerName: "",
  orderId: "",
  amount: "",
  reasonCode: "",
};

export function NewRefundRequestForm({ reasonCodes, onCreated }) {
  const { actor } = useRole();
  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitError, setSubmitError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const updateField = (field, value) =>
    setForm((current) => ({ ...current, [field]: value }));

  const handleSubmit = async (event) => {
    event.preventDefault();

    const errors = validateNewRefundRequest(form);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setIsSubmitting(true);
    try {
      await createRefundRequest(
        { ...form, amount: Number(form.amount) },
        actor,
      );
      setForm(EMPTY_FORM);
      setSubmitError(null);
      onCreated();
    } catch (error) {
      setSubmitError(error.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form className="new-request-form" onSubmit={handleSubmit}>
      <h3 className="panel__title">Raise a refund request</h3>
      <ErrorBanner
        message={submitError}
        onDismiss={() => setSubmitError(null)}
      />

      <div className="new-request-form__field">
        <label htmlFor="new-customer-name">Customer name</label>
        <input
          id="new-customer-name"
          value={form.customerName}
          onChange={(event) => updateField("customerName", event.target.value)}
        />
        {fieldErrors.customerName ? (
          <p className="field-error">{fieldErrors.customerName}</p>
        ) : null}
      </div>

      <div className="new-request-form__field">
        <label htmlFor="new-order-id">Order ID</label>
        <input
          id="new-order-id"
          placeholder="ORD-2026-00042"
          value={form.orderId}
          onChange={(event) => updateField("orderId", event.target.value)}
        />
        {fieldErrors.orderId ? (
          <p className="field-error">{fieldErrors.orderId}</p>
        ) : null}
      </div>

      <div className="new-request-form__field">
        <label htmlFor="new-amount">Amount ($)</label>
        <input
          id="new-amount"
          type="number"
          step="0.01"
          min="0"
          value={form.amount}
          onChange={(event) => updateField("amount", event.target.value)}
        />
        {fieldErrors.amount ? (
          <p className="field-error">{fieldErrors.amount}</p>
        ) : null}
      </div>

      <div className="new-request-form__field">
        <label htmlFor="new-reason-code">Reason code</label>
        <select
          id="new-reason-code"
          value={form.reasonCode}
          onChange={(event) => updateField("reasonCode", event.target.value)}
        >
          <option value="">Select a reason…</option>
          {reasonCodes.map((reasonCode) => (
            <option key={reasonCode} value={reasonCode}>
              {formatReasonCode(reasonCode)}
            </option>
          ))}
        </select>
        {fieldErrors.reasonCode ? (
          <p className="field-error">{fieldErrors.reasonCode}</p>
        ) : null}
      </div>

      <button
        type="submit"
        className="button button--primary"
        disabled={isSubmitting}
      >
        {isSubmitting ? "Submitting…" : "Submit request"}
      </button>
    </form>
  );
}

NewRefundRequestForm.propTypes = {
  reasonCodes: PropTypes.arrayOf(PropTypes.string).isRequired,
  onCreated: PropTypes.func.isRequired,
};
