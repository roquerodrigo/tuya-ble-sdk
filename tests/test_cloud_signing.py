from __future__ import annotations

import pytest

from tuya_ble_sdk.cloud.body import decrypt_post_data, encrypt_post_data
from tuya_ble_sdk.cloud.crypto import hmac_sha256_hex, md5_hex
from tuya_ble_sdk.cloud.signing import (
    body_key,
    build_sign_string,
    post_data_sign_field,
    pre_login_body_key,
    sign,
    swap_sign_string,
)
from tuya_ble_sdk.exceptions import TuyaBleProtocolError


def test_the_sign_string_keeps_only_whitelisted_parameters():
    assert build_sign_string({"a": "api", "sdkVersion": "5.2.0"}) == "a=api"


def test_the_sign_string_drops_empty_parameters():
    assert build_sign_string({"a": "api", "sid": ""}) == "a=api"


def test_the_sign_string_is_sorted_by_key():
    assert build_sign_string({"v": "1.0", "a": "api"}) == "a=api||v=1.0"


def test_the_signature_is_an_hmac_under_the_composite_key():
    assert sign("a=api", "key") == hmac_sha256_hex("key", "a=api")


def test_swapping_reorders_the_two_halves_of_each_half():
    assert swap_sign_string("0" * 8 + "1" * 8 + "2" * 8 + "3" * 8) == (
        "1" * 8 + "0" * 8 + "3" * 8 + "2" * 8
    )


def test_a_value_that_is_not_an_md5_hex_is_left_alone():
    assert swap_sign_string("short") == "short"


def test_the_post_data_field_is_the_swapped_md5_of_the_body():
    assert post_data_sign_field("body") == swap_sign_string(md5_hex("body"))


def test_a_body_key_is_sixteen_characters():
    assert len(body_key("request", "ecode")) == 16
    assert len(pre_login_body_key("request")) == 16


def test_a_body_key_differs_before_and_after_the_login():
    assert body_key("request", "ecode", "key") != pre_login_body_key("request", "key")


def test_a_body_survives_the_round_trip():
    key = pre_login_body_key("request")

    assert decrypt_post_data(key, encrypt_post_data(key, b'{"a":1}')) == b'{"a":1}'


def test_every_encryption_uses_a_fresh_nonce():
    key = pre_login_body_key("request")

    assert encrypt_post_data(key, b"body") != encrypt_post_data(key, b"body")


def test_a_body_that_is_not_base64_is_rejected():
    with pytest.raises(TuyaBleProtocolError, match="decode"):
        decrypt_post_data(pre_login_body_key("request"), "not base64!")


def test_a_body_shorter_than_the_nonce_and_tag_is_rejected():
    with pytest.raises(TuyaBleProtocolError, match="shorter"):
        decrypt_post_data(pre_login_body_key("request"), "AAAA")


def test_a_body_encrypted_under_another_key_is_rejected():
    encrypted = encrypt_post_data(pre_login_body_key("one"), b"body")

    with pytest.raises(TuyaBleProtocolError, match="authentication tag"):
        decrypt_post_data(pre_login_body_key("two"), encrypted)
