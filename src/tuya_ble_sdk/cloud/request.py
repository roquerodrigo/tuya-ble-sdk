"""One gateway call, as it stands just before it is signed."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GatewayRequest:
    """
    What identifies a call on the wire.

    ``request_id`` is what the body key is derived from, so it belongs to the
    request rather than to the caller's arguments.
    """

    api: str
    version: str
    request_id: str
    encrypted_body: str
