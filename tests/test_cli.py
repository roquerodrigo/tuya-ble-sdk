from __future__ import annotations

from hashlib import md5

import pytest
from typer.testing import CliRunner

from tuya_ble_sdk import cli as cli_module
from tuya_ble_sdk.cli import app
from tuya_ble_sdk.crypto import encrypt
from tuya_ble_sdk.protocol import MANUFACTURER_DATA_IDENTIFIER, SERVICE_UUID

from .fake_device import DEVICE_ID, LOCAL_KEY, UUID

ADDRESS = "AA:BB:CC:DD:EE:FF"
PRODUCT_ID = "gvygg3m8"
runner = CliRunner()


class FakeBleDevice:
    address = ADDRESS
    name = "TY"


class FakeAdvertisement:
    def __init__(self, *, with_service_data: bool = True) -> None:
        key = md5(PRODUCT_ID.encode()).digest()
        self.service_uuids = [SERVICE_UUID]
        self.service_data = (
            {SERVICE_UUID: b"\x00" + PRODUCT_ID.encode()} if with_service_data else {}
        )
        self.manufacturer_data = {
            MANUFACTURER_DATA_IDENTIFIER: bytes([0x80, 3, 0, 0, 1, 0])
            + encrypt(key, key, UUID.encode())
        }


@pytest.fixture
def discovered(monkeypatch):
    """Stand in for the scanner, both as a sweep and as a live callback."""
    found: dict[str, tuple[FakeBleDevice, FakeAdvertisement]] = {
        ADDRESS: (FakeBleDevice(), FakeAdvertisement())
    }

    class FakeScanner:
        def __init__(self, detection_callback=None):
            self._detected = detection_callback

        async def start(self):
            for device, advertisement in list(found.values()):
                self._detected(device, advertisement)

        async def stop(self):
            return None

        @staticmethod
        async def discover(**_kwargs):
            return found

    monkeypatch.setattr(cli_module, "BleakScanner", FakeScanner)
    return found


def test_scan_lists_the_devices_it_found(discovered):
    result = runner.invoke(app, ["scan", "--seconds", "0.1"])

    assert result.exit_code == 0
    assert ADDRESS in result.output
    assert PRODUCT_ID in result.output
    assert UUID in result.output


def test_scan_ignores_devices_that_are_not_tuya(discovered):
    advertisement = FakeAdvertisement()
    advertisement.service_uuids = []
    advertisement.service_data = {}
    discovered["11:22:33:44:55:66"] = (FakeBleDevice(), advertisement)

    result = runner.invoke(app, ["scan", "--seconds", "0.1"])

    assert result.output.count("product_id=") == 1


def test_scan_reports_when_nothing_answered(discovered):
    discovered.clear()

    result = runner.invoke(app, ["scan", "--seconds", "0.1"])

    assert result.exit_code == 1
    assert "no Tuya BLE device" in result.output


def test_read_prints_every_datapoint(monkeypatch, discovered):
    monkeypatch.setattr(
        cli_module.TuyaBleClient,
        "async_read_data_points",
        _fake_read,
    )

    result = runner.invoke(
        app,
        [
            "read",
            "--address",
            ADDRESS.lower(),
            "--device-id",
            DEVICE_ID,
            "--local-key",
            LOCAL_KEY,
            "--seconds",
            "0.1",
            "-v",
        ],
    )

    assert result.exit_code == 0
    assert "dp   3" in result.output
    assert "VALUE" in result.output


def test_read_refuses_an_address_that_never_advertised(discovered):
    discovered.clear()

    result = runner.invoke(
        app,
        [
            "read",
            "--address",
            ADDRESS,
            "--device-id",
            DEVICE_ID,
            "--local-key",
            LOCAL_KEY,
            "--seconds",
            "0.1",
        ],
    )

    assert result.exit_code != 0


def test_read_refuses_a_device_that_advertises_no_uuid(discovered):
    discovered[ADDRESS] = (FakeBleDevice(), FakeAdvertisement(with_service_data=False))

    result = runner.invoke(
        app,
        [
            "read",
            "--address",
            ADDRESS,
            "--device-id",
            DEVICE_ID,
            "--local-key",
            LOCAL_KEY,
        ],
    )

    assert result.exit_code != 0


def test_read_accepts_a_uuid_given_on_the_command_line(monkeypatch, discovered):
    discovered[ADDRESS] = (FakeBleDevice(), FakeAdvertisement(with_service_data=False))
    monkeypatch.setattr(
        cli_module.TuyaBleClient,
        "async_read_data_points",
        _fake_read,
    )

    result = runner.invoke(
        app,
        [
            "read",
            "--address",
            ADDRESS,
            "--device-id",
            DEVICE_ID,
            "--local-key",
            LOCAL_KEY,
            "--uuid",
            UUID,
        ],
    )

    assert result.exit_code == 0


async def _fake_read(_self):
    from tuya_ble_sdk.models import DataPoint
    from tuya_ble_sdk.protocol import DataPointType

    return {
        3: DataPoint(
            identifier=3, data_type=DataPointType.VALUE, value=42, timestamp=1.0
        )
    }


def test_read_connects_on_the_first_sighting_not_after_the_window(
    monkeypatch, discovered
):
    """
    The read must not sweep the whole window before connecting.

    A battery-powered device stops listening while a full scan runs, so the
    sweep is a silent regression rather than a slow path — this test fails if
    `read` ever goes back to it.
    """

    async def _refuse(**_kwargs):
        message = "read must not sweep the whole window"
        raise AssertionError(message)

    monkeypatch.setattr(cli_module.BleakScanner, "discover", staticmethod(_refuse))
    monkeypatch.setattr(cli_module.TuyaBleClient, "async_read_data_points", _fake_read)

    result = runner.invoke(
        app,
        [
            "read",
            "--address",
            ADDRESS,
            "--device-id",
            DEVICE_ID,
            "--local-key",
            LOCAL_KEY,
            "--seconds",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert "dp   3" in result.output
