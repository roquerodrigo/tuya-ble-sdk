"""One Tuya BLE frame: its header, its CRC and its trip through AES."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from struct import pack, unpack

from ..crypto import (
    BLOCK_SIZE,
    crc16,
    decrypt,
    encrypt,
    random_initialization_vector,
)
from ..exceptions import TuyaBleProtocolError
from .constants import CRC_LENGTH, FRAME_HEADER_LENGTH, GATT_MTU
from .varint import pack_varint

_HEADER_FORMAT = ">IIHH"
_INITIALIZATION_VECTOR_END = 1 + BLOCK_SIZE
_MINIMUM_PAYLOAD_LENGTH = _INITIALIZATION_VECTOR_END + BLOCK_SIZE
_PROTOCOL_VERSION_SHIFT = 4


def security_flag_of(payload: bytes) -> int:
    """
    Return the flag that says which key a received payload was encrypted with.

    It is read before decryption on purpose: the caller owns the keys and the
    frame cannot say which one applies until this byte has been looked at.
    """
    if not payload:
        message = "Failed to read a frame: the payload is empty"
        raise TuyaBleProtocolError(message)
    return payload[0]


def build_packets(payload: bytes, protocol_version: int) -> list[bytes]:
    """
    Split one encrypted payload into the fragments a 20-byte MTU allows.

    Every fragment opens with its own index; the first one also carries the
    total length and the protocol version, so the device knows when it has the
    whole frame.
    """
    packets: list[bytes] = []
    position = 0
    index = 0
    while position < len(payload):
        header = bytearray(pack_varint(index))
        if index == 0:
            header += pack_varint(len(payload))
            header += pack(">B", protocol_version << _PROTOCOL_VERSION_SHIFT)
        chunk = payload[position : position + GATT_MTU - len(header)]
        packets.append(bytes(header + chunk))
        position += len(chunk)
        index += 1
    return packets


@dataclass(frozen=True, slots=True)
class Frame:
    """
    The unit of conversation with a Tuya BLE device.

    ``code`` stays an ``int`` rather than a :class:`TuyaBleCommandCode`: the
    device emits codes this SDK does not implement, and a frame carrying one
    must still decode so it can be logged and ignored.
    """

    sequence_number: int
    response_to: int
    code: int
    data: bytes

    def encode(self, key: bytes, security_flag: int) -> bytes:
        """Return the encrypted payload of this frame, ready to be fragmented."""
        plaintext = bytearray(
            pack(
                _HEADER_FORMAT,
                self.sequence_number,
                self.response_to,
                self.code,
                len(self.data),
            )
        )
        plaintext += self.data
        plaintext += pack(">H", crc16(bytes(plaintext)))
        plaintext += bytes(-len(plaintext) % BLOCK_SIZE)
        initialization_vector = random_initialization_vector()
        return (
            pack(">B", security_flag)
            + initialization_vector
            + encrypt(key, initialization_vector, bytes(plaintext))
        )

    @classmethod
    def decode(cls, payload: bytes, key: bytes) -> Frame:
        """Decrypt a reassembled payload and validate its header and CRC."""
        if len(payload) < _MINIMUM_PAYLOAD_LENGTH:
            message = (
                f"Failed to read a frame: {len(payload)} bytes is shorter than "
                "the initialization vector plus one block"
            )
            raise TuyaBleProtocolError(message)
        ciphertext = payload[_INITIALIZATION_VECTOR_END:]
        if len(ciphertext) % BLOCK_SIZE != 0:
            message = (
                f"Failed to read a frame: {len(ciphertext)} bytes is not a whole "
                "number of AES blocks"
            )
            raise TuyaBleProtocolError(message)
        plaintext = decrypt(key, payload[1:_INITIALIZATION_VECTOR_END], ciphertext)
        try:
            sequence_number, response_to, code, length = unpack(
                _HEADER_FORMAT, plaintext[:FRAME_HEADER_LENGTH]
            )
        except struct.error as exception:
            message = f"Failed to read a frame header: {exception}"
            raise TuyaBleProtocolError(message) from exception
        end = FRAME_HEADER_LENGTH + length
        if len(plaintext) < end:
            message = (
                f"Failed to read a frame: it declares {length} bytes of data but "
                f"only {len(plaintext) - FRAME_HEADER_LENGTH} arrived"
            )
            raise TuyaBleProtocolError(message)
        _verify_crc_or_raise(plaintext, end)
        return cls(
            sequence_number=sequence_number,
            response_to=response_to,
            code=code,
            data=plaintext[FRAME_HEADER_LENGTH:end],
        )


def _verify_crc_or_raise(plaintext: bytes, end: int) -> None:
    """
    Check the checksum that follows the data, when the padding left room for it.

    A frame whose data fills the last block exactly carries no CRC, so its
    absence is not an error.
    """
    if len(plaintext) < end + CRC_LENGTH:
        return
    (declared,) = unpack(">H", plaintext[end : end + CRC_LENGTH])
    computed = crc16(plaintext[:end])
    if declared != computed:
        message = (
            f"Failed to verify a frame: CRC {declared:#06x} does not match the "
            f"computed {computed:#06x}"
        )
        raise TuyaBleProtocolError(message)
