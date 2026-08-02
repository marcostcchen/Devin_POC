/** Flag list card: toolbar (search + state filter + create), then the table. */

import { useState } from "react";
import { FlagRow } from "./FlagRow";
import { NewFlagForm } from "./NewFlagForm";
import type { AuditEntry, Flag, FlagCreate, FlagUpdate } from "../types";

type StateFilter = "all" | "on" | "off";

interface Props {
  flags: Flag[];
  isAdmin: boolean;
  onCreate: (flag: FlagCreate) => Promise<boolean>;
  onUpdate: (id: number, changes: FlagUpdate) => Promise<boolean>;
  onDelete: (id: number) => Promise<boolean>;
  loadHistory: (id: number) => Promise<AuditEntry[]>;
}

export function FlagTable({ flags, isAdmin, onCreate, ...rowProps }: Props) {
  const [query, setQuery] = useState("");
  const [stateFilter, setStateFilter] = useState<StateFilter>("all");
  const [creating, setCreating] = useState(false);

  const term = query.trim().toLowerCase();
  const visible = flags.filter((flag) => {
    const matchesTerm =
      !term ||
      flag.name.toLowerCase().includes(term) ||
      flag.description.toLowerCase().includes(term);
    const matchesState =
      stateFilter === "all" || (stateFilter === "on") === Boolean(flag.enabled);
    return matchesTerm && matchesState;
  });

  const create = async (draft: FlagCreate) => {
    const ok = await onCreate(draft);
    if (ok) setCreating(false);
    return ok;
  };

  return (
    <section className="card">
      <div className="card-head">
        <h2>Flags</h2>
        <span className="pill">{visible.length}</span>
        <div className="row spacer">
          <input
            id="search"
            type="search"
            placeholder="Search flags…"
            aria-label="search flags"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <select
            aria-label="filter by state"
            value={stateFilter}
            onChange={(event) => setStateFilter(event.target.value as StateFilter)}
          >
            <option value="all">All states</option>
            <option value="on">Enabled</option>
            <option value="off">Disabled</option>
          </select>
          <button disabled={!isAdmin} onClick={() => setCreating((open) => !open)}>
            {creating ? "Close" : "New flag"}
          </button>
        </div>
      </div>

      {creating && <NewFlagForm onCreate={create} onCancel={() => setCreating(false)} />}

      {visible.length === 0 ? (
        <p className="empty">
          {flags.length === 0 ? "No flags yet." : "No flags match this filter."}
        </p>
      ) : (
        <table>
          <colgroup>
            <col />
            <col className="col-state" />
            <col className="col-targeting" />
            <col className="col-actions" />
          </colgroup>
          <thead>
            <tr>
              <th>Flag</th>
              <th>State</th>
              <th>Targeting</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((flag) => (
              <FlagRow key={flag.id} flag={flag} isAdmin={isAdmin} {...rowProps} />
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
