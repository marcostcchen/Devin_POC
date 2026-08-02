/** Create-flag form, revealed from the flag list toolbar (admins only). */

import { useState } from "react";
import type { FlagCreate } from "../types";

const EMPTY: FlagCreate = {
  name: "",
  description: "",
  enabled: false,
  rollout_percentage: 100,
  target_team: "",
};

interface Props {
  onCreate: (flag: FlagCreate) => Promise<boolean>;
  onCancel: () => void;
}

export function NewFlagForm({ onCreate, onCancel }: Props) {
  const [draft, setDraft] = useState<FlagCreate>(EMPTY);

  const submit = async () => {
    if (await onCreate(draft)) setDraft(EMPTY);
  };

  return (
    <div className="card-body">
      <div className="form-grid">
        <label className="form-field" htmlFor="new-name">
          Name
          <input
            id="new-name"
            placeholder="flag-name"
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          />
        </label>
        <label className="form-field" htmlFor="new-description">
          Description
          <input
            id="new-description"
            placeholder="What does it gate?"
            value={draft.description}
            onChange={(e) => setDraft({ ...draft, description: e.target.value })}
          />
        </label>
        <label className="form-field" htmlFor="new-rollout">
          Rollout %
          <input
            id="new-rollout"
            type="number"
            min={0}
            max={100}
            value={draft.rollout_percentage}
            onChange={(e) => setDraft({ ...draft, rollout_percentage: Number(e.target.value) })}
          />
        </label>
        <label className="form-field" htmlFor="new-team">
          Target team
          <input
            id="new-team"
            placeholder="optional"
            value={draft.target_team}
            onChange={(e) => setDraft({ ...draft, target_team: e.target.value })}
          />
        </label>
        <div className="form-actions">
          <label className="switch">
            <input
              id="new-enabled"
              type="checkbox"
              checked={draft.enabled}
              onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })}
            />
            <span className="track" />
            <span className="switch-label">{draft.enabled ? "ON" : "OFF"}</span>
          </label>
          <button id="create-flag" onClick={() => void submit()}>
            Create
          </button>
          <button className="secondary" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
