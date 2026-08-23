"""
Public surface of the SDK.

Everything a consumer is meant to import is re-exported here, so the module
layout stays free to change without breaking the integration that depends on
it.
"""

from __future__ import annotations

from .advertisement import parse_advertisement
from .client import TuyaBleClient
from .cloud import DEFAULT_REGION, REGIONS, TuyaBleCloudClient
from .exceptions import (
    TuyaBleAuthenticationError,
    TuyaBleCloudError,
    TuyaBleConnectionError,
    TuyaBleError,
    TuyaBleHandshakeTimeoutError,
    TuyaBleProtocolError,
)
from .models import (
    AccountSession,
    AdvertisementInfo,
    CloudDevice,
    DataPoint,
    DataPointValue,
    DeviceInfo,
    TuyaBleCredentials,
)
from .protocol import SERVICE_UUID, DataPointType, TuyaBleCommandCode

__all__ = [
    "DEFAULT_REGION",
    "REGIONS",
    "SERVICE_UUID",
    "AccountSession",
    "AdvertisementInfo",
    "CloudDevice",
    "DataPoint",
    "DataPointType",
    "DataPointValue",
    "DeviceInfo",
    "TuyaBleAuthenticationError",
    "TuyaBleClient",
    "TuyaBleCloudClient",
    "TuyaBleCloudError",
    "TuyaBleCommandCode",
    "TuyaBleConnectionError",
    "TuyaBleCredentials",
    "TuyaBleError",
    "TuyaBleHandshakeTimeoutError",
    "TuyaBleProtocolError",
    "parse_advertisement",
]
