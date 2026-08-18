"""A fake Tuya BLE peripheral the client tests drive instead of real hardware."""

from __future__ import annotations

import asyncio

from tuya_ble_sdk.crypto import login_key, session_key
from tuya_ble_sdk.protocol import (
    SECURITY_FLAG_LOGIN_KEY,
    SECURITY_FLAG_SESSION_KEY,
    Frame,
    PacketReassembler,
    TuyaBleCommandCode,
    build_packets,
    security_flag_of,
)

LOCAL_KEY = "abcdef0123456789"
DEVICE_ID = "dddddddddddddddd"
UUID = "0123456789abcdef"
SRAND = b"srand!"
AUTH_KEY = bytes(range(32))
PROTOCOL_VERSION = 3


def build_device_info(*, protocol_version: int = PROTOCOL_VERSION) -> bytes:
    """Lay out the fixed 46-byte record the handshake answers with."""
    return bytes([1, 2, protocol_version, 0, 0, 1]) + SRAND + bytes([9, 3]) + AUTH_KEY


def build_data_point_report() -> bytes:
    """A soil-sensor report: moisture, temperature, unit, battery state, battery."""
    return (
        bytes([3, 2, 4])
        + (42).to_bytes(4, "big")
        + bytes([5, 2, 4])
        + (260).to_bytes(4, "big")
        + bytes([9, 4, 1, 0])
        + bytes([14, 4, 1, 1])
        + bytes([15, 2, 4])
        + (77).to_bytes(4, "big")
    )


class FakeBleakClient:
    """Speaks the Tuya BLE protocol back at the client under test."""

    def __init__(self, *, device_info: bytes | None = None) -> None:
        self.device_info = (
            device_info if device_info is not None else build_device_info()
        )
        self.pairing_result = b"\x02"
        self.status_result = b"\x00"
        self.reports: list[bytes] = [build_data_point_report()]
        self.time_request: TuyaBleCommandCode | None = None
        self.received: list[Frame] = []
        self.is_connected = True
        self.disconnected = False
        self._login_key = login_key(LOCAL_KEY)
        self._session_key = session_key(LOCAL_KEY, SRAND)
        self._reassembler = PacketReassembler()
        self._notify: object | None = None
        self._sequence_number = 100

    async def start_notify(self, _characteristic: str, callback: object) -> None:
        """Register the client's notification handler."""
        self._notify = callback

    async def disconnect(self) -> None:
        """Record the teardown."""
        self.disconnected = True
        self.is_connected = False

    async def write_gatt_char(
        self, _characteristic: str, packet: bytes, response: bool = False
    ) -> None:
        """Reassemble what the client wrote and answer it."""
        payload = self._reassembler.feed(bytes(packet))
        if payload is None:
            return
        key = (
            self._login_key
            if security_flag_of(payload) == SECURITY_FLAG_LOGIN_KEY
            else self._session_key
        )
        frame = Frame.decode(payload, key)
        self.received.append(frame)
        if frame.response_to == 0:
            self._answer(frame)

    def _answer(self, frame: Frame) -> None:
        """Produce whatever the real device would send back for this command."""
        code = TuyaBleCommandCode.from_value(frame.code)
        if code is TuyaBleCommandCode.SENDER_DEVICE_INFO:
            self._send(frame.code, self.device_info, frame.sequence_number, login=True)
        elif code is TuyaBleCommandCode.SENDER_PAIR:
            self._send(frame.code, self.pairing_result, frame.sequence_number)
        elif code is TuyaBleCommandCode.SENDER_DEVICE_STATUS:
            self._send(frame.code, self.status_result, frame.sequence_number)
            if self.time_request is not None:
                self._send(self.time_request, b"", 0)
            for report in self.reports:
                self._send(TuyaBleCommandCode.RECEIVE_DATA_POINT, report, 0)

    def _send(
        self, code: int, data: bytes, response_to: int, *, login: bool = False
    ) -> None:
        """Push one frame at the client, fragment by fragment."""
        self._sequence_number += 1
        frame = Frame(
            sequence_number=self._sequence_number,
            response_to=response_to,
            code=code,
            data=data,
        )
        payload = frame.encode(
            self._login_key if login else self._session_key,
            SECURITY_FLAG_LOGIN_KEY if login else SECURITY_FLAG_SESSION_KEY,
        )
        for packet in build_packets(payload, PROTOCOL_VERSION):
            asyncio.get_running_loop().call_soon(self._notify, None, bytearray(packet))
