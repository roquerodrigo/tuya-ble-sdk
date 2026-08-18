"""Typer-powered `tuya-ble` CLI: scan for devices and dump their datapoints."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import typer
from bleak import BleakScanner

from .advertisement import parse_advertisement
from .client import TuyaBleClient
from .models import TuyaBleCredentials
from .protocol import SERVICE_UUID

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice
    from bleak.backends.scanner import AdvertisementData

    from .models import AdvertisementInfo, DataPoint

app = typer.Typer(add_completion=False, help="Tuya BLE device control")

DEFAULT_SCAN_SECONDS = 20.0


@app.command()
def scan(
    seconds: float = typer.Option(DEFAULT_SCAN_SECONDS, help="How long to listen"),
    verbose: bool = typer.Option(False, "-v", help="Protocol debug logs"),
) -> None:
    """List every Tuya BLE device advertising nearby."""
    _configure_logging(verbose=verbose)
    found = asyncio.run(_async_scan(seconds))
    if not found:
        typer.echo("no Tuya BLE device advertised")
        raise typer.Exit(code=1)
    for device, info in found:
        typer.echo(
            f"{device.address}  {device.name or '?'}  "
            f"product_id={info.product_id or '?'}  uuid={info.uuid or '?'}  "
            f"protocol={info.protocol_version or '?'}  bound={info.is_bound}"
        )


@app.command()
def read(
    address: str = typer.Option(..., help="Bluetooth address of the device"),
    device_id: str = typer.Option(..., help="Device id from the Tuya account"),
    local_key: str = typer.Option(..., help="Local key from the Tuya account"),
    uuid: str = typer.Option(
        "", help="Device uuid; read from the advertisement if omitted"
    ),
    seconds: float = typer.Option(DEFAULT_SCAN_SECONDS, help="How long to listen"),
    verbose: bool = typer.Option(False, "-v", help="Protocol debug logs"),
) -> None:
    """Connect to one device and print the datapoints it reports."""
    _configure_logging(verbose=verbose)
    data_points = asyncio.run(
        _async_read(address, device_id, local_key, uuid or None, seconds)
    )
    for identifier in sorted(data_points):
        data_point = data_points[identifier]
        typer.echo(
            f"dp {identifier:>3}  {data_point.data_type.name:<7}  {data_point.value!r}"
        )


def _configure_logging(*, verbose: bool) -> None:
    """
    Turn on protocol logging when the user asked for it.

    Only this package is turned up: bleak's own debug output is a wall of D-Bus
    traffic that buries the frames the user asked to see.
    """
    if verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger(__package__).setLevel(logging.DEBUG)


async def _async_scan(seconds: float) -> list[tuple[BLEDevice, AdvertisementInfo]]:
    """Collect every advertisement that carries the Tuya BLE service."""
    discovered = await BleakScanner.discover(timeout=seconds, return_adv=True)
    found: list[tuple[BLEDevice, AdvertisementInfo]] = []
    for device, advertisement in discovered.values():
        if not _is_tuya(advertisement):
            continue
        found.append(
            (
                device,
                parse_advertisement(
                    advertisement.service_data, advertisement.manufacturer_data
                ),
            )
        )
    return found


async def _async_read(
    address: str,
    device_id: str,
    local_key: str,
    uuid: str | None,
    seconds: float,
) -> dict[int, DataPoint]:
    """Resolve the device, then run one full session against it."""
    discovered = await BleakScanner.discover(timeout=seconds, return_adv=True)
    match = discovered.get(address.upper())
    if match is None:
        message = f"{address} did not advertise within {seconds:.0f}s"
        raise typer.BadParameter(message)
    device, advertisement = match
    resolved = (
        uuid
        or parse_advertisement(
            advertisement.service_data, advertisement.manufacturer_data
        ).uuid
    )
    if not resolved:
        message = f"{address} advertised no uuid; pass --uuid"
        raise typer.BadParameter(message)
    client = TuyaBleClient(
        device,
        TuyaBleCredentials(uuid=resolved, device_id=device_id, local_key=local_key),
    )
    return await client.async_read_data_points()


def _is_tuya(advertisement: AdvertisementData) -> bool:
    """Report whether the advertisement exposes the Tuya BLE service."""
    return (
        SERVICE_UUID in advertisement.service_uuids
        or SERVICE_UUID in advertisement.service_data
    )
