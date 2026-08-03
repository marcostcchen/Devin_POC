import { config } from "../config/env.js";
import { ROLES, isKnownRole } from "../constants/roles.js";
import { AppError } from "../utils/AppError.js";

const DEFAULT_ACTOR_NAMES = {
  [ROLES.SUPPORT_AGENT]: "agent.demo",
  [ROLES.FINANCE_APPROVER]: "finance.demo",
};

/**
 * Mocked identity. Standalone, the role switcher in the UI sends
 * `x-user-role`/`x-user-name`; under the POC platform the gateway injects the
 * selected persona as `x-platform-role`/`x-platform-user[-name]` and strips any
 * copy the browser sent. Either way this is not authentication — it only exists
 * to demo RBAC behaviour.
 */
export function currentActor(req, res, next) {
  const platformRole = config.platformManaged
    ? req.get("x-platform-role")
    : null;
  const role = platformRole ?? req.get("x-user-role") ?? ROLES.SUPPORT_AGENT;
  const header = platformRole ? "x-platform-role" : "x-user-role";

  if (!isKnownRole(role)) {
    return next(
      AppError.badRequest(`Unknown role "${role}" in ${header} header`),
    );
  }

  const platformName = platformRole
    ? (req.get("x-platform-user-name") ?? req.get("x-platform-user"))
    : null;

  req.actor = {
    role,
    name:
      platformName?.trim() ||
      req.get("x-user-name")?.trim() ||
      DEFAULT_ACTOR_NAMES[role],
    platformManaged: Boolean(platformRole),
  };

  return next();
}
