"""A fake Tuya app gateway the cloud tests drive instead of the real one."""

from __future__ import annotations

import json

from cryptography.hazmat.primitives.asymmetric import padding, rsa

from tuya_ble_sdk.cloud.body import decrypt_post_data, encrypt_post_data
from tuya_ble_sdk.cloud.crypto import md5_hex
from tuya_ble_sdk.cloud.signing import (
    body_key,
    build_sign_string,
    post_data_sign_field,
    pre_login_body_key,
    sign,
)

EMAIL = "someone@example.com"
PASSWORD = "correct horse"
COUNTRY_CODE = "55"
SID = "sid-1234"
ECODE = "ecode-5678"
UID = "uid-9012"
HOME_ID = 41441017

# Generated once: a fresh key per fake gateway would dominate the test run.
SERVER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)

BLE_DEVICE = {
    "devId": "ebc0496t9ektfzip",
    "localKey": "-xGE=f(253=Zziu-",
    "uuid": "792e1bd35df2d02e",
    "mac": "DC2351E5D13A",
    "productId": "gvygg3m8",
    "name": "Soil sensor",
}
WIFI_DEVICE = {
    "devId": "ebe1f9b8f5d0732236bsli",
    "localKey": "CtN[u^c4j}@=uf-Q",
    "uuid": "c4a5ce0d553e28fa",
    "mac": "4ca919c0af72",
    "productId": "4tjsokgxfdetovsd",
    "name": "Living room light",
}


class FakeResponse:
    """The little of an aiohttp response the gateway touches."""

    def __init__(self, text: str) -> None:
        self._text = text

    def raise_for_status(self) -> None:
        return None

    async def text(self) -> str:
        return self._text


class FakeGatewaySession:
    """
    Answers the signed calls the gateway makes, as the real one would.

    The signature and the encrypted body are verified rather than ignored, so
    a test failure means the wire format changed and not just the mock.
    """

    def __init__(self, homes=None, devices=None, errors=None):
        self._key = SERVER_KEY
        self.homes = [{"gid": HOME_ID}] if homes is None else homes
        self.devices = [BLE_DEVICE, WIFI_DEVICE] if devices is None else devices
        self.errors = errors or {}
        self.calls: list[str] = []
        self.closed = False
        self.received_password: str | None = None

    async def post(self, url, data=None, headers=None):
        del url, headers
        api = data["a"]
        self.calls.append(api)
        key = (
            body_key(data["requestId"], ECODE)
            if "sid" in data
            else pre_login_body_key(data["requestId"])
        )
        self._verify_signature(data)
        post = json.loads(decrypt_post_data(key, data["postData"]))
        error = self.errors.get(api)
        if error:
            return FakeResponse(json.dumps(error))
        result = self._result(api, post, data)
        return FakeResponse(
            json.dumps(
                {
                    "result": encrypt_post_data(
                        key, json.dumps({"result": result}).encode()
                    )
                }
            )
        )

    async def close(self):
        self.closed = True

    def _verify_signature(self, data):
        signed = {**data, "postData": post_data_sign_field(data["postData"])}
        del signed["sign"]
        assert data["sign"] == sign(build_sign_string(signed))

    def _result(self, api, post, data):
        if api == "smartlife.m.user.username.token.get":
            numbers = self._key.public_key().public_numbers()
            return {
                "publicKey": str(numbers.n),
                "exponent": str(numbers.e),
                "token": "token-3456",
            }
        if api == "smartlife.m.user.email.password.login":
            self.received_password = self._key.decrypt(
                bytes.fromhex(post["passwd"]), padding.PKCS1v15()
            ).decode()
            return {"sid": SID, "ecode": ECODE, "uid": UID}
        if api == "tuya.m.location.list":
            return self.homes
        if api == "tuya.m.my.group.device.list":
            assert data["gid"] == str(HOME_ID)
            return self.devices
        message = f"unexpected api {api}"
        raise AssertionError(message)


def password_md5() -> str:
    """Return what the login call is expected to carry as the password."""
    return md5_hex(PASSWORD)
