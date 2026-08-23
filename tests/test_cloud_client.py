from __future__ import annotations

import json

import aiohttp
import pytest

from tuya_ble_sdk import (
    TuyaBleAuthenticationError,
    TuyaBleCloudClient,
    TuyaBleConnectionError,
    TuyaBleProtocolError,
)
from tuya_ble_sdk.cloud import gateway as gateway_module

from .fake_gateway import (
    BLE_DEVICE,
    COUNTRY_CODE,
    EMAIL,
    PASSWORD,
    SID,
    FakeGatewaySession,
    password_md5,
)


def build_client(session):
    return TuyaBleCloudClient(EMAIL, PASSWORD, COUNTRY_CODE, session=session)


async def test_login_returns_the_session_the_gateway_handed_back():
    session = FakeGatewaySession()

    account = await build_client(session).async_login()

    assert account.sid == SID
    assert session.received_password == password_md5()


async def test_listing_devices_logs_in_first():
    session = FakeGatewaySession()

    devices = await build_client(session).async_list_devices()

    assert session.calls[0] == "smartlife.m.user.username.token.get"
    assert [device.name for device in devices] == ["Soil sensor", "Living room light"]


async def test_a_listed_device_carries_what_pairing_needs():
    devices = await build_client(FakeGatewaySession()).async_list_devices()

    assert devices[0].device_id == BLE_DEVICE["devId"]
    assert devices[0].local_key == BLE_DEVICE["localKey"]
    assert devices[0].uuid == BLE_DEVICE["uuid"]
    assert devices[0].product_id == BLE_DEVICE["productId"]


async def test_the_mac_is_normalized_to_bare_uppercase_hex():
    session = FakeGatewaySession(devices=[{**BLE_DEVICE, "mac": "dc:23:51:e5:d1:3a"}])

    devices = await build_client(session).async_list_devices()

    assert devices[0].mac == "DC2351E5D13A"


async def test_a_device_without_credentials_is_skipped():
    session = FakeGatewaySession(
        devices=[
            {**BLE_DEVICE, "localKey": ""},
            {**BLE_DEVICE, "uuid": ""},
            {**BLE_DEVICE, "devId": ""},
        ]
    )

    assert await build_client(session).async_list_devices() == []


async def test_a_device_listed_by_two_homes_is_returned_once():
    session = FakeGatewaySession(homes=[{"gid": 41441017}, {"gid": 41441017}])

    devices = await build_client(session).async_list_devices()

    assert [device.device_id for device in devices] == [
        BLE_DEVICE["devId"],
        "ebe1f9b8f5d0732236bsli",
    ]


async def test_a_home_without_an_id_is_skipped():
    session = FakeGatewaySession(homes=[{"name": "no gid"}])

    assert await build_client(session).async_list_devices() == []


async def test_a_device_with_no_name_falls_back_to_its_id():
    session = FakeGatewaySession(devices=[{**BLE_DEVICE, "name": ""}])

    devices = await build_client(session).async_list_devices()

    assert devices[0].name == BLE_DEVICE["devId"]


async def test_rejected_credentials_raise_an_authentication_error():
    session = FakeGatewaySession(
        errors={
            "smartlife.m.user.email.password.login": {
                "errorCode": "USER_PASSWD_WRONG",
                "errorMsg": "wrong password",
            }
        }
    )

    with pytest.raises(TuyaBleAuthenticationError, match="wrong password"):
        await build_client(session).async_login()


async def test_a_rejection_without_a_message_still_names_the_call():
    session = FakeGatewaySession(
        errors={"smartlife.m.user.username.token.get": {"success": False}}
    )

    with pytest.raises(TuyaBleAuthenticationError, match="rejected"):
        await build_client(session).async_login()


async def test_an_answer_that_is_not_an_object_is_a_protocol_error():
    session = FakeGatewaySession()
    session.errors = {}

    async def post(url, data=None, headers=None):
        del url, data, headers
        return _plain(json.dumps({"result": [1, 2, 3]}))

    session.post = post

    with pytest.raises(TuyaBleProtocolError, match="not an object"):
        await build_client(session).async_login()


async def test_an_answer_that_is_not_a_list_is_a_protocol_error():
    session = FakeGatewaySession(homes={"gid": 1})

    with pytest.raises(TuyaBleProtocolError, match="not a list"):
        await build_client(session).async_list_devices()


async def test_an_empty_result_is_a_protocol_error():
    session = FakeGatewaySession()

    async def post(url, data=None, headers=None):
        del url, data, headers
        return _plain(json.dumps({"success": True}))

    session.post = post

    with pytest.raises(TuyaBleProtocolError, match="empty"):
        await build_client(session).async_login()


async def test_an_unreachable_gateway_is_a_connection_error():
    session = FakeGatewaySession()

    async def post(url, data=None, headers=None):
        del url, data, headers
        raise aiohttp.ClientError("no route to host")

    session.post = post

    with pytest.raises(TuyaBleConnectionError, match="no route to host"):
        await build_client(session).async_login()


async def test_a_gateway_that_never_answers_is_a_connection_error():
    session = FakeGatewaySession()

    async def post(url, data=None, headers=None):
        del url, data, headers
        raise TimeoutError

    session.post = post

    with pytest.raises(TuyaBleConnectionError, match="timed out"):
        await build_client(session).async_login()


async def test_closing_leaves_a_session_it_did_not_open_alone():
    session = FakeGatewaySession()

    await build_client(session).async_close()

    assert not session.closed


async def test_the_context_manager_releases_the_client():
    session = FakeGatewaySession()

    async with build_client(session) as client:
        await client.async_login()

    assert not session.closed


async def test_a_session_the_client_opened_itself_is_closed(monkeypatch):
    session = FakeGatewaySession()
    monkeypatch.setattr(gateway_module.aiohttp, "ClientSession", lambda: session)

    client = TuyaBleCloudClient(EMAIL, PASSWORD, COUNTRY_CODE)
    await client.async_login()
    await client.async_close()

    assert session.closed


class _PlainResponse:
    def __init__(self, text):
        self._text = text

    def raise_for_status(self):
        return None

    async def text(self):
        return self._text


def _plain(text):
    """Answer with an envelope that carries no encrypted body."""
    return _PlainResponse(text)
