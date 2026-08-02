/** Forwards rejected promises from route handlers to the Express error handler. */
export function asyncHandler(handler) {
  return (req, res, next) =>
    Promise.resolve(handler(req, res, next)).catch(next);
}
