from __future__ import annotations

import time

import pytest

from tuya_ble_sdk.commands import (
    build_local_time_reply,
    build_pairing_request,
    build_unix_time_reply,
    parse_data_points,
    parse_device_info,
    parse_timestamp,
    verify_pairing_result,
)
from tuya_ble_sdk.exceptions import TuyaBleAuthenticationError, TuyaBleProtocolError
from tuya_ble_sdk.models import TuyaBleCredentials
from tuya_ble_sdk.protocol import DataPointType

from .fake_device import DEVICE_ID, LOCAL_KEY, UUID, build_device_info


def test_device_info_is_read_field_by_field():
    info = parse_device_info(build_device_info())
    assert info.device_version == "1.2"
    assert info.protocol_version == 3
    assert info.protocol_version_name == "3.0"
    assert info.hardware_version == "9.3"
    assert info.is_bound is True
    assert info.srand == b"srand!"
    assert len(info.auth_key) == 32


def test_device_info_rejects_a_short_record():
    with pytest.raises(TuyaBleProtocolError, match="bytes arrived"):
        parse_device_info(bytes(10))


def test_pairing_request_is_padded_to_the_fixed_width():
    request = build_pairing_request(
        TuyaBleCredentials(uuid=UUID, device_id=DEVICE_ID, local_key=LOCAL_KEY)
    )
    assert len(request) == 44
    assert request.startswith(UUID.encode() + b"abcdef" + DEVICE_ID.encode())
    assert request.endswith(b"\x00" * 4)


def test_pairing_request_refuses_credentials_that_do_not_fit():
    with pytest.raises(TuyaBleProtocolError, match="maximum"):
        build_pairing_request(
            TuyaBleCredentials(uuid="u" * 40, device_id="d" * 40, local_key=LOCAL_KEY)
        )


@pytest.mark.parametrize("result", [b"\x00", b"\x02"])
def test_pairing_accepts_both_success_codes(result):
    verify_pairing_result(result)


def test_pairing_rejection_is_an_authentication_error():
    with pytest.raises(TuyaBleAuthenticationError, match="code 1"):
        verify_pairing_result(b"\x01")


def test_pairing_result_must_be_one_byte():
    with pytest.raises(TuyaBleProtocolError, match="1 expected"):
        verify_pairing_result(b"")


def test_data_points_are_read_by_declared_type():
    data = (
        bytes([3, 2, 4])
        + (42).to_bytes(4, "big")
        + bytes([9, 4, 1, 1])
        + bytes([1, 1, 1, 1])
        + bytes([2, 3, 2])
        + b"ok"
        + bytes([4, 0, 2])
        + b"\xde\xad"
        + bytes([5, 5, 1, 3])
    )
    points = {point.identifier: point for point in parse_data_points(data, 0, 1.0)}
    assert points[3].value == 42
    assert points[3].data_type is DataPointType.VALUE
    assert points[9].value == 1
    assert points[1].value is True
    assert points[2].value == "ok"
    assert points[4].value == b"\xde\xad"
    assert points[5].value == b"\x03"


def test_negative_values_are_signed():
    data = bytes([5, 2, 4]) + (-120).to_bytes(4, "big", signed=True)
    assert parse_data_points(data, 0, 1.0)[0].value == -120


def test_data_points_reject_an_unknown_type():
    with pytest.raises(TuyaBleProtocolError, match="unknown value type"):
        parse_data_points(bytes([3, 9, 1, 0]), 0, 1.0)


def test_data_points_reject_a_truncated_record():
    with pytest.raises(TuyaBleProtocolError, match="declares"):
        parse_data_points(bytes([3, 2, 8]) + bytes(2), 0, 1.0)


def test_data_points_reject_undecodable_strings():
    with pytest.raises(TuyaBleProtocolError, match="string datapoint"):
        parse_data_points(bytes([2, 3, 1, 0xFF]), 0, 1.0)


def test_millisecond_timestamps_are_read_as_seconds():
    timestamp, position = parse_timestamp(b"\x00" + b"1700000000000", 0)
    assert timestamp == 1700000000.0
    assert position == 14


def test_second_timestamps_are_read_as_they_are():
    timestamp, position = parse_timestamp(b"\x01" + (1700000000).to_bytes(4, "big"), 0)
    assert timestamp == 1700000000.0
    assert position == 5


def test_timestamp_rejects_an_unknown_encoding():
    with pytest.raises(TuyaBleProtocolError, match="unknown encoding"):
        parse_timestamp(b"\x09", 0)


def test_timestamp_rejects_an_empty_report():
    with pytest.raises(TuyaBleProtocolError, match="truncated"):
        parse_timestamp(b"", 0)


def test_timestamp_rejects_a_truncated_value():
    with pytest.raises(TuyaBleProtocolError, match="declares"):
        parse_timestamp(b"\x01\x00", 0)


def test_timestamp_rejects_non_numeric_milliseconds():
    with pytest.raises(TuyaBleProtocolError, match="timestamp"):
        parse_timestamp(b"\x00" + b"not-a-number!", 0)


def test_unix_time_reply_carries_milliseconds_and_the_offset():
    reply = build_unix_time_reply()
    assert len(reply) > 2
    assert int(reply[:-2].decode()) / 1000 == pytest.approx(time.time(), abs=5)


def test_local_time_reply_is_the_broken_down_clock():
    reply = build_local_time_reply()
    assert len(reply) == 9
    assert reply[1] == time.localtime().tm_mon
