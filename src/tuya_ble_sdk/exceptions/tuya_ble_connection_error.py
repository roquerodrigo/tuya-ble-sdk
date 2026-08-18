"""Error raised when the device or service cannot be reached."""

from __future__ import annotations

from .tuya_ble_error import TuyaBleError


class TuyaBleConnectionError(TuyaBleError):
    """The request never completed: timeout, DNS, refused connection."""
