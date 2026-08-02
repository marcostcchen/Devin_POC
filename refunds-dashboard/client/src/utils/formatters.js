const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

export function formatCurrency(amount) {
  return currencyFormatter.format(Number(amount ?? 0));
}

export function formatDateTime(isoString) {
  if (!isoString) return "—";
  return new Date(isoString).toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function formatReasonCode(reasonCode) {
  return reasonCode
    .replaceAll("_", " ")
    .replace(/^./, (character) => character.toUpperCase());
}

export function formatStatus(status) {
  return status.replace(/^./, (character) => character.toUpperCase());
}
