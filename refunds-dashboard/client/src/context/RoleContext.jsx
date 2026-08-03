import { createContext, useContext, useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { fetchCurrentActor } from "../api/refundsApi.js";

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

const ROLE_LABELS = Object.fromEntries(
  ROLE_PROFILES.map((profile) => [profile.role, profile.label]),
);

const RoleContext = createContext(null);

/**
 * Holds the mocked active user.
 *
 * Standalone, the switcher below picks it. Under the POC platform the gateway
 * decides it from the persona selected in the console, so we adopt whatever
 * `/api/me` reports and lock the switcher. Replacing either with real auth is a
 * separate task.
 */
export function RoleProvider({ children }) {
  const [actor, setActor] = useState(ROLE_PROFILES[0]);
  const [platform, setPlatform] = useState({ managed: false, consoleUrl: "" });

  useEffect(() => {
    let cancelled = false;

    fetchCurrentActor()
      .then((payload) => {
        if (cancelled || !payload.platformManaged) return;
        setPlatform({ managed: true, consoleUrl: payload.platformConsoleUrl });
        setActor({
          role: payload.actor.role,
          name: payload.actor.name,
          label: ROLE_LABELS[payload.actor.role] ?? payload.actor.role,
        });
      })
      .catch(() => {
        // Standalone behaviour is the fallback: keep the local switcher.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo(
    () => ({
      actor,
      platform,
      isFinanceApprover: actor.role === ROLES.FINANCE_APPROVER,
      switchRole: (role) =>
        setActor(
          ROLE_PROFILES.find((profile) => profile.role === role) ??
            ROLE_PROFILES[0],
        ),
    }),
    [actor, platform],
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
