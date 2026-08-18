"""Parse the reply to the device-information request."""

from __future__ import annotations

from ..exceptions import TuyaBleProtocolError
from ..models import DeviceInfo
from ..protocol import DEVICE_INFO_RESPONSE_LENGTH


def parse_device_info(data: bytes) -> DeviceInfo:
    """Read the fixed-layout record the device answers the handshake with."""
    if len(data) < DEVICE_INFO_RESPONSE_LENGTH:
        message = (
            f"Failed to read the device information: {len(data)} bytes arrived, "
            f"{DEVICE_INFO_RESPONSE_LENGTH} expected"
        )
        raise TuyaBleProtocolError(message)
    return DeviceInfo(
        device_version=f"{data[0]}.{data[1]}",
        protocol_version=data[2],
        protocol_version_name=f"{data[2]}.{data[3]}",
        hardware_version=f"{data[12]}.{data[13]}",
        flags=data[4],
        is_bound=data[5] != 0,
        srand=data[6:12],
        auth_key=data[14:DEVICE_INFO_RESPONSE_LENGTH],
    )
