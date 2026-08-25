"""
Jio AI Cloud SDK - Custom Exceptions
"""

class JioCloudError(Exception):
    """Base exception class for all Jio Cloud SDK errors."""
    def __init__(self, message: str = "Unknown Jio Cloud error", status_code=None, error_code=None, raw_response=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.raw_response = raw_response

    def __str__(self):
        err = self.message
        if self.status_code:
            err = f"[{self.status_code}] {err}"
        if self.error_code:
            err = f"{err} (Code: {self.error_code})"
        return err


class AuthenticationError(JioCloudError):
    """Raised when authentication credentials or tokens are invalid/expired (HTTP 401)."""


class ForbiddenError(JioCloudError):
    """Raised when the requested operation is forbidden (HTTP 403)."""


class ObjectNotFoundError(JioCloudError):
    """Raised when a file, folder, or object key is not found (HTTP 404)."""


class InvalidRequestError(JioCloudError):
    """Raised when request parameters, query, or body are invalid (HTTP 400)."""


class QuotaExceededError(JioCloudError):
    """Raised when user account storage quota is full."""


class RateLimitError(JioCloudError):
    """Raised when too many requests are sent in a short timeframe (HTTP 429)."""


class ConflictError(JioCloudError):
    """Raised on HTTP 409 conflicts (e.g., duplicate folder name at destination)."""


class PayloadTooLargeError(JioCloudError):
    """Raised when an entity/body exceeds server limits (HTTP 413)."""


class ServerError(JioCloudError):
    """Raised on upstream server faults (HTTP 5xx)."""


class NetworkError(JioCloudError):
    """Raised when the connection to Jio Cloud fails entirely (DNS, timeout, reset)."""
