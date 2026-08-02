import { AppError } from "../utils/AppError.js";

/** Rejects non-numeric :id path params before they reach the data layer. */
export function validateNumericId(req, res, next) {
  const id = Number(req.params.id);

  if (!Number.isInteger(id) || id <= 0) {
    return next(
      AppError.badRequest(`Invalid refund request id "${req.params.id}"`),
    );
  }

  req.refundRequestId = id;
  return next();
}
