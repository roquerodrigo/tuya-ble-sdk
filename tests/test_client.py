from __future__ import annotations

import asyncio

import pytest
from bleak.exc import BleakError

from tuya_ble_sdk import client as client_module
from tuya_ble_sdk.client import TuyaBleClient
from tuya_ble_sdk.exceptions import (
    TuyaBleAuthenticationError,
    TuyaBleConnectionError,
    TuyaBleError,
    TuyaBleProtocolError,
)
from tuya_ble_sdk.models import TuyaBleCredentials
from tuya_ble_sdk.protocol import DataPointType, Frame, TuyaBleCommandCode

from .fake_device import (
    DEVICE_ID,
    LOCAL_KEY,
    UUID,
    FakeBleakClient,
    build_device_info,
)


class FakeBleDevice:
    address = "AA:BB:CC:DD:EE:FF"
    name = "TY"


@pytest.fixture
def credentials():
    return TuyaBleCredentials(uuid=UUID, device_id=DEVICE_ID, local_key=LOCAL_KEY)


@pytest.fixture
def peripheral():
    return FakeBleakClient()


@pytest.fixture
def connected(monkeypatch, peripheral):
    async def _establish_connection(_class, _device, _name, **_kwargs):
        return peripheral

    monkeypatch.setattr(client_module, "establish_connection", _establish_connection)
    monkeypatch.setattr(client_module, "FIRST_REPORT_TIMEOUT", 1.0)
    monkeypatch.setattr(client_module, "REPORT_QUIET_PERIOD", 0.05)
    monkeypatch.setattr(client_module, "RESPONSE_TIMEOUT", 1.0)
    return peripheral


async def test_a_session_reads_every_datapoint(connected, credentials):
    data_points = await TuyaBleClient(
        FakeBleDevice(), credentials
    ).async_read_data_points()

    assert set(data_points) == {3, 5, 9, 14, 15}
    assert data_points[3].value == 42
    assert data_points[5].value == 260
    assert data_points[9].data_type is DataPointType.ENUM
    assert data_points[15].value == 77
    assert connected.disconnected is True


async def test_the_handshake_runs_in_the_order_the_protocol_requires(
    connected, credentials
):
    await TuyaBleClient(FakeBleDevice(), credentials).async_read_data_points()

    sent = [frame.code for frame in connected.received if frame.response_to == 0]
    assert sent[:3] == [
        TuyaBleCommandCode.SENDER_DEVICE_INFO,
        TuyaBleCommandCode.SENDER_PAIR,
        TuyaBleCommandCode.SENDER_DEVICE_STATUS,
    ]


async def test_reports_are_acknowledged(connected, credentials):
    await TuyaBleClient(FakeBleDevice(), credentials).async_read_data_points()

    assert any(frame.response_to != 0 for frame in connected.received)


async def test_the_address_is_the_device_address(credentials):
    assert TuyaBleClient(FakeBleDevice(), credentials).address == FakeBleDevice.address


async def test_a_rejected_local_key_is_an_authentication_error(connected, credentials):
    connected.pairing_result = b"\x01"

    with pytest.raises(TuyaBleAuthenticationError, match="rejected the credentials"):
        await TuyaBleClient(FakeBleDevice(), credentials).async_read_data_points()
    assert connected.disconnected is True


async def test_a_silent_device_times_out(connected, credentials):
    connected.reports = []
    connected.status_result = b"\x00"

    with pytest.raises(TuyaBleProtocolError, match="reported no datapoint"):
        await TuyaBleClient(FakeBleDevice(), credentials).async_read_data_points()


async def test_an_unanswered_command_is_a_connection_error(
    monkeypatch, connected, credentials
):
    monkeypatch.setattr(connected, "_answer", lambda _frame: None)

    with pytest.raises(TuyaBleConnectionError, match="SENDER_DEVICE_INFO"):
        await TuyaBleClient(FakeBleDevice(), credentials).async_read_data_points()


async def test_a_failed_connection_is_a_connection_error(monkeypatch, credentials):
    async def _refuse(*_args, **_kwargs):
        raise BleakError("out of range")

    monkeypatch.setattr(client_module, "establish_connection", _refuse)

    with pytest.raises(TuyaBleConnectionError, match="Failed to connect"):
        await TuyaBleClient(FakeBleDevice(), credentials).async_read_data_points()


