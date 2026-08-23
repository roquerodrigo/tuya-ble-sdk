"""
The JSON shapes the gateway answers with, and the accessors that narrow them.

The gateway describes a device with free-form JSON, and this SDK types its
whole surface, so every value that crosses that boundary is read through one of
the accessors here rather than indexed straight out of a permissive mapping.
"""

from __future__ import annotations

import json

from ..exceptions import TuyaBleProtocolError

type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


def parse_json_object(raw: str | bytes) -> JsonObject:
    """Parse a JSON document that must be an object."""
    try:
        decoded: object = json.loads(raw)
    except ValueError as exception:
        message = f"Failed to parse the gateway answer: {exception}"
        raise TuyaBleProtocolError(message) from exception
    if not isinstance(decoded, dict):
        message = "Failed to parse the gateway answer: top level is not an object"
        raise TuyaBleProtocolError(message)
    return decoded


def dump_json(value: JsonValue) -> bytes:
    """Serialize a JSON value the way the app does, without whitespace padding."""
    return json.dumps(value, separators=(",", ":")).encode()


def optional_str(source: JsonObject, key: str) -> str | None:
    """Return a string field, or None when it is absent or empty."""
    value = source.get(key)
    return value if isinstance(value, str) and value else None


def require_str(source: JsonObject, key: str) -> str:
    """Return a string field, or fail when it is missing."""
    value = optional_str(source, key)
    if value is None:
        message = f"Failed to read {key}: not a non-empty string"
        raise TuyaBleProtocolError(message)
    return value
