import { ROLE_PROFILES, useRole } from "../../context/RoleContext.jsx";

/**
 * Mocked role switcher — it changes the headers we send, not real permissions.
 * Under the POC platform the persona comes from the platform console, so the
 * switcher becomes a read-only label pointing back there.
 */
export function RoleSwitcher() {
  const { actor, platform, switchRole } = useRole();

  if (platform.managed) {
    return (
      <div className="role-switcher">
        <span className="role-switcher__label">Acting as</span>
        <strong>
          {actor.label} ({actor.name})
        </strong>
        <a href={platform.consoleUrl || "/"}>switch in the platform console</a>
      </div>
    );
  }

  return (
    <div className="role-switcher">
      <label className="role-switcher__label" htmlFor="role-select">
        Acting as
      </label>
      <select
        id="role-select"
        className="role-switcher__select"
        value={actor.role}
        onChange={(event) => switchRole(event.target.value)}
      >
        {ROLE_PROFILES.map((profile) => (
          <option key={profile.role} value={profile.role}>
            {profile.label} ({profile.name})
          </option>
        ))}
      </select>
    </div>
  );
}
