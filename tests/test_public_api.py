from __future__ import annotations

import tuya_ble_sdk


def test_every_exported_name_resolves():
    for name in tuya_ble_sdk.__all__:
        assert getattr(tuya_ble_sdk, name) is not None


def test_the_export_list_has_no_duplicates():
    assert len(tuya_ble_sdk.__all__) == len(set(tuya_ble_sdk.__all__))


def test_the_service_uuid_is_the_one_tuya_advertises():
    assert tuya_ble_sdk.SERVICE_UUID == "0000a201-0000-1000-8000-00805f9b34fb"
