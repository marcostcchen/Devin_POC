import { getDatabase } from "../db/index.js";

const SORTABLE_COLUMNS = {
  amount: "amount",
  createdAt: "created_at",
  customerName: "customer_name",
  status: "status",
};

function toRefundRequest(row) {
  if (!row) return null;

  return {
    id: row.id,
    customerName: row.customer_name,
    orderId: row.order_id,
    amount: row.amount,
    reasonCode: row.reason_code,
    status: row.status,
    requestedBy: row.requested_by,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export function listRefundRequests({
  status,
  minAmount,
  maxAmount,
  sortBy,
  sortDirection,
}) {
  const conditions = [];
  const params = {};

  if (status) {
    conditions.push("status = @status");
    params.status = status;
  }
  if (minAmount !== undefined) {
    conditions.push("amount >= @minAmount");
    params.minAmount = minAmount;
  }
  if (maxAmount !== undefined) {
    conditions.push("amount <= @maxAmount");
    params.maxAmount = maxAmount;
  }

  const whereClause = conditions.length
    ? `WHERE ${conditions.join(" AND ")}`
    : "";
  // Column and direction are resolved through allow-lists, never interpolated raw.
  const orderColumn = SORTABLE_COLUMNS[sortBy] ?? SORTABLE_COLUMNS.createdAt;
  const orderDirection = sortDirection === "asc" ? "ASC" : "DESC";

  const rows = getDatabase()
    .prepare(
      `SELECT * FROM refund_requests ${whereClause} ORDER BY ${orderColumn} ${orderDirection}, id DESC`,
    )
    .all(params);

  return rows.map(toRefundRequest);
}

export function getRefundRequestById(id) {
  const row = getDatabase()
    .prepare("SELECT * FROM refund_requests WHERE id = ?")
    .get(id);
  return toRefundRequest(row);
}

export function getRefundRequestByOrderId(orderId) {
  const row = getDatabase()
    .prepare("SELECT * FROM refund_requests WHERE order_id = ?")
    .get(orderId);
  return toRefundRequest(row);
}

export function insertRefundRequest({
  customerName,
  orderId,
  amount,
  reasonCode,
  requestedBy,
  status,
  createdAt,
}) {
  const { lastInsertRowid } = getDatabase()
    .prepare(
      `INSERT INTO refund_requests
        (customer_name, order_id, amount, reason_code, status, requested_by, created_at, updated_at)
       VALUES (@customerName, @orderId, @amount, @reasonCode, @status, @requestedBy, @createdAt, @createdAt)`,
    )
    .run({
      customerName,
      orderId,
      amount,
      reasonCode,
      requestedBy,
      status,
      createdAt,
    });

  return getRefundRequestById(Number(lastInsertRowid));
}

export function updateRefundRequestStatus(id, status, updatedAt) {
  getDatabase()
    .prepare(
      "UPDATE refund_requests SET status = @status, updated_at = @updatedAt WHERE id = @id",
    )
    .run({ id, status, updatedAt });

  return getRefundRequestById(id);
}

export function getStatusCounts() {
  return getDatabase()
    .prepare(
      "SELECT status, COUNT(*) AS count FROM refund_requests GROUP BY status",
    )
    .all();
}

export function getAmountAggregates() {
  return getDatabase()
    .prepare(
      `SELECT
         COUNT(*) AS totalRequests,
         COALESCE(AVG(amount), 0) AS averageAmount,
         COALESCE(SUM(amount), 0) AS totalRequestedAmount,
         COALESCE(SUM(CASE WHEN status = 'processed' THEN amount ELSE 0 END), 0) AS totalProcessedAmount,
         COALESCE(SUM(CASE WHEN status IN ('approved', 'processed') THEN amount ELSE 0 END), 0) AS totalApprovedAmount,
         COALESCE(SUM(CASE WHEN status = 'pending' THEN amount ELSE 0 END), 0) AS pendingAmount
       FROM refund_requests`,
    )
    .get();
}
