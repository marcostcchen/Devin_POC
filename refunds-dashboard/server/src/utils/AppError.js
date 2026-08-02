/** Error carrying the HTTP status code that the error handler should return. */
export class AppError extends Error {
  constructor(statusCode, message, details) {
    super(message);
    this.name = "AppError";
    this.statusCode = statusCode;
    this.details = details;
  }

  static badRequest(message, details) {
    return new AppError(400, message, details);
  }

  static forbidden(message) {
    return new AppError(403, message);
  }

  static notFound(message) {
    return new AppError(404, message);
  }

  static conflict(message) {
    return new AppError(409, message);
  }
}
