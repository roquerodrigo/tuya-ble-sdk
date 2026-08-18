from __future__ import annotations

from hashlib import md5

import pytest

from tuya_ble_sdk import parse_advertisement
from tuya_ble_sdk.crypto import encrypt
from tuya_ble_sdk.exceptions import TuyaBleProtocolError
from tuya_ble_sdk.protocol import MANUFACTURER_DATA_IDENTIFIER, SERVICE_UUID

PRODUCT_ID = "gvygg3m8"
UUID = "0123456789abcdef"


def _service_data(product_id: str = PRODUCT_ID) -> dict[str, bytes]:
    return {SERVICE_UUID: b"\x00" + product_id.encode()}


def _manufacturer_data(*, bound: bool = False) -> dict[int, bytes]:
    key = md5(PRODUCT_ID.encode()).digest()
    header = bytes([0x80 if bound else 0x00, 3, 0, 0, 1, 0])
    return {MANUFACTURER_DATA_IDENTIFIER: header + encrypt(key, key, UUID.encode())}


def test_a_full_advertisement_yields_every_field():
    info = parse_advertisement(_service_data(), _manufacturer_data(bound=True))
    assert info.product_id == PRODUCT_ID
    assert info.uuid == UUID
    assert info.protocol_version == 3
    assert info.is_bound is True


def test_an_unbound_device_reports_it():
    assert parse_advertisement(_service_data(), _manufacturer_data()).is_bound is False


def test_service_data_alone_identifies_the_product_but_not_the_device():
    info = parse_advertisement(_service_data(), {})
    assert info.product_id == PRODUCT_ID
    assert info.uuid is None
    assert info.protocol_version is None


def test_manufacturer_data_alone_leaves_the_uuid_encrypted():
    info = parse_advertisement({}, _manufacturer_data())
    assert info.product_id is None
    assert info.uuid is None
    assert info.protocol_version == 3


def test_a_short_manufacturer_record_is_ignored():
    info = parse_advertisement(_service_data(), {MANUFACTURER_DATA_IDENTIFIER: b"\x00"})
    assert info.uuid is None
    assert info.is_bound is False


def test_another_service_record_type_is_not_a_product_id():
    info = parse_advertisement({SERVICE_UUID: b"\x01abc"}, {})
    assert info.product_id is None


def test_an_empty_service_record_is_not_a_product_id():
    assert parse_advertisement({SERVICE_UUID: b"\x00"}, {}).product_id is None


def test_an_obfuscated_product_record_still_yields_the_uuid():
    """A bound device broadcasts bytes that name no product but decrypt the uuid."""
    raw = bytes.fromhex("5bdcee4a9b776f7a")
    key = md5(raw).digest()
    manufacturer_data = {
        MANUFACTURER_DATA_IDENTIFIER: bytes([0x80, 3, 0, 0, 1, 0])
        + encrypt(key, key, UUID.encode())
    }

    info = parse_advertisement({SERVICE_UUID: b"\x00" + raw}, manufacturer_data)

    assert info.product_id is None
    assert info.uuid == UUID
    assert info.is_bound is True


def test_a_partial_block_of_encrypted_uuid_is_a_protocol_error():
    manufacturer_data = {MANUFACTURER_DATA_IDENTIFIER: bytes(6) + b"short"}

    with pytest.raises(TuyaBleProtocolError, match="whole number of AES blocks"):
        parse_advertisement(_service_data(), manufacturer_data)


def test_an_undecodable_uuid_is_a_protocol_error():
    key = md5(PRODUCT_ID.encode()).digest()
    manufacturer_data = {
        MANUFACTURER_DATA_IDENTIFIER: bytes(6) + encrypt(key, key, bytes([0xFF]) * 16)
    }

    with pytest.raises(TuyaBleProtocolError, match="Failed to decode"):
        parse_advertisement(_service_data(), manufacturer_data)
