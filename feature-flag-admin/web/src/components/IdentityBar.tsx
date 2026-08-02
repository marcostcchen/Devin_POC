/** Sticky top bar: product mark, "acting as" switcher and the current role. */

import type { Identity } from "../types";

interface Props {
  identity: Identity | null;
  onActAs: (email: string) => void;
}

export function IdentityBar({ identity, onActAs }: Props) {
  const role = identity?.role ?? "…";

  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">
          ⚑
        </span>
        <span>
          <h1>Feature Flags</h1>
          <span className="brand-sub">Internal admin panel</span>
        </span>
      </div>

      {identity?.platform_managed ? (
        <span className="field-inline">
          Acting as
          <strong>{identity.display_name || identity.email}</strong>
          <a href={identity.platform_console_url || "/"}>switch in the platform console</a>
        </span>
      ) : (
        <label className="field-inline" htmlFor="user">
          Acting as
          <select
            id="user"
            value={identity?.email ?? ""}
            onChange={(event) => onActAs(event.target.value)}
          >
            {Object.entries(identity?.users ?? {}).map(([email, userRole]) => (
              <option key={email} value={email}>
                {email} ({userRole})
              </option>
            ))}
          </select>
        </label>
      )}

      <span className={`pill ${role === "admin" ? "accent" : ""}`} title="Current role">
        {role === "admin" ? "admin · can edit" : `${role} · read-only`}
      </span>
    </header>
  );
}
