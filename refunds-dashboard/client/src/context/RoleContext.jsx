import { createContext, useContext, useMemo, useState } from "react";
import PropTypes from "prop-types";

export const ROLES = {
  SUPPORT_AGENT: "support_agent",
  FINANCE_APPROVER: "finance_approver",
};

export const ROLE_PROFILES = [
  { role: ROLES.SUPPORT_AGENT, name: "agent.riley", label: "Support agent" },
  {
    role: ROLES.FINANCE_APPROVER,
    name: "finance.dana",
    label: "Finance approver",
  },
];

const RoleContext = createContext(null);

/** Holds the mocked active user. Replacing this with real auth is a separate task. */
export function RoleProvider({ children }) {
  const [actor, setActor] = useState(ROLE_PROFILES[0]);

  const value = useMemo(
    () => ({
      actor,
      isFinanceApprover: actor.role === ROLES.FINANCE_APPROVER,
      switchRole: (role) =>
        setActor(
          ROLE_PROFILES.find((profile) => profile.role === role) ??
            ROLE_PROFILES[0],
        ),
    }),
    [actor],
  );

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>;
}

RoleProvider.propTypes = { children: PropTypes.node };

export function useRole() {
  const context = useContext(RoleContext);
  if (!context) {
    throw new Error("useRole must be used inside a RoleProvider");
  }
  return context;
}
