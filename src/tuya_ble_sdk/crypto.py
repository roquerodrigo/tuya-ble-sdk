"""AES, CRC and key derivation for the Tuya BLE protocol."""

from __future__ import annotations

import secrets
from hashlib import md5

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .exceptions import TuyaBleProtocolError

BLOCK_SIZE = 16
_CRC16_INITIAL = 0xFFFF
_CRC16_POLYNOMIAL = 0xA001
_LOCAL_KEY_PREFIX_LENGTH = 6


def crc16(data: bytes) -> int:
    """Compute the CRC-16/MODBUS checksum Tuya appends to every frame."""
    crc = _CRC16_INITIAL
    for byte in data:
        crc ^= byte
        for _ in range(8):
            carry = crc & 1
            crc >>= 1
            if carry:
                crc ^= _CRC16_POLYNOMIAL
    return crc


def key_material(local_key: str) -> bytes:
    """Return the six local-key characters every derived key is built from."""
    return local_key[:_LOCAL_KEY_PREFIX_LENGTH].encode()


def login_key(local_key: str) -> bytes:
    """Derive the key that protects the frames sent before a session exists."""
    return md5(key_material(local_key)).digest()  # noqa: S324 -- the protocol specifies MD5


def session_key(local_key: str, srand: bytes) -> bytes:
    """Derive the key that protects every frame after the handshake."""
    return md5(key_material(local_key) + srand).digest()  # noqa: S324 -- the protocol specifies MD5


def random_initialization_vector() -> bytes:
    """Return a fresh initialization vector; the protocol uses one per frame."""
    return secrets.token_bytes(BLOCK_SIZE)


def encrypt(key: bytes, initialization_vector: bytes, data: bytes) -> bytes:
    """Encrypt block-aligned data with AES-128-CBC."""
    encryptor = Cipher(
        algorithms.AES(key), modes.CBC(initialization_vector)
    ).encryptor()
    return encryptor.update(data) + encryptor.finalize()


def decrypt(key: bytes, initialization_vector: bytes, data: bytes) -> bytes:
    """Decrypt block-aligned data with AES-128-CBC."""
    decryptor = Cipher(
        algorithms.AES(key), modes.CBC(initialization_vector)
    ).decryptor()
    return decryptor.update(data) + decryptor.finalize()


def decrypt_advertised_uuid(raw_product_id: bytes, encrypted_uuid: bytes) -> str:
    """
    Recover the device uuid a Tuya BLE advertisement carries.

    The product-id record broadcast alongside it is the whole secret: its MD5
    digest serves as both the key and the initialization vector. The record is
    hashed as it arrived — a bound device broadcasts bytes that are not the
    printable product id, and those bytes are still the key.
    """
    key = md5(raw_product_id).digest()  # noqa: S324 -- the protocol specifies MD5
    if len(encrypted_uuid) % BLOCK_SIZE != 0:
        message = (
            f"Failed to decrypt the advertised uuid: {len(encrypted_uuid)} bytes "
            "is not a whole number of AES blocks"
        )
        raise TuyaBleProtocolError(message)
    try:
        return decrypt(key, key, encrypted_uuid).decode()
    except UnicodeDecodeError as exception:
        message = f"Failed to decode the advertised uuid: {exception}"
        raise TuyaBleProtocolError(message) from exception
