/** Create-flag form. Disabled entirely for viewers. */

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
  disabled: boolean;
  onCreate: (flag: FlagCreate) => Promise<boolean>;
}

export function NewFlagForm({ disabled, onCreate }: Props) {
  const [draft, setDraft] = useState<FlagCreate>(EMPTY);

  const submit = async () => {
    if (await onCreate(draft)) setDraft(EMPTY);
  };

  return (
    <section className="card">
      <strong>New flag</strong>
      <div className="row">
        <input
          id="new-name"
          placeholder="flag-name"
          value={draft.name}
          disabled={disabled}
          onChange={(e) => setDraft({ ...draft, name: e.target.value })}
        />
        <input
          id="new-description"
          placeholder="description"
          className="wide"
          value={draft.description}
          disabled={disabled}
          onChange={(e) => setDraft({ ...draft, description: e.target.value })}
        />
        <label>
          rollout %{" "}
          <input
            id="new-rollout"
            type="number"
            min={0}
            max={100}
            className="narrow"
            value={draft.rollout_percentage}
            disabled={disabled}
            onChange={(e) =>
              setDraft({ ...draft, rollout_percentage: Number(e.target.value) })
            }
          />
        </label>
        <input
          id="new-team"
          placeholder="target team (optional)"
          value={draft.target_team}
          disabled={disabled}
          onChange={(e) => setDraft({ ...draft, target_team: e.target.value })}
        />
        <label>
          <input
            id="new-enabled"
            type="checkbox"
            checked={draft.enabled}
            disabled={disabled}
            onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })}
          />{" "}
          enabled
        </label>
        <button id="create-flag" disabled={disabled} onClick={() => void submit()}>
          Create
        </button>
      </div>
    </section>
  );
}
