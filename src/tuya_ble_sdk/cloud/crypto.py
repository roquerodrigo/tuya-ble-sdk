"""Digests and password encryption the gateway's calls are built on."""

from __future__ import annotations

import hashlib
import hmac

from cryptography.hazmat.primitives.asymmetric import padding, rsa


def _as_bytes(value: str | bytes) -> bytes:
    """Encode a value the digests take either way."""
    return value.encode() if isinstance(value, str) else value


def md5_hex(value: str | bytes) -> str:
    """Return the lowercase hex MD5 digest the key derivations use."""
    return hashlib.md5(_as_bytes(value), usedforsecurity=False).hexdigest()


def hmac_sha256_hex(key: str | bytes, message: str | bytes) -> str:
    """Return the lowercase hex HMAC-SHA256 digest."""
    return hmac.new(_as_bytes(key), _as_bytes(message), hashlib.sha256).hexdigest()


def encrypt_password(modulus_decimal: str, exponent: str, password_md5: str) -> str:
    """
    Encrypt the password MD5 under the key the token call hands out.

    The modulus arrives as a decimal string, the padding is PKCS#1 v1.5 and the
    output is hex rather than base64.
    """
    public_key = rsa.RSAPublicNumbers(int(exponent), int(modulus_decimal)).public_key()
    return public_key.encrypt(password_md5.encode(), padding.PKCS1v15()).hex()
