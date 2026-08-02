/** Renders audit entries, used for both per-flag history and global activity. */

import { formatTimestamp } from "../format";
import type { AuditEntry } from "../types";

interface Props {
  entries: AuditEntry[];
  emptyText: string;
}

export function AuditList({ entries, emptyText }: Props) {
  if (entries.length === 0) {
    return <p className="muted">{emptyText}</p>;
  }
  return (
    <ul className="audit">
      {entries.map((entry) => (
        <li key={entry.id}>
          <span>
            {`${entry.actor} ${entry.action} `}
            <strong>{entry.flag_name}</strong>
            {entry.detail && ` — ${entry.detail}`}
          </span>
          <span className="audit-meta" title={entry.created_at}>
            {formatTimestamp(entry.created_at)}
          </span>
        </li>
      ))}
    </ul>
  );
}
