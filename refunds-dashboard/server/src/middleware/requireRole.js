import { ROLE_LABELS } from "../constants/roles.js";
import { AppError } from "../utils/AppError.js";

/** Blocks the request unless the mocked actor holds one of the allowed roles. */
export function requireRole(...allowedRoles) {
  return function roleGuard(req, res, next) {
    if (!req.actor || !allowedRoles.includes(req.actor.role)) {
      const labels = allowedRoles
        .map((role) => ROLE_LABELS[role] ?? role)
        .join(" or ");
      return next(
        AppError.forbidden(`This action requires the ${labels} role`),
      );
    }
    return next();
  };
}
