"""Join the 20-byte notifications a Tuya BLE device splits its frames into."""

from __future__ import annotations

from ..exceptions import TuyaBleProtocolError
from .varint import unpack_varint

_PROTOCOL_VERSION_LENGTH = 1


class PacketReassembler:
    """
    Buffers notification fragments until one whole encrypted payload is there.

    The first fragment declares the total length, so the end is computed rather
    than searched for: the payload is ciphertext and any delimiter would occur
    inside it eventually.
    """

    __slots__ = ("_buffer", "_expected_length", "_next_index")

    def __init__(self) -> None:
        """Start with nothing buffered."""
        self._buffer = bytearray()
        self._expected_length = 0
        self._next_index = 0

    def feed(self, chunk: bytes) -> bytes | None:
        """
        Add one notification and return the payload once it is complete.

        Raises when a fragment arrives out of order, which means one was lost:
        the buffer is dropped first, so the next frame starts clean.
        """
        index, position = unpack_varint(chunk, 0)
        if index == 0:
            self._start(chunk, position)
            position = self._payload_start(chunk, position)
        elif index != self._next_index:
            expected = self._next_index
            self._reset()
            message = (
                f"Failed to reassemble a frame: fragment {index} arrived where "
                f"{expected} was expected"
            )
            raise TuyaBleProtocolError(message)
        self._buffer += chunk[position:]
        self._next_index += 1
        if len(self._buffer) > self._expected_length:
            received = len(self._buffer)
            expected_length = self._expected_length
            self._reset()
            message = (
                f"Failed to reassemble a frame: {received} bytes arrived for a "
                f"declared length of {expected_length}"
            )
            raise TuyaBleProtocolError(message)
        if len(self._buffer) < self._expected_length:
            return None
        payload = bytes(self._buffer)
        self._reset()
        return payload

    def _start(self, chunk: bytes, position: int) -> None:
        """Begin a new frame, reading the length the first fragment declares."""
        self._buffer = bytearray()
        self._next_index = 0
        self._expected_length, _ = unpack_varint(chunk, position)

    def _payload_start(self, chunk: bytes, position: int) -> int:
        """Skip the declared length and the protocol version byte after it."""
        _, position = unpack_varint(chunk, position)
        if position + _PROTOCOL_VERSION_LENGTH > len(chunk):
            self._reset()
            message = "Failed to reassemble a frame: the first fragment is truncated"
            raise TuyaBleProtocolError(message)
        return position + _PROTOCOL_VERSION_LENGTH

    def _reset(self) -> None:
        """Drop whatever was buffered."""
        self._buffer = bytearray()
        self._expected_length = 0
        self._next_index = 0
