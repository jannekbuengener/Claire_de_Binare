"""RFC 8785 JSON Canonicalization Scheme (JCS) for contract hashing.

Official source: https://www.rfc-editor.org/info/rfc8785/

CDB policy for cdb.agent_execution.v1:
- Only JSON types object/array/string/number/boolean/null.
- Numbers must be finite integers (no float, no NaN, no Infinity).
- No silent fallback serializers.

This module implements the subset required for deterministic contract digests
without adding a third-party JCS dependency.
"""

from __future__ import annotations

import math
from typing import Any

from tools.agent_execution_contract.errors import ContractValidationError


def _escape_string(value: str) -> str:
    parts: list[str] = ['"']
    for ch in value:
        code = ord(ch)
        if ch == '"':
            parts.append('\\"')
        elif ch == "\\":
            parts.append("\\\\")
        elif ch == "\b":
            parts.append("\\b")
        elif ch == "\f":
            parts.append("\\f")
        elif ch == "\n":
            parts.append("\\n")
        elif ch == "\r":
            parts.append("\\r")
        elif ch == "\t":
            parts.append("\\t")
        elif code < 0x20:
            parts.append(f"\\u{code:04x}")
        else:
            parts.append(ch)
    parts.append('"')
    return "".join(parts)


def _serialize_number(value: int | float) -> str:
    if isinstance(value, bool):
        # bool is a subclass of int; callers must route bools elsewhere.
        raise ContractValidationError(
            "CONTRACT_NONDETERMINISTIC_NUMBER",
            "boolean must not be serialized as number",
        )
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ContractValidationError(
                "CONTRACT_NONDETERMINISTIC_NUMBER",
                "NaN and Infinity are rejected by RFC 8785 / CDB policy",
            )
        raise ContractValidationError(
            "CONTRACT_NONDETERMINISTIC_NUMBER",
            "floating-point numbers are rejected for cdb.agent_execution.v1",
        )
    if isinstance(value, int):
        return str(value)
    raise ContractValidationError(
        "CONTRACT_NONDETERMINISTIC_NUMBER",
        f"unsupported number type: {type(value).__name__}",
    )


def _serialize(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return _escape_string(value)
    if isinstance(value, bool):
        # Unreachable after True/False checks; kept for type clarity.
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return _serialize_number(value)
    if isinstance(value, float):
        return _serialize_number(value)
    if isinstance(value, list):
        return "[" + ",".join(_serialize(item) for item in value) + "]"
    if isinstance(value, dict):
        items = []
        for key in sorted(value.keys()):
            if not isinstance(key, str):
                raise ContractValidationError(
                    "CONTRACT_INVALID_OBJECT_KEY",
                    f"object keys must be strings, got {type(key).__name__}",
                )
            items.append(_escape_string(key) + ":" + _serialize(value[key]))
        return "{" + ",".join(items) + "}"
    raise ContractValidationError(
        "CONTRACT_UNSUPPORTED_TYPE",
        f"unsupported JSON type for JCS: {type(value).__name__}",
    )


def canonicalize(value: Any) -> str:
    """Return RFC 8785 canonical JSON text (no insignificant whitespace)."""
    return _serialize(value)


def canonicalize_bytes(value: Any) -> bytes:
    """UTF-8 bytes of the canonical JSON representation."""
    return canonicalize(value).encode("utf-8")
