"""One datapoint value reported by a Tuya BLE device."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..protocol import DataPointType

type DataPointValue = bytes | bool | int | str


@dataclass(frozen=True, slots=True)
class DataPoint:
    """
    A datapoint as it arrived from the device.

    ``timestamp`` is the moment the device attributed to the reading when it
    sent one, and the moment of reception otherwise; both are Unix seconds.
    """

    identifier: int
    data_type: DataPointType
    value: DataPointValue
    timestamp: float
