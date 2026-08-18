"""The little-endian base-128 integers that prefix every BLE fragment."""

from __future__ import annotations

from ..exceptions import TuyaBleProtocolError

_CONTINUATION_BIT = 0x80
_VALUE_MASK = 0x7F
_BITS_PER_BYTE = 7
_MAX_BYTES = 4


def pack_varint(value: int) -> bytes:
    """Encode a non-negative integer as a variable-length integer."""
    encoded = bytearray()
    while True:
        current = value & _VALUE_MASK
        value >>= _BITS_PER_BYTE
        if value:
            current |= _CONTINUATION_BIT
        encoded.append(current)
        if not value:
            return bytes(encoded)


def unpack_varint(data: bytes, start: int) -> tuple[int, int]:
    """Decode the varint at ``start`` and return it with the position after it."""
    value = 0
    for offset in range(_MAX_BYTES):
        position = start + offset
        if position >= len(data):
            message = "Failed to parse a fragment header: it ends mid-integer"
            raise TuyaBleProtocolError(message)
        current = data[position]
        value |= (current & _VALUE_MASK) << (offset * _BITS_PER_BYTE)
        if not current & _CONTINUATION_BIT:
            return value, position + 1
    message = "Failed to parse a fragment header: the integer never terminates"
    raise TuyaBleProtocolError(message)
