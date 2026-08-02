/** One flag: state pill, targeting editor, actions and collapsible history. */

import { useEffect, useState } from "react";
import { AuditList } from "./AuditList";
import type { AuditEntry, Flag, FlagUpdate } from "../types";

interface Props {
  flag: Flag;
  isAdmin: boolean;
  onUpdate: (id: number, changes: FlagUpdate) => Promise<boolean>;
  onDelete: (id: number) => Promise<boolean>;
  loadHistory: (id: number) => Promise<AuditEntry[]>;
}

export function FlagRow({ flag, isAdmin, onUpdate, onDelete, loadHistory }: Props) {
  const [rollout, setRollout] = useState(String(flag.rollout_percentage));
  const [team, setTeam] = useState(flag.target_team);
  const [description, setDescription] = useState<string | null>(null);
  const [history, setHistory] = useState<AuditEntry[] | null>(null);

  // Re-sync the targeting inputs whenever the server's copy changes, so a
  // rejected save (e.g. rollout 150) does not leave a value that was never
  // stored sitting in the row.
  useEffect(() => {
    setRollout(String(flag.rollout_percentage));
    setTeam(flag.target_team);
  }, [flag.rollout_percentage, flag.target_team, flag.updated_at]);

  const refreshHistory = async () => setHistory(await loadHistory(flag.id));

  /** Apply a change, then refresh the history if it is currently open. */
  const update = async (changes: FlagUpdate) => {
    const ok = await onUpdate(flag.id, changes);
    if (ok && history) await refreshHistory();
    return ok;
  };

  const saveTargeting = () =>
    void update({ rollout_percentage: Number(rollout), target_team: team });

  const saveDescription = async () => {
    if (description !== null && (await update({ description }))) setDescription(null);
  };

  const toggleHistory = async () => {
    if (history) setHistory(null);
    else await refreshHistory();
  };

  const remove = () => {
    if (window.confirm(`Delete ${flag.name}?`)) void onDelete(flag.id);
  };

  return (
    <tr>
      <td>
        <strong>{flag.name}</strong>
        {description === null ? (
          <div className="muted">{flag.description || "no description"}</div>
        ) : (
          <div className="row">
            <input
              aria-label={`description for ${flag.name}`}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <button className="secondary" onClick={() => void saveDescription()}>
              Save
            </button>
            <button className="secondary" onClick={() => setDescription(null)}>
              Cancel
            </button>
          </div>
        )}
        {history && <AuditList entries={history} emptyText="no history yet" />}
      </td>

      <td>
        <span className={`pill ${flag.enabled ? "on" : "off"}`}>
          {flag.enabled ? "ON" : "OFF"}
        </span>
      </td>

      <td>
        <div className="row">
          <input
            aria-label={`rollout percentage for ${flag.name}`}
            type="number"
            min={0}
            max={100}
            className="narrow"
            value={rollout}
            disabled={!isAdmin}
            onChange={(e) => setRollout(e.target.value)}
          />
          %
          <input
            aria-label={`target team for ${flag.name}`}
            placeholder="team"
            className="narrow-text"
            value={team}
            disabled={!isAdmin}
            onChange={(e) => setTeam(e.target.value)}
          />
          <button className="secondary" disabled={!isAdmin} onClick={saveTargeting}>
            Save
          </button>
        </div>
      </td>

      <td>
        <div className="row">
          <button disabled={!isAdmin} onClick={() => void update({ enabled: !flag.enabled })}>
            {flag.enabled ? "Disable" : "Enable"}
          </button>
          <button
            className="secondary"
            disabled={!isAdmin}
            onClick={() => setDescription(flag.description)}
          >
            Edit description
          </button>
          <button className="secondary" onClick={() => void toggleHistory()}>
            History
          </button>
          <button className="secondary" disabled={!isAdmin} onClick={remove}>
            Delete
          </button>
        </div>
      </td>
    </tr>
  );
}
