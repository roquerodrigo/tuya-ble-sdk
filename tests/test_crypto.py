from __future__ import annotations

from hashlib import md5

import pytest

from tuya_ble_sdk.crypto import (
    BLOCK_SIZE,
    crc16,
    decrypt,
    decrypt_advertised_uuid,
    encrypt,
    key_material,
    login_key,
    random_initialization_vector,
    session_key,
)
from tuya_ble_sdk.exceptions import TuyaBleProtocolError


def test_crc16_matches_the_modbus_reference_vector():
    assert crc16(b"123456789") == 0x4B37


def test_crc16_of_nothing_is_the_seed():
    assert crc16(b"") == 0xFFFF


def test_key_material_is_the_first_six_characters():
    assert key_material("abcdef0123456789") == b"abcdef"


def test_login_key_is_the_digest_of_the_key_material():
    assert login_key("abcdef0123456789") == md5(b"abcdef").digest()


def test_session_key_salts_the_key_material_with_srand():
    assert session_key("abcdef0123456789", b"srand!") == md5(b"abcdefsrand!").digest()


def test_initialization_vectors_are_one_block_long_and_differ():
    assert len(random_initialization_vector()) == BLOCK_SIZE
    assert random_initialization_vector() != random_initialization_vector()


def test_encrypt_and_decrypt_round_trip():
    key = login_key("abcdef0123456789")
    initialization_vector = random_initialization_vector()
    plaintext = bytes(range(BLOCK_SIZE * 2))
    encrypted = encrypt(key, initialization_vector, plaintext)
    assert encrypted != plaintext
    assert decrypt(key, initialization_vector, encrypted) == plaintext


def test_advertised_uuid_is_recovered_with_the_product_id():
    product_id = b"gvygg3m8"
    key = md5(product_id).digest()
    encrypted = encrypt(key, key, b"0123456789abcdef")
    assert decrypt_advertised_uuid(product_id, encrypted) == "0123456789abcdef"


def test_advertised_uuid_rejects_a_partial_block():
    with pytest.raises(TuyaBleProtocolError, match="whole number of AES blocks"):
        decrypt_advertised_uuid(b"gvygg3m8", b"short")


def test_advertised_uuid_rejects_undecodable_bytes():
    product_id = b"gvygg3m8"
    key = md5(product_id).digest()
    encrypted = encrypt(key, key, bytes([0xFF]) * BLOCK_SIZE)
    with pytest.raises(TuyaBleProtocolError, match="Failed to decode"):
        decrypt_advertised_uuid(product_id, encrypted)
