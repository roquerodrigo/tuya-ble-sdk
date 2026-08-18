"""Error raised when the credentials are rejected."""

from __future__ import annotations

from .tuya_ble_error import TuyaBleError


class TuyaBleAuthenticationError(TuyaBleError):
    """
    The credentials were rejected.

    Kept apart from the connection error so the integration can start a reauth
    flow instead of retrying forever.
    """
