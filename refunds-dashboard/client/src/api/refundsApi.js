import { request } from "./apiClient.js";

function buildQueryString(filters) {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });

  const queryString = params.toString();
  return queryString ? `?${queryString}` : "";
}

export function fetchAppConfig() {
  return request("/config");
}

export function fetchRefundRequests(filters, actor) {
  return request(`/refunds${buildQueryString(filters)}`, { actor });
}

export function fetchRefundHistory(refundRequestId, actor) {
  return request(`/refunds/${refundRequestId}/audit`, { actor });
}

export function fetchSummaryMetrics(actor) {
  return request("/metrics/summary", { actor });
}

export function createRefundRequest(payload, actor) {
  return request("/refunds", { method: "POST", body: payload, actor });
}

export function submitRefundDecision(
  refundRequestId,
  { decision, reason },
  actor,
) {
  return request(`/refunds/${refundRequestId}/decision`, {
    method: "POST",
    body: { decision, reason },
    actor,
  });
}

export function processRefundRequest(refundRequestId, { reason }, actor) {
  return request(`/refunds/${refundRequestId}/process`, {
    method: "POST",
    body: { reason },
    actor,
  });
}
