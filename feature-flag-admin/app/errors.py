"""Domain errors raised by the service layer.

Routers stay free of HTTP plumbing for these cases: `app.main` registers a
handler that maps each error to its `status_code`.
"""


class DomainError(Exception):
    """Base class for expected, user-facing failures."""

    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class FlagNotFound(DomainError):
    status_code = 404


class DuplicateFlag(DomainError):
    status_code = 409


class PermissionDenied(DomainError):
    status_code = 403


class UnknownUser(DomainError):
    status_code = 401
