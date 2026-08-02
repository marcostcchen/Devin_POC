import PropTypes from "prop-types";
import { formatDateTime } from "../../utils/formatters.js";

const ACTION_LABELS = {
  created: "Request created",
  approved: "Approved",
  denied: "Denied",
  processed: "Processed (mock payout)",
};

export function AuditTrail({ auditEvents }) {
  if (auditEvents.length === 0) {
    return <p className="audit-trail__empty">No history recorded yet.</p>;
  }

  return (
    <ol className="audit-trail">
      {auditEvents.map((auditEvent) => (
        <li key={auditEvent.id} className="audit-trail__event">
          <p className="audit-trail__headline">
            <strong>
              {ACTION_LABELS[auditEvent.action] ?? auditEvent.action}
            </strong>{" "}
            by {auditEvent.actorName}{" "}
            <span className="audit-trail__role">
              ({auditEvent.actorRole.replace("_", " ")})
            </span>
          </p>
          <p className="audit-trail__timestamp">
            {formatDateTime(auditEvent.createdAt)}
          </p>
          {auditEvent.reason ? (
            <p className="audit-trail__reason">“{auditEvent.reason}”</p>
          ) : null}
        </li>
      ))}
    </ol>
  );
}

AuditTrail.propTypes = { auditEvents: PropTypes.array.isRequired };
