import { ROLES, isKnownRole } from "../constants/roles.js";
import { AppError } from "../utils/AppError.js";

const DEFAULT_ACTOR_NAMES = {
  [ROLES.SUPPORT_AGENT]: "agent.demo",
  [ROLES.FINANCE_APPROVER]: "finance.demo",
};

/**
 * Mocked identity: the role switcher in the UI sends `x-user-role`/`x-user-name`.
 * This is not authentication — it only exists to demo RBAC behaviour.
 */
export function currentActor(req, res, next) {
  const role = req.get("x-user-role") ?? ROLES.SUPPORT_AGENT;

  if (!isKnownRole(role)) {
    return next(
      AppError.badRequest(`Unknown role "${role}" in x-user-role header`),
    );
  }

  req.actor = {
    role,
    name: req.get("x-user-name")?.trim() || DEFAULT_ACTOR_NAMES[role],
  };

  return next();
}
