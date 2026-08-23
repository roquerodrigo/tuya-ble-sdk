"""One Tuya account, and the device credentials it can hand out."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from ..exceptions import TuyaBleAuthenticationError, TuyaBleCloudError
from ..models import AccountSession, CloudDevice
from .constants import DEFAULT_REGION
from .crypto import encrypt_password, md5_hex
from .gateway import Gateway
from .json_values import optional_str, require_str

if TYPE_CHECKING:
    from types import TracebackType

    import aiohttp

    from .json_values import JsonObject

_LOGIN_TOKEN_API = "smartlife.m.user.username.token.get"  # noqa: S105
_LOGIN_API = "smartlife.m.user.email.password.login"
_HOME_LIST_API = "tuya.m.location.list"
_DEVICE_LIST_API = "tuya.m.my.group.device.list"

# The gateway answers a burst of logins with this instead of judging the
# credentials, and calling that an authentication failure sends the caller
# looking for a typo that is not there.
_RATE_LIMITED = "REQUEST_TOO_FREQUENTLY_PLEASE_TRY_AGAIN_LATER"


class TuyaBleCloudClient:
    """
    Looks up on the Tuya account what a BLE session cannot learn from the air.

    A device only accepts the pairing handshake when the caller already knows
    its device id and local key, and nothing the device broadcasts discloses
    them — the account that owns the device is the only source. One login is
    enough for every device on the account.
    """

    def __init__(
        self,
        email: str,
        password: str,
        country_code: str,
        region: str = DEFAULT_REGION,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Describe the account and the region its gateway lives in."""
        self._email = email
        self._password = password
        self._country_code = country_code
        self._gateway = Gateway(region, session=session)
        self._account: AccountSession | None = None

    async def __aenter__(self) -> Self:
        """Enter the context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Release the gateway's HTTP session."""
        await self.async_close()

    async def async_login(self) -> AccountSession:
        """
        Log in, replacing any session this client already held.

        The password's MD5 is RSA-encrypted under the key the token call hands
        out, and posted to the login call. A rejection is reported as an
        authentication error, unless the gateway is merely rate limiting.
        """
        try:
            token = await self._gateway.async_call_object(
                _LOGIN_TOKEN_API,
                "2.0",
                {
                    "countryCode": self._country_code,
                    "username": self._email,
                    "isUid": False,
                },
            )
            account = await self._gateway.async_call_object(
                _LOGIN_API,
                "3.0",
                {
                    "countryCode": self._country_code,
                    "email": self._email,
                    "ifencrypt": 1,
                    "options": '{"group": 1}',
                    "passwd": encrypt_password(
                        require_str(token, "publicKey"),
                        require_str(token, "exponent"),
                        md5_hex(self._password),
                    ),
                    "token": require_str(token, "token"),
                },
            )
        except TuyaBleCloudError as exception:
            if exception.code == _RATE_LIMITED:
                raise
            message = f"Failed to log in: {exception}"
            raise TuyaBleAuthenticationError(message) from exception
        self._account = AccountSession(
            sid=require_str(account, "sid"),
            ecode=require_str(account, "ecode"),
            uid=require_str(account, "uid"),
        )
        return self._account

    async def async_list_devices(self) -> list[CloudDevice]:
        """
        Return every device on the account, across all of its homes.

        Bluetooth and Wi-Fi devices are listed side by side, and the record of
        a Bluetooth one carries the same uuid its advertisement does.
        """
        account = self._account or await self.async_login()
        devices: list[CloudDevice] = []
        seen: set[str] = set()
        for home in await self._gateway.async_call_object_list(
            _HOME_LIST_API, "2.1", {}, account
        ):
            group_id = home.get("gid")
            if not isinstance(group_id, int):
                continue
            for raw in await self._gateway.async_call_object_list(
                _DEVICE_LIST_API, "1.0", {}, account, {"gid": str(group_id)}
            ):
                device = _parse_device(raw)
                if device and device.device_id not in seen:
                    seen.add(device.device_id)
                    devices.append(device)
        return devices

    async def async_close(self) -> None:
        """Release the gateway's HTTP session, if this client opened it."""
        await self._gateway.async_close()


def _parse_device(raw: JsonObject) -> CloudDevice | None:
    """
    Read one device list entry, skipping what cannot pair a BLE device.

    A record without an id, a local key or a uuid names nothing this SDK can
    use, whatever else it carries.
    """
    device_id = optional_str(raw, "devId")
    local_key = optional_str(raw, "localKey")
    uuid = optional_str(raw, "uuid")
    if not device_id or not local_key or not uuid:
        return None
    return CloudDevice(
        device_id=device_id,
        local_key=local_key,
        uuid=uuid,
        mac=(optional_str(raw, "mac") or "").replace(":", "").upper(),
        product_id=optional_str(raw, "productId"),
        name=optional_str(raw, "name") or device_id,
    )
