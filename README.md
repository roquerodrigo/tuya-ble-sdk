# tuya-ble-sdk

[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-db61a2?logo=githubsponsors&logoColor=white&style=for-the-badge)](https://github.com/sponsors/roquerodrigo)

Python SDK for **Tuya Bluetooth Low Energy devices**. It speaks the Tuya BLE
GATT protocol directly — handshake, session key, encrypted frames and
datapoints — and knows nothing about Home Assistant. It also reads the device
credentials off the Tuya account, since the handshake needs values the device
never broadcasts.

Consumed by the [`ha-tuya-ble`](https://github.com/roquerodrigo/ha-tuya-ble)
integration, which pins it from `manifest.json`.

## What it does

One read is one whole session: the client connects, performs the handshake,
collects the datapoint report and disconnects. Tuya BLE sensors are battery
powered and only listen for a moment after they advertise, so holding a
connection open would drain them and occupy a proxy slot for nothing.

The session is bounded end to end: it gives the connection back after
`SESSION_TIMEOUT` (60 s) whatever the radio is doing, and the connection
attempt itself after `CONNECT_TIMEOUT` (20 s). A proxy shares a handful of
slots between every device behind it, so a read that cannot finish has to stop
holding one.

```python
from tuya_ble_sdk import TuyaBleClient, TuyaBleCredentials, parse_advertisement

info = parse_advertisement(service_data, manufacturer_data)
client = TuyaBleClient(
    ble_device,
    TuyaBleCredentials(uuid=info.uuid, device_id=device_id, local_key=local_key),
)
data_points = await client.async_read_data_points()
```

Discovery belongs to the caller: the client takes an already-resolved
`BLEDevice`, which is what lets Home Assistant hand over a device seen through
a Bluetooth proxy.

`parse_advertisement` reads what the advertisement discloses — every field of
the result is optional. The uuid is encrypted with the product-id record
broadcast beside it, so no cloud call is needed to learn it; the readable
product id, however, is only there on an **unbound** device. One bound to a
Tuya account broadcasts an obfuscated value in its place: those bytes still
decrypt the uuid, but they name no product, and the caller has to learn what
the device is some other way.

## Credentials from the account

A session needs a device id and a local key, and no device discloses either:
only the Tuya account that owns it does. `TuyaBleCloudClient` logs into the
mobile app gateway with the account's e-mail and password and returns what it
knows about every device on it.

```python
from tuya_ble_sdk import TuyaBleCloudClient

async with TuyaBleCloudClient(email, password, country_code, region="us") as cloud:
    devices = await cloud.async_list_devices()

paired = next(device for device in devices if device.uuid == info.uuid)
credentials = TuyaBleCredentials(
    uuid=paired.uuid, device_id=paired.device_id, local_key=paired.local_key
)
```

The account describes a Bluetooth device with the same `uuid` its
advertisement carries and with its `mac`, so either one ties an account record
to a device seen over the air. The record also names the `product_id` a bound
device stops broadcasting.

Region is the account's data centre — one of `us`, `eu`, `cn`, `in`, `we` — and
`country_code` is the calling code the account was registered with (`55` for
Brazil). Nothing is cached: one client is one login.

## Command line

The optional `cli` extra installs a `tuya-ble` command:

```bash
uv run --extra cli tuya-ble scan
uv run --extra cli tuya-ble read \
    --address AA:BB:CC:DD:EE:FF --device-id <id> --local-key <key>
```

`scan` lists every nearby Tuya BLE device with its product id and uuid; `read`
runs one session and prints the datapoints it reported. `credentials` logs into
a Tuya account and prints the device id and local key it holds for each device:

```bash
uv run --extra cli tuya-ble credentials --email you@example.com --country-code 55
```

## Not implemented

The device may report datapoints in a *signed* form (`0x8004` / `0x8005`)
instead of the plain one this SDK reads. Those two commands are recognised and
logged, not parsed: the reference implementation disagrees with itself about
where the records start inside them, and no device was available to settle it.
A device that uses them shows up as a read that reports no datapoint, with the
command name in the debug log.

## Development

```bash
uv sync                     # create .venv and install dependencies
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest               # 90 % coverage gate
```

Runtime dependencies carry a `>=` floor and nothing else: Home Assistant pins its
own transitive dependencies exactly, so an `==` pin here eventually contradicts
HA's pin and the integration stops installing.

## Support

This SDK is built and maintained on personal time, on hardware bought for the purpose. If it is useful to you, consider [sponsoring the work](https://github.com/sponsors/roquerodrigo) — it keeps the devices, the testing and the releases coming.

## Credits

The protocol implementation is derived from
[`PlusPlus-ua/ha_tuya_ble`](https://github.com/PlusPlus-ua/ha_tuya_ble) (MIT),
itself based on [`redphx/poc-tuya-ble-fingerbot`](https://github.com/redphx/poc-tuya-ble-fingerbot).

## License

[MIT](LICENSE)
