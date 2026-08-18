"""Read the datapoint records a Tuya BLE device pushes as notifications."""

from __future__ import annotations

from ..exceptions import TuyaBleProtocolError
from ..models import DataPoint, DataPointValue
from ..protocol import DataPointType

_RECORD_HEADER_LENGTH = 3
_MILLISECOND_TIMESTAMP = 0
_SECOND_TIMESTAMP = 1
_MILLISECOND_TIMESTAMP_LENGTH = 13
_SECOND_TIMESTAMP_LENGTH = 4
_MILLISECONDS_PER_SECOND = 1000


def parse_timestamp(data: bytes, start: int) -> tuple[float, int]:
    """
    Read the timestamp prefixing a timed datapoint report.

    Returns the moment in Unix seconds together with the position the datapoint
    records begin at.
    """
    if start >= len(data):
        message = "Failed to read a datapoint timestamp: the report is truncated"
        raise TuyaBleProtocolError(message)
    encoding = data[start]
    position = start + 1
    if encoding == _MILLISECOND_TIMESTAMP:
        end = position + _MILLISECOND_TIMESTAMP_LENGTH
        _verify_length_or_raise(data, end)
        return _decode_millisecond_timestamp(data[position:end]), end
    if encoding == _SECOND_TIMESTAMP:
        end = position + _SECOND_TIMESTAMP_LENGTH
        _verify_length_or_raise(data, end)
        return float(int.from_bytes(data[position:end], "big")), end
    message = f"Failed to read a datapoint timestamp: unknown encoding {encoding}"
    raise TuyaBleProtocolError(message)


def parse_data_points(data: bytes, start: int, timestamp: float) -> list[DataPoint]:
    """Read every ``identifier | type | length | value`` record from ``start``."""
    data_points: list[DataPoint] = []
    position = start
    while len(data) - position > _RECORD_HEADER_LENGTH:
        identifier = data[position]
        data_type = _data_point_type(data[position + 1])
        length = data[position + 2]
        end = position + _RECORD_HEADER_LENGTH + length
        _verify_length_or_raise(data, end)
        raw_value = data[position + _RECORD_HEADER_LENGTH : end]
        data_points.append(
            DataPoint(
                identifier=identifier,
                data_type=data_type,
                value=_decode_value(data_type, raw_value),
                timestamp=timestamp,
            )
        )
        position = end
    return data_points


def _data_point_type(value: int) -> DataPointType:
    """Turn the type byte into its member, refusing anything undefined."""
    try:
        return DataPointType(value)
    except ValueError as exception:
        message = f"Failed to read a datapoint: unknown value type {value}"
        raise TuyaBleProtocolError(message) from exception


def _decode_value(data_type: DataPointType, raw_value: bytes) -> DataPointValue:
    """Interpret the value bytes according to the declared type."""
    match data_type:
        case DataPointType.RAW | DataPointType.BITMAP:
            return raw_value
        case DataPointType.BOOLEAN:
            return int.from_bytes(raw_value, "big") != 0
        case DataPointType.VALUE | DataPointType.ENUM:
            return int.from_bytes(raw_value, "big", signed=True)
        case DataPointType.STRING:
            return _decode_string(raw_value)


def _decode_string(raw_value: bytes) -> str:
    """Decode a string datapoint, reporting undecodable bytes as a protocol error."""
    try:
        return raw_value.decode()
    except UnicodeDecodeError as exception:
        message = f"Failed to read a string datapoint: {exception}"
        raise TuyaBleProtocolError(message) from exception


def _decode_millisecond_timestamp(raw_value: bytes) -> float:
    """Decode the ASCII millisecond timestamp the protocol also allows."""
    try:
        return int(raw_value.decode()) / _MILLISECONDS_PER_SECOND
    except (UnicodeDecodeError, ValueError) as exception:
        message = f"Failed to read a datapoint timestamp: {exception}"
        raise TuyaBleProtocolError(message) from exception


def _verify_length_or_raise(data: bytes, end: int) -> None:
    """Refuse a record that declares more bytes than the report carries."""
    if end > len(data):
        message = (
            f"Failed to read a datapoint report: it declares {end} bytes but only "
            f"{len(data)} arrived"
        )
        raise TuyaBleProtocolError(message)
