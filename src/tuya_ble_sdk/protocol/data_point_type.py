"""How the value bytes of a datapoint are to be read."""

from __future__ import annotations

from enum import IntEnum


class DataPointType(IntEnum):
    """The six datapoint encodings the Tuya protocol defines."""

    RAW = 0
    BOOLEAN = 1
    VALUE = 2
    STRING = 3
    ENUM = 4
    BITMAP = 5
