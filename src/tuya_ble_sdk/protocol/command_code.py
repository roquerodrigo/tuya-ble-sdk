"""The command codes carried in the header of every Tuya BLE frame."""

from __future__ import annotations

from enum import IntEnum


class TuyaBleCommandCode(IntEnum):
    """
    Codes below ``0x8000`` are sent by the client, the rest by the device.

    Only the codes this SDK acts on are listed; anything else the device sends
    is logged and dropped, which is why the parser never converts blindly.
    """

    SENDER_DEVICE_INFO = 0x0000
    SENDER_PAIR = 0x0001
    SENDER_DATA_POINTS = 0x0002
    SENDER_DEVICE_STATUS = 0x0003
    SENDER_UNBIND = 0x0005
    SENDER_DEVICE_RESET = 0x0006

    RECEIVE_DATA_POINT = 0x8001
    RECEIVE_TIME_DATA_POINT = 0x8003
    RECEIVE_SIGNED_DATA_POINT = 0x8004
    RECEIVE_SIGNED_TIME_DATA_POINT = 0x8005
    RECEIVE_UNIX_TIME_REQUEST = 0x8011
    RECEIVE_LOCAL_TIME_REQUEST = 0x8012

    @classmethod
    def from_value(cls, value: int) -> TuyaBleCommandCode | None:
        """Return the matching member, or ``None`` when the code is unknown."""
        try:
            return cls(value)
        except ValueError:
            return None
