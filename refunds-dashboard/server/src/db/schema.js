/**
 * Creates the two tables the app needs. `audit_events` is append-only: decisions
 * are never updated or deleted, they are only added, so the trail stays complete.
 */
export function createSchema(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS refund_requests (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_name TEXT NOT NULL,
      order_id TEXT NOT NULL UNIQUE,
      amount REAL NOT NULL CHECK (amount > 0),
      reason_code TEXT NOT NULL,
      status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'denied', 'processed')),
      requested_by TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS audit_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      refund_request_id INTEGER NOT NULL REFERENCES refund_requests(id) ON DELETE CASCADE,
      action TEXT NOT NULL,
      reason TEXT,
      actor_name TEXT NOT NULL,
      actor_role TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_refund_requests_status ON refund_requests(status);
    CREATE INDEX IF NOT EXISTS idx_audit_events_request ON audit_events(refund_request_id);
  `);
}
