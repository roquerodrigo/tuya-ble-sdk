"""The Tuya mobile app gateway: signed, encrypted calls and their answers."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING
from uuid import uuid4

import aiohttp

from ..exceptions import (
    TuyaBleCloudError,
    TuyaBleConnectionError,
    TuyaBleProtocolError,
)
from .body import decrypt_post_data, encrypt_post_data
from .constants import (
    APP_VERSION,
    CH_KEY,
    CLIENT_ID,
    COMPOSITE_KEY,
    DEFAULT_DEVICE_FINGERPRINT,
    DEFAULT_REGION,
    LANGUAGE,
    REQUEST_TIMEOUT_SECONDS,
    SDK_VERSION,
    TTID,
    gateway_url,
)
from .json_values import dump_json, optional_str, parse_json_object
from .request import GatewayRequest
from .signing import (
    body_key,
    build_sign_string,
    post_data_sign_field,
    pre_login_body_key,
    sign,
)

if TYPE_CHECKING:
    from ..models import AccountSession
    from .json_values import JsonObject, JsonValue


class Gateway:
    """
    Calls the mobile API gateway on behalf of one account.

    Every call is signed, its body is AES-GCM encrypted (``et=3``) and its
    answer is encrypted the same way. The gateway owns no session state:
    callers pass the :class:`AccountSession` back in.
    """

    def __init__(
        self,
        region: str = DEFAULT_REGION,
        device_fingerprint: str = DEFAULT_DEVICE_FINGERPRINT,
        session: aiohttp.ClientSession | None = None,
        composite_key: str = COMPOSITE_KEY,
    ) -> None:
        """Point the gateway at a region and adopt an HTTP session, if given."""
        self._url = gateway_url(region)
        self._device_fingerprint = device_fingerprint
        self._composite_key = composite_key
        self._session = session
        self._owns_session = session is None

    async def async_call(
        self,
        api: str,
        version: str,
        post: JsonValue,
        account: AccountSession | None = None,
        extra_params: dict[str, str] | None = None,
    ) -> JsonValue:
        """
        Issue one signed ``et=3`` request and return the decrypted result.

        Without an account the call is a pre-login one, whose body key is
        derived from the composite key alone.
        """
        request_id = str(uuid4())
        key = (
            body_key(request_id, account.ecode, self._composite_key)
            if account
            else pre_login_body_key(request_id, self._composite_key)
        )
        request = GatewayRequest(
            api, version, request_id, encrypt_post_data(key, dump_json(post))
        )
        params = self._build_params(request, account, extra_params)
        return self._unwrap(api, key, await self._async_post(api, params))

    async def async_call_object(
        self,
        api: str,
        version: str,
        post: JsonValue,
        account: AccountSession | None = None,
        extra_params: dict[str, str] | None = None,
    ) -> JsonObject:
        """Call an API whose result must be an object."""
        result = await self.async_call(api, version, post, account, extra_params)
        if not isinstance(result, dict):
            message = f"Failed to call {api}: the result is not an object"
            raise TuyaBleProtocolError(message)
        return result

    async def async_call_object_list(
        self,
        api: str,
        version: str,
        post: JsonValue,
        account: AccountSession,
        extra_params: dict[str, str] | None = None,
    ) -> list[JsonObject]:
        """Call an API whose result must be a list of objects."""
        result = await self.async_call(api, version, post, account, extra_params)
        if not isinstance(result, list):
            message = f"Failed to call {api}: the result is not a list"
            raise TuyaBleProtocolError(message)
        return [item for item in result if isinstance(item, dict)]

    async def async_close(self) -> None:
        """Release the HTTP session, but only the one this gateway opened."""
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    def _build_params(
        self,
        request: GatewayRequest,
        account: AccountSession | None,
        extra_params: dict[str, str] | None,
    ) -> dict[str, str]:
        """Assemble the form parameters, signing the whitelisted ones."""
        params = {
            "a": request.api,
            "v": request.version,
            "clientId": CLIENT_ID,
            "time": str(int(time.time())),
            "requestId": request.request_id,
            "lang": LANGUAGE,
            "deviceId": self._device_fingerprint,
            "appVersion": APP_VERSION,
            "ttid": TTID,
            "os": "Android",
            "sdkVersion": SDK_VERSION,
            "chKey": CH_KEY,
            "et": "3",
            "postData": request.encrypted_body,
        }
        if account:
            params["sid"] = account.sid
        if extra_params:
            params.update(extra_params)
        signed = dict(params)
        signed["postData"] = post_data_sign_field(request.encrypted_body)
        params["sign"] = sign(build_sign_string(signed), self._composite_key)
        return params

    async def _async_post(self, api: str, params: dict[str, str]) -> str:
        """Send the form and return the raw answer."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                response = await self._session.post(
                    self._url,
                    data=params,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "User-Agent": f"TY/{APP_VERSION}",
                    },
                )
                response.raise_for_status()
                return await response.text()
        except TimeoutError as exception:
            message = f"Failed to call {api}: timed out"
            raise TuyaBleConnectionError(message) from exception
        except aiohttp.ClientError as exception:
            message = f"Failed to call {api}: {exception}"
            raise TuyaBleConnectionError(message) from exception

    def _unwrap(self, api: str, key: str, raw: str) -> JsonValue:
        """Decrypt the answer envelope and return the result it carries."""
        envelope = parse_json_object(raw)
        result = envelope.get("result")
        if isinstance(result, str) and result:
            inner = parse_json_object(decrypt_post_data(key, result))
            envelope = {**envelope, **inner}
            result = inner.get("result")
        error_code = optional_str(envelope, "errorCode")
        if error_code or envelope.get("success") is False:
            message = optional_str(envelope, "errorMsg") or "the request was rejected"
            raise TuyaBleCloudError(api, error_code or "", message)
        if result is None:
            message = f"Failed to call {api}: the result is empty"
            raise TuyaBleProtocolError(message)
        return result
