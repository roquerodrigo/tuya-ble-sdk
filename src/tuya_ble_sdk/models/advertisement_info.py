"""What a Tuya BLE advertisement discloses before any connection is made."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdvertisementInfo:
    """
    The identity a Tuya BLE device broadcasts.

    ``uuid`` is only present when the advertisement carried both records, since
    the product-id record is the decryption key. ``product_id`` is only present
    when that record is the printable product id: a bound device broadcasts an
    obfuscated value there, which still decrypts the uuid but names no product.
    """

    product_id: str | None
    uuid: str | None
    protocol_version: int | None
    is_bound: bool
