# tuya-ble-sdk

Python SDK for **Tuya Bluetooth Low Energy devices**. It speaks the Tuya BLE
GATT protocol directly — handshake, session key, encrypted frames and
datapoints — and knows nothing about Home Assistant.

Consumed by the [`ha-tuya-ble`](https://github.com/roquerodrigo/ha-tuya-ble)
integration, which pins it from `manifest.json`.

## What it does

One read is one whole session: the client connects, performs the handshake,
collects the datapoint report and disconnects. Tuya BLE sensors are battery
powered and only listen for a moment after they advertise, so holding a
connection open would drain them and occupy a proxy slot for nothing.

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

## Command line

The optional `cli` extra installs a `tuya-ble` command:

```bash
uv run --extra cli tuya-ble scan
uv run --extra cli tuya-ble read \
    --address AA:BB:CC:DD:EE:FF --device-id <id> --local-key <key>
```

`scan` lists every nearby Tuya BLE device with its product id and uuid; `read`
runs one session and prints the datapoints it reported.

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

## Credits

The protocol implementation is derived from
[`PlusPlus-ua/ha_tuya_ble`](https://github.com/PlusPlus-ua/ha_tuya_ble) (MIT),
itself based on [`redphx/poc-tuya-ble-fingerbot`](https://github.com/redphx/poc-tuya-ble-fingerbot).

## License

[MIT](LICENSE)
