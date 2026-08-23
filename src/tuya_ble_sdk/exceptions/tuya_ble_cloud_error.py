"""Error raised when the Tuya cloud rejects a call."""

from __future__ import annotations

from .tuya_ble_error import TuyaBleError


class TuyaBleCloudError(TuyaBleError):
    """
    The gateway answered, and the answer was a rejection.

    The error code is kept apart from the message because it is the only part
    the caller can branch on: the message is localized to the account.
    """

    def __init__(self, api: str, code: str, message: str) -> None:
        """Describe which call was rejected, and how."""
        super().__init__(f"Failed to call {api}: {message} ({code})")
        self.api = api
        self.code = code
