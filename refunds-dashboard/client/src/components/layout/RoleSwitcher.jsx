import { ROLE_PROFILES, useRole } from "../../context/RoleContext.jsx";

/** Mocked role switcher — it changes the headers we send, not real permissions. */
export function RoleSwitcher() {
  const { actor, switchRole } = useRole();

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
