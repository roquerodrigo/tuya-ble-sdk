"""Error raised when a frame coming off the wire cannot be trusted."""

from __future__ import annotations

from .tuya_ble_error import TuyaBleError


class TuyaBleProtocolError(TuyaBleError):
    """
    A received packet was malformed, truncated or failed its CRC.

    Distinct from the connection error: the link is up and the device answered,
    the answer just does not parse.
    """
