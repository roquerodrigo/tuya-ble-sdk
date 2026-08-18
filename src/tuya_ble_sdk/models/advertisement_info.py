"""What a Tuya BLE advertisement discloses before any connection is made."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdvertisementInfo:
    """
    The identity a Tuya BLE device broadcasts.

    ``uuid`` is only present when the advertisement carried both the product id
    and the encrypted identifier, since the product id is the decryption key.
    """

    product_id: str | None
    uuid: str | None
    protocol_version: int | None
    is_bound: bool
