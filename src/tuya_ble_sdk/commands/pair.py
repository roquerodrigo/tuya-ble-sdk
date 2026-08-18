"""Build the pairing request and judge the device's verdict on it."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..crypto import key_material
from ..exceptions import TuyaBleAuthenticationError, TuyaBleProtocolError
from ..protocol import PAIRING_REQUEST_LENGTH

if TYPE_CHECKING:
    from ..models import TuyaBleCredentials

_ACCEPTED = 0
_ALREADY_PAIRED = 2


def build_pairing_request(credentials: TuyaBleCredentials) -> bytes:
    """Lay the three credentials out in the fixed-width record the device wants."""
    request = (
        credentials.uuid.encode()
        + key_material(credentials.local_key)
        + credentials.device_id.encode()
    )
    if len(request) > PAIRING_REQUEST_LENGTH:
        message = (
            f"Failed to build the pairing request: the credentials take "
            f"{len(request)} bytes, {PAIRING_REQUEST_LENGTH} is the maximum"
        )
        raise TuyaBleProtocolError(message)
    return request.ljust(PAIRING_REQUEST_LENGTH, b"\x00")


def verify_pairing_result(data: bytes) -> None:
    """
    Accept the two outcomes that mean the session is usable.

    A device that was already paired answers ``2``, which is a success: the
    handshake it just completed still applies.
    """
    if len(data) != 1:
        message = (
            f"Failed to read the pairing result: {len(data)} bytes arrived, 1 expected"
        )
        raise TuyaBleProtocolError(message)
    if data[0] not in (_ACCEPTED, _ALREADY_PAIRED):
        message = (
            f"Failed to pair with the device: it rejected the credentials with "
            f"code {data[0]}"
        )
        raise TuyaBleAuthenticationError(message)
