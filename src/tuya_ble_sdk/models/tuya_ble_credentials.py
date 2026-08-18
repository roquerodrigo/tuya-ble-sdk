"""Credentials needed to open a session with one Tuya BLE device."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TuyaBleCredentials:
    """
    The three values the pairing handshake needs.

    ``uuid`` comes from the advertisement (or from the Tuya account),
    ``device_id`` and ``local_key`` from the Tuya account. Only the first six
    characters of the local key take part in the key derivation, but the whole
    value is kept so a device that changes that rule keeps working.
    """

    uuid: str
    device_id: str
    local_key: str
