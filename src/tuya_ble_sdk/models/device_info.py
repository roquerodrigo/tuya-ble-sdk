"""What the device answers to the device-information request."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    """
    The first reply of the handshake, before the session key exists.

    ``srand`` is the per-session salt the session key is derived from, and
    ``is_bound`` reports whether the device still considers itself bound to a
    Tuya account.
    """

    device_version: str
    protocol_version: int
    protocol_version_name: str
    hardware_version: str
    flags: int
    is_bound: bool
    srand: bytes
    auth_key: bytes
