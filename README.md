# tuya-ble-sdk

Python SDK for **Tuya Bluetooth Low Energy devices**. It speaks the Tuya BLE
GATT protocol directly — handshake, session key, encrypted frames and
datapoints — and knows nothing about Home Assistant.

Consumed by the [`ha-tuya-ble`](https://github.com/roquerodrigo/ha-tuya-ble)
integration, which pins it from `manifest.json`.

> **Status: scaffold.** The package is set up but the protocol is not
> implemented yet; `client.py` is still the template's sample. The design lives
> in [`ha-tuya-ble/PLAN.md`](https://github.com/roquerodrigo/ha-tuya-ble/blob/main/PLAN.md).

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
