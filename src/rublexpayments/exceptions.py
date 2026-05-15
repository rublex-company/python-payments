"""Exception types raised by the Rublex SDK.

(c) Rublex Team <payments@rublex.io>
"""


class RublexError(Exception):
    """Base error for everything raised by the Rublex SDK."""


class RublexConfigError(RublexError):
    """Raised when required configuration (e.g. the API key) is missing."""


class RublexRequestError(RublexError):
    """Raised on network failures or non-JSON responses from the gateway."""

    def __init__(self, message, status=None, body=None):
        super().__init__(message)
        self.status = status
        self.body = body
