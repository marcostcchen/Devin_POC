import { AppError } from "../utils/AppError.js";

export function notFoundHandler(req, res) {
  res
    .status(404)
    .json({
      error: {
        message: `Route ${req.method} ${req.originalUrl} does not exist`,
      },
    });
}

/* eslint-disable-next-line no-unused-vars -- Express identifies error handlers by arity. */
export function errorHandler(error, req, res, next) {
  if (error instanceof AppError) {
    return res.status(error.statusCode).json({
      error: { message: error.message, details: error.details },
    });
  }

  console.error("Unhandled error while serving request:", error);
  return res
    .status(500)
    .json({ error: { message: "Unexpected server error" } });
}
