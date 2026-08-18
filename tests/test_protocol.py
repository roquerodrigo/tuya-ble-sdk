from __future__ import annotations

import pytest

from tuya_ble_sdk.crypto import BLOCK_SIZE, crc16, encrypt, login_key
from tuya_ble_sdk.exceptions import TuyaBleProtocolError
from tuya_ble_sdk.protocol import (
    GATT_MTU,
    SECURITY_FLAG_SESSION_KEY,
    DataPointType,
    Frame,
    PacketReassembler,
    TuyaBleCommandCode,
    build_packets,
    pack_varint,
    security_flag_of,
    unpack_varint,
)

KEY = login_key("abcdef0123456789")


@pytest.mark.parametrize(
    ("value", "encoded"),
    [
        (0, b"\x00"),
        (1, b"\x01"),
        (127, b"\x7f"),
        (128, b"\x80\x01"),
        (300, b"\xac\x02"),
    ],
)
def test_varint_round_trip(value, encoded):
    assert pack_varint(value) == encoded
    assert unpack_varint(encoded, 0) == (value, len(encoded))


def test_unpack_varint_rejects_a_truncated_integer():
    with pytest.raises(TuyaBleProtocolError, match="ends mid-integer"):
        unpack_varint(b"\x80", 0)


def test_unpack_varint_rejects_an_integer_that_never_terminates():
    with pytest.raises(TuyaBleProtocolError, match="never terminates"):
        unpack_varint(b"\x80\x80\x80\x80\x80", 0)


def test_command_code_returns_none_for_an_unknown_value():
    assert (
        TuyaBleCommandCode.from_value(0x0000) is TuyaBleCommandCode.SENDER_DEVICE_INFO
    )
    assert TuyaBleCommandCode.from_value(0x7FFF) is None


def test_data_point_types_follow_the_protocol_numbering():
    assert DataPointType.RAW == 0
    assert DataPointType.BITMAP == 5


def test_frame_round_trips_through_encryption():
    frame = Frame(sequence_number=7, response_to=0, code=0x0003, data=b"payload")
    payload = frame.encode(KEY, SECURITY_FLAG_SESSION_KEY)
    assert security_flag_of(payload) == SECURITY_FLAG_SESSION_KEY
    assert Frame.decode(payload, KEY) == frame


def test_encoded_payload_is_flag_plus_vector_plus_whole_blocks():
    payload = Frame(sequence_number=1, response_to=0, code=0, data=b"").encode(
        KEY, SECURITY_FLAG_SESSION_KEY
    )
    assert (len(payload) - 1 - BLOCK_SIZE) % BLOCK_SIZE == 0


def test_security_flag_of_rejects_an_empty_payload():
    with pytest.raises(TuyaBleProtocolError, match="payload is empty"):
        security_flag_of(b"")


def test_decode_rejects_a_payload_shorter_than_one_block():
    with pytest.raises(TuyaBleProtocolError, match="shorter than"):
        Frame.decode(b"\x05" + bytes(BLOCK_SIZE), KEY)


def test_decode_rejects_a_partial_block():
    with pytest.raises(TuyaBleProtocolError, match="whole number of AES blocks"):
        Frame.decode(b"\x05" + bytes(BLOCK_SIZE) + bytes(BLOCK_SIZE + 1), KEY)


def _encrypted(plaintext: bytes) -> bytes:
    initialization_vector = bytes(BLOCK_SIZE)
    return (
        bytes([SECURITY_FLAG_SESSION_KEY])
        + initialization_vector
        + encrypt(KEY, initialization_vector, plaintext)
    )


def test_decode_rejects_a_frame_that_declares_more_data_than_it_carries():
    plaintext = bytes(8) + (0x0003).to_bytes(2, "big") + (200).to_bytes(2, "big")
    with pytest.raises(TuyaBleProtocolError, match="only"):
        Frame.decode(_encrypted(plaintext + bytes(4)), KEY)


def test_decode_rejects_a_bad_checksum():
    header = bytes(8) + (0x0003).to_bytes(2, "big") + (2).to_bytes(2, "big")
    plaintext = header + b"hi" + b"\x00\x00"
    with pytest.raises(TuyaBleProtocolError, match="does not match"):
        Frame.decode(_encrypted(plaintext), KEY)


def test_decode_accepts_a_frame_whose_data_leaves_no_room_for_a_checksum():
    header = bytes(8) + (0x0003).to_bytes(2, "big") + (4).to_bytes(2, "big")
    plaintext = header + b"data"
    assert Frame.decode(_encrypted(plaintext), KEY).data == b"data"


def test_checksum_covers_the_header_and_the_data():
    header = bytes(8) + (0x0003).to_bytes(2, "big") + (2).to_bytes(2, "big")
    plaintext = header + b"hi"
    plaintext += crc16(plaintext).to_bytes(2, "big")
    assert Frame.decode(_encrypted(plaintext), KEY).data == b"hi"


def test_packets_never_exceed_the_mtu_and_reassemble():
    payload = bytes(range(200))
    packets = build_packets(payload, 3)
    assert len(packets) > 1
    assert all(len(packet) <= GATT_MTU for packet in packets)
    reassembler = PacketReassembler()
    assert [reassembler.feed(packet) for packet in packets][-1] == payload


def test_a_single_short_payload_is_one_packet():
    packets = build_packets(b"abc", 3)
    assert len(packets) == 1
    assert PacketReassembler().feed(packets[0]) == b"abc"


def test_reassembler_rejects_a_missing_fragment():
    packets = build_packets(bytes(range(200)), 3)
    reassembler = PacketReassembler()
    reassembler.feed(packets[0])
    with pytest.raises(TuyaBleProtocolError, match="arrived where"):
        reassembler.feed(packets[2])


def test_reassembler_recovers_after_a_missing_fragment():
    packets = build_packets(bytes(range(200)), 3)
    reassembler = PacketReassembler()
    reassembler.feed(packets[0])
    with pytest.raises(TuyaBleProtocolError):
        reassembler.feed(packets[2])
    assert [reassembler.feed(packet) for packet in packets][-1] == bytes(range(200))


def test_reassembler_rejects_a_truncated_first_fragment():
    reassembler = PacketReassembler()
    with pytest.raises(TuyaBleProtocolError, match="truncated"):
        reassembler.feed(b"\x00\x0a")


def test_reassembler_rejects_more_bytes_than_declared():
    reassembler = PacketReassembler()
    with pytest.raises(TuyaBleProtocolError, match="declared length"):
        reassembler.feed(b"\x00\x02\x30" + bytes(5))
