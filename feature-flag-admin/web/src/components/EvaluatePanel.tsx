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
      <div className="card-head">
        <h2>Evaluate</h2>
        <span className="muted spacer">as an SDK would</span>
      </div>
      <div className="card-body">
        <div className="form-grid">
          <label className="form-field" htmlFor="evaluate-flag">
            Flag
            <input
              id="evaluate-flag"
              placeholder="flag-name"
              value={flag}
              onChange={(e) => setFlag(e.target.value)}
            />
          </label>
          <label className="form-field" htmlFor="evaluate-user">
            User id
            <input
              id="evaluate-user"
              placeholder="user-1"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            />
          </label>
          <label className="form-field" htmlFor="evaluate-team">
            Team
            <input
              id="evaluate-team"
              placeholder="optional"
              value={team}
              onChange={(e) => setTeam(e.target.value)}
            />
          </label>
        </div>
        <div className="row mt">
          <button id="evaluate" onClick={() => void run()}>
            Evaluate
          </button>
        </div>
        {result && (
          <div id="evaluate-result" className="result">
            {result}
          </div>
        )}
      </div>
    </section>
  );
}
