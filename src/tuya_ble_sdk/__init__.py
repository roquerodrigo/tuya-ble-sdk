"""
Public surface of the SDK.

Everything a consumer is meant to import is re-exported here, so the module
layout stays free to change without breaking the integration that depends on
it.
"""

from __future__ import annotations

from .advertisement import parse_advertisement
from .client import TuyaBleClient
from .exceptions import (
    TuyaBleAuthenticationError,
    TuyaBleConnectionError,
    TuyaBleError,
    TuyaBleProtocolError,
)
from .models import (
    AdvertisementInfo,
    DataPoint,
    DataPointValue,
    DeviceInfo,
    TuyaBleCredentials,
)
from .protocol import SERVICE_UUID, DataPointType, TuyaBleCommandCode

__all__ = [
    "SERVICE_UUID",
    "AdvertisementInfo",
    "DataPoint",
    "DataPointType",
    "DataPointValue",
    "DeviceInfo",
    "TuyaBleAuthenticationError",
    "TuyaBleClient",
    "TuyaBleCommandCode",
    "TuyaBleConnectionError",
    "TuyaBleCredentials",
    "TuyaBleError",
    "TuyaBleProtocolError",
    "parse_advertisement",
]
