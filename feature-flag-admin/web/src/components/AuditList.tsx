/** Renders audit entries as one line each, newest first. */

import type { AuditEntry } from "../types";

interface Props {
  entries: AuditEntry[];
  emptyText: string;
}

export function AuditList({ entries, emptyText }: Props) {
  if (entries.length === 0) {
    return (
      <ul className="audit">
        <li className="muted">{emptyText}</li>
      </ul>
    );
  }
  return (
    <ul className="audit">
      {entries.map((entry) => (
        <li key={entry.id}>
          {entry.created_at} — {entry.actor} {entry.action} {entry.flag_name}
          {entry.detail && ` (${entry.detail})`}
        </li>
      ))}
    </ul>
  );
}
