export const ROLES = {
  SUPPORT_AGENT: "support_agent",
  FINANCE_APPROVER: "finance_approver",
};

export const ROLE_LABELS = {
  [ROLES.SUPPORT_AGENT]: "Support agent",
  [ROLES.FINANCE_APPROVER]: "Finance approver",
};

export const ALL_ROLES = Object.values(ROLES);

export function isKnownRole(role) {
  return ALL_ROLES.includes(role);
}
