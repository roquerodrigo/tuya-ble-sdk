"""
The ``et=3`` encrypted request and response body.

AES-GCM with a fresh 12-byte nonce, on the wire as base64 of
``nonce || ciphertext || tag``. Despite the Java helper being named
"appendNonce", the nonce goes at the front.
"""

from __future__ import annotations

import secrets
from base64 import b64decode, b64encode

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ..exceptions import TuyaBleProtocolError

_NONCE_LENGTH = 12
_TAG_LENGTH = 16


def encrypt_post_data(key: str, post_json: bytes) -> str:
    """Encrypt one request body and return it base64-encoded."""
    nonce = secrets.token_bytes(_NONCE_LENGTH)
    sealed = AESGCM(key.encode()).encrypt(nonce, post_json, None)
    return b64encode(nonce + sealed).decode()


def decrypt_post_data(key: str, encrypted: str) -> bytes:
    """Decrypt one base64 body, whether it came from a request or a response."""
    try:
        raw = b64decode(encrypted, validate=True)
    except ValueError as exception:
        message = f"Failed to decode the gateway body: {exception}"
        raise TuyaBleProtocolError(message) from exception
    if len(raw) < _NONCE_LENGTH + _TAG_LENGTH:
        message = "Failed to decode the gateway body: shorter than nonce and tag"
        raise TuyaBleProtocolError(message)
    try:
        return AESGCM(key.encode()).decrypt(
            raw[:_NONCE_LENGTH], raw[_NONCE_LENGTH:], None
        )
    except InvalidTag as exception:
        message = "Failed to decrypt the gateway body: authentication tag"
        raise TuyaBleProtocolError(message) from exception
