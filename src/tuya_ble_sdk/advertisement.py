"""Read the identity a Tuya BLE device broadcasts before anyone connects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .crypto import decrypt_advertised_uuid
from .models import AdvertisementInfo
from .protocol import MANUFACTURER_DATA_IDENTIFIER, SERVICE_UUID

if TYPE_CHECKING:
    from collections.abc import Mapping

_PRODUCT_ID_RECORD = 0
_MINIMUM_RECORD_LENGTH = 2
_BOUND_FLAG = 0x80
_UUID_OFFSET = 6


def parse_advertisement(
    service_data: Mapping[str, bytes],
    manufacturer_data: Mapping[int, bytes],
) -> AdvertisementInfo:
    """
    Extract the product id, the uuid and the binding state from an advertisement.

    Every field is optional: the uuid only becomes readable when both records
    are present, since the product-id record is what decrypts it.
    """
    raw_product_id = _parse_product_id(service_data.get(SERVICE_UUID))
    payload = manufacturer_data.get(MANUFACTURER_DATA_IDENTIFIER)
    if payload is None or len(payload) <= _UUID_OFFSET:
        return AdvertisementInfo(
            product_id=_readable(raw_product_id),
            uuid=None,
            protocol_version=None,
            is_bound=False,
        )
    return AdvertisementInfo(
        product_id=_readable(raw_product_id),
        uuid=_parse_uuid(raw_product_id, payload[_UUID_OFFSET:]),
        protocol_version=payload[1],
        is_bound=bool(payload[0] & _BOUND_FLAG),
    )


def _parse_product_id(service_data: bytes | None) -> bytes | None:
    """
    Return the product-id record as it was broadcast.

    It stays bytes: a bound device broadcasts an obfuscated value here instead
    of the printable product id, and those bytes are still exactly the key
    material the uuid was encrypted with.
    """
    if service_data is None or len(service_data) < _MINIMUM_RECORD_LENGTH:
        return None
    if service_data[0] != _PRODUCT_ID_RECORD:
        return None
    return service_data[1:]


def _readable(raw_product_id: bytes | None) -> str | None:
    """Return the product id as text, when the device broadcasts it in the clear."""
    if raw_product_id is None or not raw_product_id.isascii():
        return None
    if not raw_product_id.isalnum():
        return None
    return raw_product_id.decode()


def _parse_uuid(raw_product_id: bytes | None, encrypted_uuid: bytes) -> str | None:
    """Decrypt the uuid, which is only possible once the product record is known."""
    if raw_product_id is None:
        return None
    return decrypt_advertised_uuid(raw_product_id, encrypted_uuid)
