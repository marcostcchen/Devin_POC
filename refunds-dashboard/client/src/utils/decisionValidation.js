export const MIN_REASON_LENGTH = 5;
export const MAX_REASON_LENGTH = 500;

/** Client-side mirror of the server rule so users get feedback before submitting. */
export function validateDecisionReason(reason) {
  const trimmed = (reason ?? "").trim();

  if (trimmed.length === 0) return "A reason is required.";
  if (trimmed.length < MIN_REASON_LENGTH)
    return `Reason must be at least ${MIN_REASON_LENGTH} characters.`;
  if (trimmed.length > MAX_REASON_LENGTH)
    return `Reason must be at most ${MAX_REASON_LENGTH} characters.`;

  return null;
}

export function validateNewRefundRequest({
  customerName,
  orderId,
  amount,
  reasonCode,
}) {
  const errors = {};

  if (!customerName || customerName.trim().length < 2) {
    errors.customerName = "Customer name must be at least 2 characters.";
  }
  if (!/^[A-Za-z0-9-]{4,32}$/.test((orderId ?? "").trim())) {
    errors.orderId = "Order ID must be 4-32 letters, digits or dashes.";
  }

  const numericAmount = Number(amount);
  if (amount === "" || !Number.isFinite(numericAmount)) {
    errors.amount = "Amount must be numeric.";
  } else if (numericAmount <= 0) {
    errors.amount = "Amount must be greater than zero.";
  }

  if (!reasonCode) {
    errors.reasonCode = "Pick a reason code.";
  }

  return errors;
}
