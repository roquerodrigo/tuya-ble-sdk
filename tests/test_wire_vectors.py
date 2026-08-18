"""
Frozen wire output, byte for byte.

The expected bytes were produced by the reference implementation this SDK was
ported from (PlusPlus-ua/ha_tuya_ble) for the same inputs, with the per-frame
initialization vector fixed so the ciphertext is reproducible. They are the
only check that survives a refactor of the framing code: everything else in
the suite compares this implementation against itself.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tuya_ble_sdk.crypto import login_key, session_key
from tuya_ble_sdk.protocol import (
    SECURITY_FLAG_LOGIN_KEY,
    SECURITY_FLAG_SESSION_KEY,
    Frame,
    PacketReassembler,
    build_packets,
)

LOCAL_KEY = "abcdef0123456789"
SRAND = b"srand!"
INITIALIZATION_VECTOR = bytes(range(16))
PROTOCOL_VERSION = 3

VECTORS = [
    pytest.param(
        1,
        0x0000,
        b"",
        True,
        [
            "00213004000102030405060708090a0b0c0d0e0f",
            "01f8bc69d43b1f0e3bf28ac34ec4aa2723",
        ],
        id="device_info",
    ),
    pytest.param(
        2,
        0x0001,
        bytes(range(44)),
        False,
        [
            "00513005000102030405060708090a0b0c0d0e0f",
            "01a14a20e14a24729f8aba085a0b3b4c07796414",
            "021f194475ed20400e52052fe5302ff8ab087f9a",
            "0327be3a2bd9df103ff68cacd0dd226d7064bb9f",
            "042845024fe7fb53",
        ],
        id="pair",
    ),
    pytest.param(
        3,
        0x0003,
        b"",
        False,
        [
            "00213005000102030405060708090a0b0c0d0e0f",
            "017949b6c0976133a68068991ec727311a",
        ],
        id="device_status",
    ),
]


def _key_and_flag(login: bool) -> tuple[bytes, int]:
    if login:
        return login_key(LOCAL_KEY), SECURITY_FLAG_LOGIN_KEY
    return session_key(LOCAL_KEY, SRAND), SECURITY_FLAG_SESSION_KEY


@pytest.mark.parametrize(
    ("sequence_number", "code", "data", "login", "packets"), VECTORS
)
def test_the_wire_bytes_are_unchanged(sequence_number, code, data, login, packets):
    key, security_flag = _key_and_flag(login)

    with patch(
        "tuya_ble_sdk.protocol.frame.random_initialization_vector",
        return_value=INITIALIZATION_VECTOR,
    ):
        payload = Frame(
            sequence_number=sequence_number, response_to=0, code=code, data=data
        ).encode(key, security_flag)

    assert [
        packet.hex() for packet in build_packets(payload, PROTOCOL_VERSION)
    ] == packets


@pytest.mark.parametrize(
    ("sequence_number", "code", "data", "login", "packets"), VECTORS
)
def test_the_wire_bytes_decode_back(sequence_number, code, data, login, packets):
    key, _ = _key_and_flag(login)
    reassembler = PacketReassembler()

    payload = None
    for packet in packets:
        payload = reassembler.feed(bytes.fromhex(packet))

    assert payload is not None
    assert Frame.decode(payload, key) == Frame(
        sequence_number=sequence_number, response_to=0, code=code, data=data
    )
