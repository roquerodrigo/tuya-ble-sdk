"""Answer the two clock requests a Tuya BLE device may raise mid-session."""

from __future__ import annotations

import time
from struct import pack

_MILLISECONDS_PER_SECOND = 1000
_NANOSECONDS_PER_MILLISECOND = 1_000_000
_SECONDS_PER_TIMEZONE_UNIT = 36
_CENTURY = 100


def _timezone_offset() -> int:
    """Return the local offset in hundredths of an hour, positive east of UTC."""
    return -int(time.timezone / _SECONDS_PER_TIMEZONE_UNIT)


def build_unix_time_reply() -> bytes:
    """Answer with the epoch in ASCII milliseconds plus the timezone offset."""
    milliseconds = time.time_ns() // _NANOSECONDS_PER_MILLISECOND
    return str(milliseconds).encode() + pack(">h", _timezone_offset())


def build_local_time_reply() -> bytes:
    """Answer with the broken-down local time the device asks for by field."""
    local = time.localtime()
    return pack(
        ">BBBBBBBh",
        local.tm_year % _CENTURY,
        local.tm_mon,
        local.tm_mday,
        local.tm_hour,
        local.tm_min,
        local.tm_sec,
        local.tm_wday,
        _timezone_offset(),
    )
