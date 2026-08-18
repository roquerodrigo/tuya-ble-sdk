"""The Tuya BLE wire protocol: constants, frames and fragmentation."""

from __future__ import annotations

from .command_code import TuyaBleCommandCode
from .constants import (
    CRC_LENGTH,
    DEFAULT_PROTOCOL_VERSION,
    DEVICE_INFO_RESPONSE_LENGTH,
    FRAME_HEADER_LENGTH,
    GATT_MTU,
    MANUFACTURER_DATA_IDENTIFIER,
    NOTIFY_CHARACTERISTIC_UUID,
    PAIRING_REQUEST_LENGTH,
    SECURITY_FLAG_AUTHENTICATION_KEY,
    SECURITY_FLAG_LOGIN_KEY,
    SECURITY_FLAG_SESSION_KEY,
    SERVICE_UUID,
    SUPPORTED_PROTOCOL_VERSION,
    WRITE_CHARACTERISTIC_UUID,
)
from .data_point_type import DataPointType
from .frame import Frame, build_packets, security_flag_of
from .reassembler import PacketReassembler
from .varint import pack_varint, unpack_varint

__all__ = [
    "CRC_LENGTH",
    "DEFAULT_PROTOCOL_VERSION",
    "DEVICE_INFO_RESPONSE_LENGTH",
    "FRAME_HEADER_LENGTH",
    "GATT_MTU",
    "MANUFACTURER_DATA_IDENTIFIER",
    "NOTIFY_CHARACTERISTIC_UUID",
    "PAIRING_REQUEST_LENGTH",
    "SECURITY_FLAG_AUTHENTICATION_KEY",
    "SECURITY_FLAG_LOGIN_KEY",
    "SECURITY_FLAG_SESSION_KEY",
    "SERVICE_UUID",
    "SUPPORTED_PROTOCOL_VERSION",
    "WRITE_CHARACTERISTIC_UUID",
    "DataPointType",
    "Frame",
    "PacketReassembler",
    "TuyaBleCommandCode",
    "build_packets",
    "pack_varint",
    "security_flag_of",
    "unpack_varint",
]
