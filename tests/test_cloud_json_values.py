from __future__ import annotations

import pytest

from tuya_ble_sdk.cloud.json_values import (
    dump_json,
    optional_str,
    parse_json_object,
    require_str,
)
from tuya_ble_sdk.exceptions import TuyaBleProtocolError


def test_an_object_is_parsed():
    assert parse_json_object('{"a": 1}') == {"a": 1}


def test_a_document_that_is_not_json_is_rejected():
    with pytest.raises(TuyaBleProtocolError, match="parse"):
        parse_json_object("not json")


def test_a_document_that_is_not_an_object_is_rejected():
    with pytest.raises(TuyaBleProtocolError, match="not an object"):
        parse_json_object("[1]")


def test_a_dumped_body_carries_no_padding():
    assert dump_json({"a": 1, "b": "c"}) == b'{"a":1,"b":"c"}'


def test_an_absent_or_empty_string_reads_as_missing():
    assert optional_str({"a": ""}, "a") is None
    assert optional_str({}, "a") is None
    assert optional_str({"a": 1}, "a") is None


def test_a_required_string_that_is_missing_is_rejected():
    with pytest.raises(TuyaBleProtocolError, match="publicKey"):
        require_str({}, "publicKey")


def test_a_required_string_is_returned():
    assert require_str({"a": "b"}, "a") == "b"
