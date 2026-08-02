/** Header with the "acting as" switcher, current role and the error banner. */

import type { Identity } from "../types";

interface Props {
  identity: Identity | null;
  error: string | null;
  onActAs: (email: string) => void;
}

export function IdentityBar({ identity, error, onActAs }: Props) {
  return (
    <header>
      <h1>Feature Flag Admin</h1>
      <label htmlFor="acting-as">
        Acting as{" "}
        <select
          id="acting-as"
          value={identity?.email ?? ""}
          onChange={(event) => onActAs(event.target.value)}
        >
          {Object.entries(identity?.users ?? {}).map(([email, role]) => (
            <option key={email} value={email}>
              {email} ({role})
            </option>
          ))}
        </select>
      </label>
      <span className={`pill ${identity?.role === "admin" ? "on" : "off"}`}>
        {identity?.role ?? "…"}
      </span>
      {error && <span className="error">⚠ {error}</span>}
    </header>
  );
}