async def test_a_failed_write_is_a_connection_error(
    monkeypatch, connected, credentials
):
    async def _refuse(*_args, **_kwargs):
        raise BleakError("link lost")

    monkeypatch.setattr(connected, "write_gatt_char", _refuse)

    with pytest.raises(TuyaBleConnectionError, match="Failed to write"):
        await TuyaBleClient(FakeBleDevice(), credentials).async_read_data_points()


async def test_a_clock_request_is_answered(connected, credentials):
    connected.time_request = TuyaBleCommandCode.RECEIVE_UNIX_TIME_REQUEST

    await TuyaBleClient(FakeBleDevice(), credentials).async_read_data_points()
    await asyncio.sleep(0.05)

    answered = [
        frame
        for frame in connected.received
        if frame.code == TuyaBleCommandCode.RECEIVE_UNIX_TIME_REQUEST
    ]
    assert answered and answered[0].data


async def test_a_local_clock_request_is_answered(connected, credentials):
    connected.time_request = TuyaBleCommandCode.RECEIVE_LOCAL_TIME_REQUEST

    await TuyaBleClient(FakeBleDevice(), credentials).async_read_data_points()
    await asyncio.sleep(0.05)

    answered = [
        frame
        for frame in connected.received
        if frame.code == TuyaBleCommandCode.RECEIVE_LOCAL_TIME_REQUEST
    ]
    assert answered and len(answered[0].data) == 9


async def test_a_timed_report_keeps_the_timestamp_the_device_sent(
    monkeypatch, connected, credentials
):
    report = b"\x01" + (1700000000).to_bytes(4, "big") + bytes([3, 2, 4]) + bytes(4)
    original = connected._answer

    def _answer(frame):
        original(frame)
        if TuyaBleCommandCode.from_value(frame.code) is (
            TuyaBleCommandCode.SENDER_DEVICE_STATUS
        ):
            connected._send(TuyaBleCommandCode.RECEIVE_TIME_DATA_POINT, report, 0)

    monkeypatch.setattr(connected, "_answer", _answer)

    data_points = await TuyaBleClient(
        FakeBleDevice(), credentials
    ).async_read_data_points()

    assert data_points[3].timestamp == 1700000000.0


async def test_an_unknown_command_is_ignored(monkeypatch, connected, credentials):
    original = connected._answer

    def _answer(frame):
        if TuyaBleCommandCode.from_value(frame.code) is (
            TuyaBleCommandCode.SENDER_DEVICE_STATUS
        ):
            connected._send(0x7FFF, b"junk", 0)
            connected._send(TuyaBleCommandCode.SENDER_UNBIND, b"", 0)
        original(frame)

    monkeypatch.setattr(connected, "_answer", _answer)

    assert await TuyaBleClient(FakeBleDevice(), credentials).async_read_data_points()


async def test_an_unreadable_frame_is_dropped(connected, credentials):
    tuya_client = TuyaBleClient(FakeBleDevice(), credentials)

    tuya_client._on_notification(None, bytearray(b"\x00\x02\x30\xff\xff"))

    assert tuya_client._reports.empty()


async def test_a_frame_with_no_usable_key_is_dropped(connected, credentials):
    tuya_client = TuyaBleClient(FakeBleDevice(), credentials)
    payload = Frame(sequence_number=1, response_to=0, code=0, data=b"").encode(
        bytes(16), 0x09
    )

    for packet in _fragments(payload):
        tuya_client._on_notification(None, bytearray(packet))

    assert tuya_client._reports.empty()


async def test_sending_before_the_handshake_is_refused(connected, credentials):
    tuya_client = TuyaBleClient(FakeBleDevice(), credentials)

    with pytest.raises(TuyaBleError, match="handshake has not run"):
        await tuya_client._async_request(TuyaBleCommandCode.SENDER_DEVICE_STATUS, b"")


async def test_a_short_device_info_record_is_a_protocol_error(connected, credentials):
    connected.device_info = build_device_info()[:20]

    with pytest.raises(TuyaBleProtocolError, match="device information"):
        await TuyaBleClient(FakeBleDevice(), credentials).async_read_data_points()


def _fragments(payload: bytes) -> list[bytes]:
    from tuya_ble_sdk.protocol import build_packets

    return build_packets(payload, 3)
