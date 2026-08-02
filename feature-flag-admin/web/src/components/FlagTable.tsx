/** The flag list. */

import { FlagRow } from "./FlagRow";
import type { AuditEntry, Flag, FlagUpdate } from "../types";

interface Props {
  flags: Flag[];
  isAdmin: boolean;
  onUpdate: (id: number, changes: FlagUpdate) => Promise<boolean>;
  onDelete: (id: number) => Promise<boolean>;
  loadHistory: (id: number) => Promise<AuditEntry[]>;
}

export function FlagTable({ flags, ...rowProps }: Props) {
  return (
    <section className="card">
      <strong>Flags</strong>
      <table>
        <thead>
          <tr>
            <th>Flag</th>
            <th>State</th>
            <th>Targeting</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {flags.map((flag) => (
            <FlagRow key={flag.id} flag={flag} {...rowProps} />
          ))}
        </tbody>
      </table>
      {flags.length === 0 && <p className="muted">no flags yet</p>}
    </section>
  );
}
