"""One device as the Tuya account describes it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CloudDevice:
    """
    What the account knows about a device, credentials included.

    ``uuid`` and ``mac`` are what tie this record to a device seen over the
    air: the advertisement discloses the uuid, and the Bluetooth address is the
    same value as ``mac``, formatted. ``device_id`` and ``local_key`` are what
    a BLE session needs and nothing but the account can tell.
    """

    device_id: str
    local_key: str
    uuid: str
    mac: str
    product_id: str | None
    name: str
