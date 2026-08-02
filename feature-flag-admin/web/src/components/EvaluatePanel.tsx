/** Resolves a flag for a given user/team, the way an SDK would. */

import { useState } from "react";

interface Props {
  onEvaluate: (flag: string, userId: string, team: string) => Promise<string | null>;
}

export function EvaluatePanel({ onEvaluate }: Props) {
  const [flag, setFlag] = useState("");
  const [userId, setUserId] = useState("user-1");
  const [team, setTeam] = useState("");
  const [result, setResult] = useState("");

  const run = async () => setResult((await onEvaluate(flag, userId, team)) ?? "");

  return (
    <section className="card">
      <strong>Evaluate</strong>
      <div className="row">
        <input
          id="evaluate-flag"
          placeholder="flag-name"
          value={flag}
          onChange={(e) => setFlag(e.target.value)}
        />
        <input
          id="evaluate-user"
          placeholder="user id"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
        />
        <input
          id="evaluate-team"
          placeholder="team"
          value={team}
          onChange={(e) => setTeam(e.target.value)}
        />
        <button id="evaluate" className="secondary" onClick={() => void run()}>
          Evaluate
        </button>
        <span id="evaluate-result" className="muted">
          {result}
        </span>
      </div>
    </section>
  );
}
