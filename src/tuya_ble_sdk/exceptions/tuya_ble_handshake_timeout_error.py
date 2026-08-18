"""Error raised when the device never answers the opening of the handshake."""

from __future__ import annotations

from .tuya_ble_connection_error import TuyaBleConnectionError


class TuyaBleHandshakeTimeoutError(TuyaBleConnectionError):
    """
    The link was up and the device ignored the device-information request.

    Kept apart from the plain connection error because the two mean different
    things: the connection succeeded, so the device is awake and in range, and
    the one frame it dropped is the only frame encrypted with a key derived
    from the local key. A single occurrence still means nothing — a busy device
    drops frames too — so it stays a connection error and leaves the consumer
    to decide how many in a row are evidence of wrong credentials.
    """
