/** One flag: on/off switch, targeting editor, actions and expandable history. */

import { useCallback, useEffect, useState } from "react";
import { AuditList } from "./AuditList";
import { formatTimestamp } from "../format";
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

  const resetTargeting = useCallback(() => {
    setRollout(String(flag.rollout_percentage));
    setTeam(flag.target_team);
  }, [flag.rollout_percentage, flag.target_team]);

  // Keep the inputs on the stored values: they follow the server's copy when it
  // changes, and snap back when a save is rejected (e.g. rollout 150), so the
  // row never displays a value that was never stored.
  useEffect(resetTargeting, [resetTargeting]);

  const refreshHistory = async () => setHistory(await loadHistory(flag.id));

  /** Apply a change, then refresh the history if it is currently open. */
  const update = async (changes: FlagUpdate) => {
    const ok = await onUpdate(flag.id, changes);
    if (ok && history) await refreshHistory();
    return ok;
  };

  const saveTargeting = async () => {
    const ok = await update({ rollout_percentage: Number(rollout), target_team: team });
    if (!ok) resetTargeting();
  };

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

  const dirty =
    rollout !== String(flag.rollout_percentage) || team !== flag.target_team;

  return (
    <>
      <tr>
        <td>
          <div className="flag-name">{flag.name}</div>
          {description === null ? (
            <div className="muted">{flag.description || "No description"}</div>
          ) : (
            <div className="row mt-xs">
              <input
                aria-label={`description for ${flag.name}`}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
              <button onClick={() => void saveDescription()}>Save</button>
              <button className="secondary" onClick={() => setDescription(null)}>
                Cancel
              </button>
            </div>
          )}
        </td>

        <td>
          <label className="switch" title={isAdmin ? "Toggle flag" : "Viewers cannot toggle"}>
            <input
              type="checkbox"
              aria-label={`toggle ${flag.name}`}
              checked={flag.enabled}
              disabled={!isAdmin}
              onChange={() => void update({ enabled: !flag.enabled })}
            />
            <span className="track" />
            <span className="switch-label">{flag.enabled ? "ON" : "OFF"}</span>
          </label>
        </td>

        <td>
          <div className="rollout">
            <span className={`bar ${flag.enabled ? "" : "off"}`}>
              <span style={{ width: `${flag.rollout_percentage}%` }} />
            </span>
            <span className="muted">{flag.rollout_percentage}%</span>
            {flag.target_team && <span className="pill accent">{flag.target_team}</span>}
          </div>
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
            <input
              aria-label={`target team for ${flag.name}`}
              placeholder="team"
              className="narrow-text"
              value={team}
              disabled={!isAdmin}
              onChange={(e) => setTeam(e.target.value)}
            />
            <button
              className="secondary"
              disabled={!isAdmin || !dirty}
              onClick={() => void saveTargeting()}
            >
              Save
            </button>
          </div>
        </td>

        <td>
          <div className="row">
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
            <button className="danger" disabled={!isAdmin} onClick={remove}>
              Delete
            </button>
          </div>
          <div className="muted mt-xs" title={flag.updated_at}>
            Updated {formatTimestamp(flag.updated_at)}
          </div>
        </td>
      </tr>

      {history && (
        <tr>
          <td className="history-cell" colSpan={4}>
            <div className="card-head">
              <h2>History · {flag.name}</h2>
            </div>
            <AuditList entries={history} emptyText="No history yet." />
          </td>
        </tr>
      )}
    </>
  );
}
