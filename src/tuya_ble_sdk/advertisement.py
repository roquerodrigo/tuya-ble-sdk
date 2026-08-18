"""Read the identity a Tuya BLE device broadcasts before anyone connects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .crypto import decrypt_advertised_uuid
from .exceptions import TuyaBleProtocolError
from .models import AdvertisementInfo
from .protocol import MANUFACTURER_DATA_IDENTIFIER, SERVICE_UUID

if TYPE_CHECKING:
    from collections.abc import Mapping

_PRODUCT_ID_RECORD = 0
_BOUND_FLAG = 0x80
_UUID_OFFSET = 6


def parse_advertisement(
    service_data: Mapping[str, bytes],
    manufacturer_data: Mapping[int, bytes],
) -> AdvertisementInfo:
    """
    Extract the product id, the uuid and the binding state from an advertisement.

    Every field is optional: a device that advertises only the service data
    still identifies its product, and the uuid only becomes readable when both
    records are present, since the product id is what decrypts it.
    """
    product_id = _parse_product_id(service_data.get(SERVICE_UUID))
    payload = manufacturer_data.get(MANUFACTURER_DATA_IDENTIFIER)
    if payload is None or len(payload) <= _UUID_OFFSET:
        return AdvertisementInfo(
            product_id=product_id,
            uuid=None,
            protocol_version=None,
            is_bound=False,
        )
    return AdvertisementInfo(
        product_id=product_id,
        uuid=_parse_uuid(product_id, payload[_UUID_OFFSET:]),
        protocol_version=payload[1],
        is_bound=bool(payload[0] & _BOUND_FLAG),
    )


def _parse_product_id(service_data: bytes | None) -> str | None:
    """Read the product id out of the service data record that carries it."""
    if service_data is None or len(service_data) < 2:  # noqa: PLR2004 -- a record is a type byte plus content
        return None
    if service_data[0] != _PRODUCT_ID_RECORD:
        return None
    try:
        return service_data[1:].decode()
    except UnicodeDecodeError as exception:
        message = f"Failed to read the advertised product id: {exception}"
        raise TuyaBleProtocolError(message) from exception


def _parse_uuid(product_id: str | None, encrypted_uuid: bytes) -> str | None:
    """Decrypt the uuid, which is only possible once the product id is known."""
    if product_id is None:
        return None
    return decrypt_advertised_uuid(product_id.encode(), encrypted_uuid)
