import { useState } from "react";
import PropTypes from "prop-types";
import {
  processRefundRequest,
  submitRefundDecision,
} from "../../api/refundsApi.js";
import { useRole } from "../../context/RoleContext.jsx";
import { validateDecisionReason } from "../../utils/decisionValidation.js";
import { ErrorBanner } from "../common/ErrorBanner.jsx";

/**
 * Approve / deny / process actions. The reason field is validated here and again
 * on the server; the buttons a user sees depend on their mocked role and on the
 * finance threshold flag returned with the request.
 */
export function DecisionForm({ refundRequest, onDecisionRecorded }) {
  const { actor, isFinanceApprover } = useRole();
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [pendingAction, setPendingAction] = useState(null);

  const isPending = refundRequest.status === "pending";
  const isApproved = refundRequest.status === "approved";
  const blockedByThreshold =
    refundRequest.requiresFinanceApproval && !isFinanceApprover;

  const runAction = async (actionName, action) => {
    const validationMessage = validateDecisionReason(reason);
    setReasonError(validationMessage);
    if (validationMessage) return;

    setPendingAction(actionName);
    try {
      await action(reason.trim());
      setReason("");
      setSubmitError(null);
      onDecisionRecorded();
    } catch (error) {
      setSubmitError(error.message);
    } finally {
      setPendingAction(null);
    }
  };

  if (!isPending && !isApproved) {
    return (
      <p className="decision-form__closed">
        This request is {refundRequest.status} — no further action available.
      </p>
    );
  }

  return (
    <div className="decision-form">
      <h3 className="panel__title">Decision</h3>
      <ErrorBanner
        message={submitError}
        onDismiss={() => setSubmitError(null)}
      />

      {blockedByThreshold && isPending ? (
        <p className="decision-form__notice">
          This request is at or above the finance threshold. Switch to the
          finance approver role to decide it.
        </p>
      ) : null}

      <label className="decision-form__label" htmlFor="decision-reason">
        Reason (required)
      </label>
      <textarea
        id="decision-reason"
        rows={3}
        value={reason}
        placeholder="Explain the decision — this is stored in the audit trail."
        onChange={(event) => setReason(event.target.value)}
      />
      {reasonError ? <p className="field-error">{reasonError}</p> : null}

      <div className="decision-form__actions">
        {isPending ? (
          <>
            <button
              type="button"
              className="button button--approve"
              disabled={blockedByThreshold || pendingAction !== null}
              onClick={() =>
                runAction("approve", (trimmedReason) =>
                  submitRefundDecision(
                    refundRequest.id,
                    { decision: "approve", reason: trimmedReason },
                    actor,
                  ),
                )
              }
            >
              {pendingAction === "approve" ? "Approving…" : "Approve"}
            </button>
            <button
              type="button"
              className="button button--deny"
              disabled={blockedByThreshold || pendingAction !== null}
              onClick={() =>
                runAction("deny", (trimmedReason) =>
                  submitRefundDecision(
                    refundRequest.id,
                    { decision: "deny", reason: trimmedReason },
                    actor,
                  ),
                )
              }
            >
              {pendingAction === "deny" ? "Denying…" : "Deny"}
            </button>
          </>
        ) : null}

        {isApproved ? (
          <button
            type="button"
            className="button button--primary"
            disabled={!isFinanceApprover || pendingAction !== null}
            title={
              isFinanceApprover
                ? undefined
                : "Only a finance approver can process a refund"
            }
            onClick={() =>
              runAction("process", (trimmedReason) =>
                processRefundRequest(
                  refundRequest.id,
                  { reason: trimmedReason },
                  actor,
                ),
              )
            }
          >
            {pendingAction === "process"
              ? "Processing…"
              : "Mark as processed (mock payout)"}
          </button>
        ) : null}
      </div>
    </div>
  );
}

DecisionForm.propTypes = {
  refundRequest: PropTypes.object.isRequired,
  onDecisionRecorded: PropTypes.func.isRequired,
};
