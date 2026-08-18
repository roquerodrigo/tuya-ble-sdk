"""One session with one Tuya BLE device: connect, handshake, read, disconnect."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .commands import (
    build_local_time_reply,
    build_pairing_request,
    build_unix_time_reply,
    parse_data_points,
    parse_device_info,
    parse_timestamp,
    verify_pairing_result,
)
from .crypto import login_key, session_key
from .exceptions import TuyaBleConnectionError, TuyaBleError, TuyaBleProtocolError
from .protocol import (
    DEFAULT_PROTOCOL_VERSION,
    NOTIFY_CHARACTERISTIC_UUID,
    SECURITY_FLAG_AUTHENTICATION_KEY,
    SECURITY_FLAG_LOGIN_KEY,
    SECURITY_FLAG_SESSION_KEY,
    WRITE_CHARACTERISTIC_UUID,
    Frame,
    PacketReassembler,
    TuyaBleCommandCode,
    build_packets,
    security_flag_of,
)

if TYPE_CHECKING:
    from bleak.backends.characteristic import BleakGATTCharacteristic
    from bleak.backends.device import BLEDevice

    from .models import DataPoint, DeviceInfo, TuyaBleCredentials

LOGGER = logging.getLogger(__name__)

CONNECT_ATTEMPTS = 3
RESPONSE_TIMEOUT = 20.0
FIRST_REPORT_TIMEOUT = 15.0
REPORT_QUIET_PERIOD = 1.5


class TuyaBleClient:
    """
    Reads the datapoints of one Tuya BLE device and lets go of the radio.

    The device is battery powered and only listens for a moment after it
    advertises, so the client holds no permanent connection: every read
    connects, performs the handshake, collects one report and disconnects.
    Discovery belongs to the caller, which is why an already-resolved
    ``BLEDevice`` is required rather than an address.
    """

    def __init__(self, device: BLEDevice, credentials: TuyaBleCredentials) -> None:
        """Configure the session; no radio work happens until a read is asked for."""
        self._device = device
        self._credentials = credentials
        self._login_key = login_key(credentials.local_key)
        self._session_key: bytes | None = None
        self._authentication_key: bytes | None = None
        self._protocol_version = DEFAULT_PROTOCOL_VERSION
        self._client: BleakClientWithServiceCache | None = None
        self._reassembler = PacketReassembler()
        self._pending: dict[int, asyncio.Future[Frame]] = {}
        self._reports: asyncio.Queue[list[DataPoint]] = asyncio.Queue()
        self._sequence_number = 1
        self._background: set[asyncio.Task[None]] = set()

    @property
    def address(self) -> str:
        """The Bluetooth address of the device this client talks to."""
        return self._device.address

    async def async_read_data_points(self) -> dict[int, DataPoint]:
        """
        Run a whole session and return the datapoints the device reported.

        The device answers the status request with an acknowledgement and then
        pushes its datapoints as separate notifications, so the report is
        considered complete once it goes quiet.
        """
        await self._async_connect()
        try:
            await self._async_handshake()
            return await self._async_collect_report()
        finally:
            await self._async_disconnect()

    async def _async_connect(self) -> None:
        """Open the GATT link and subscribe to the notify characteristic."""
        try:
            self._client = await establish_connection(
                BleakClientWithServiceCache,
                self._device,
                self._device.name or self._device.address,
                use_services_cache=True,
                max_attempts=CONNECT_ATTEMPTS,
            )
            await self._client.start_notify(
                NOTIFY_CHARACTERISTIC_UUID, self._on_notification
            )
        except TuyaBleError:
            raise
        except Exception as exception:
            message = f"Failed to connect to {self.address}: {exception}"
            raise TuyaBleConnectionError(message) from exception

    async def _async_disconnect(self) -> None:
        """Tear the link down, whatever state the session ended in."""
        for task in tuple(self._background):
            task.cancel()
        self._background.clear()
        for pending in self._pending.values():
            pending.cancel()
        self._pending.clear()
        client = self._client
        self._client = None
        self._session_key = None
        self._sequence_number = 1
        if client is None:
            return
        try:
            await client.disconnect()
        except Exception:  # teardown must not mask the session's own failure
            LOGGER.debug("%s: disconnect failed; ignoring", self.address, exc_info=True)

    async def _async_handshake(self) -> None:
        """Derive the session key and pair, in the order the protocol requires."""
        reply = await self._async_request(
            TuyaBleCommandCode.SENDER_DEVICE_INFO,
            b"",
            key=self._login_key,
            security_flag=SECURITY_FLAG_LOGIN_KEY,
        )
        self._adopt_device_info(parse_device_info(reply.data))
        paired = await self._async_request(
            TuyaBleCommandCode.SENDER_PAIR,
            build_pairing_request(self._credentials),
        )
        verify_pairing_result(paired.data)

    def _adopt_device_info(self, device_info: DeviceInfo) -> None:
        """Take the session parameters the device just disclosed."""
        self._protocol_version = device_info.protocol_version
        self._authentication_key = device_info.auth_key
        self._session_key = session_key(self._credentials.local_key, device_info.srand)
        LOGGER.debug(
            "%s: protocol %s, firmware %s, bound %s",
            self.address,
            device_info.protocol_version_name,
            device_info.device_version,
            device_info.is_bound,
        )

    async def _async_collect_report(self) -> dict[int, DataPoint]:
        """Ask for a full status report and drain the notifications it triggers."""
        await self._async_request(TuyaBleCommandCode.SENDER_DEVICE_STATUS, b"")
        collected: dict[int, DataPoint] = {}
        timeout = FIRST_REPORT_TIMEOUT
        while True:
            try:
                report = await asyncio.wait_for(self._reports.get(), timeout)
            except TimeoutError:
                break
            for data_point in report:
                collected[data_point.identifier] = data_point
            timeout = REPORT_QUIET_PERIOD
        if not collected:
            message = f"Failed to read {self.address}: it reported no datapoint"
            raise TuyaBleProtocolError(message)
        return collected

    async def _async_request(
        self,
        code: TuyaBleCommandCode,
        data: bytes,
        *,
        key: bytes | None = None,
        security_flag: int = SECURITY_FLAG_SESSION_KEY,
    ) -> Frame:
        """Send one frame and wait for the reply that quotes its sequence number."""
        sequence_number = self._next_sequence_number()
        pending: asyncio.Future[Frame] = asyncio.get_running_loop().create_future()
        self._pending[sequence_number] = pending
        try:
            await self._async_send(
                Frame(
                    sequence_number=sequence_number,
                    response_to=0,
                    code=code,
                    data=data,
                ),
                key=key or self._require_session_key(),
                security_flag=security_flag,
            )
            reply = await asyncio.wait_for(pending, RESPONSE_TIMEOUT)
        except TimeoutError as exception:
            message = f"Failed to read {self.address}: {code.name} was not answered"
            raise TuyaBleConnectionError(message) from exception
        finally:
            self._pending.pop(sequence_number, None)
        return reply

    async def _async_send(
        self, frame: Frame, *, key: bytes, security_flag: int
    ) -> None:
        """Encrypt one frame and write every fragment of it."""
        client = self._client
        if client is None:
            message = f"Failed to write to {self.address}: the link is closed"
            raise TuyaBleConnectionError(message)
        payload = frame.encode(key, security_flag)
        try:
            for packet in build_packets(payload, self._protocol_version):
                await client.write_gatt_char(
                    WRITE_CHARACTERISTIC_UUID, packet, response=False
                )
        except BleakError as exception:
            message = f"Failed to write to {self.address}: {exception}"
            raise TuyaBleConnectionError(message) from exception

    def _next_sequence_number(self) -> int:
        """Hand out the next sequence number; replies quote it back."""
        sequence_number = self._sequence_number
        self._sequence_number += 1
        return sequence_number

    def _require_session_key(self) -> bytes:
        """Return the session key, refusing to send before the handshake ran."""
        if self._session_key is None:
            message = f"Failed to talk to {self.address}: the handshake has not run"
            raise TuyaBleError(message)
        return self._session_key

    def _key_for(self, security_flag: int) -> bytes | None:
        """Pick the key a received payload announces it was encrypted with."""
        if security_flag == SECURITY_FLAG_AUTHENTICATION_KEY:
            return self._authentication_key
        if security_flag == SECURITY_FLAG_LOGIN_KEY:
            return self._login_key
        if security_flag == SECURITY_FLAG_SESSION_KEY:
            return self._session_key
        return None

    def _on_notification(
        self, _characteristic: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        """Reassemble, decrypt and dispatch one notification."""
        try:
            payload = self._reassembler.feed(bytes(data))
            if payload is None:
                return
            key = self._key_for(security_flag_of(payload))
            if key is None:
                LOGGER.debug("%s: dropping a frame with no usable key", self.address)
                return
            self._dispatch(Frame.decode(payload, key))
        except TuyaBleError:
            LOGGER.debug(
                "%s: dropping an unreadable frame", self.address, exc_info=True
            )

    def _dispatch(self, frame: Frame) -> None:
        """Route a decoded frame to whoever is waiting for it, or handle it here."""
        pending = self._pending.pop(frame.response_to, None)
        if pending is not None and not pending.done():
            pending.set_result(frame)
            return
        code = TuyaBleCommandCode.from_value(frame.code)
        if code is None:
            LOGGER.debug("%s: ignoring command %#06x", self.address, frame.code)
            return
        self._handle_device_command(code, frame)

    def _handle_device_command(self, code: TuyaBleCommandCode, frame: Frame) -> None:
        """Act on the frames the device sends on its own initiative."""
        match code:
            case TuyaBleCommandCode.RECEIVE_DATA_POINT:
                self._publish(parse_data_points(frame.data, 0, time.time()))
                self._reply(frame, b"")
            case TuyaBleCommandCode.RECEIVE_TIME_DATA_POINT:
                timestamp, position = parse_timestamp(frame.data, 0)
                self._publish(parse_data_points(frame.data, position, timestamp))
                self._reply(frame, b"")
            case TuyaBleCommandCode.RECEIVE_UNIX_TIME_REQUEST:
                self._reply(frame, build_unix_time_reply())
            case TuyaBleCommandCode.RECEIVE_LOCAL_TIME_REQUEST:
                self._reply(frame, build_local_time_reply())
            case _:
                LOGGER.debug("%s: ignoring %s", self.address, code.name)

    def _publish(self, data_points: list[DataPoint]) -> None:
        """Hand a parsed report to the read that is waiting for one."""
        if data_points:
            self._reports.put_nowait(data_points)

    def _reply(self, frame: Frame, data: bytes) -> None:
        """
        Answer a device-initiated frame without blocking the notification callback.

        Bleak calls the handler from the event loop, so the write is scheduled
        rather than awaited; the task is tracked so teardown can cancel it.
        """
        response = Frame(
            sequence_number=self._next_sequence_number(),
            response_to=frame.sequence_number,
            code=frame.code,
            data=data,
        )
        task = asyncio.create_task(self._async_reply(response))
        self._background.add(task)
        task.add_done_callback(self._background.discard)

    async def _async_reply(self, frame: Frame) -> None:
        """Write one reply, treating a failure as a lost frame rather than an error."""
        try:
            await self._async_send(
                frame,
                key=self._require_session_key(),
                security_flag=SECURITY_FLAG_SESSION_KEY,
            )
        except TuyaBleError:
            LOGGER.debug("%s: reply could not be sent", self.address, exc_info=True)
