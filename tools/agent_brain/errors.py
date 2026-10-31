"""Claire-side structured errors for the Agent Brain consumer path."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping


class ConsumerErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    INVALID_SCOPE = "invalid_scope"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    CONTRACT_VERSION_MISMATCH = "contract_version_mismatch"
    INTERNAL_FAILURE = "internal_failure"
    POLICY_BLOCKED = "policy_blocked"
    UNSUPPORTED_PATH = "unsupported_path"


# Map Agent Brain protocol error codes → Claire consumer codes (1:1 where shared).
_PROTOCOL_TO_CONSUMER: dict[str, ConsumerErrorCode] = {
    "invalid_input": ConsumerErrorCode.INVALID_INPUT,
    "invalid_scope": ConsumerErrorCode.INVALID_SCOPE,
    "capability_unavailable": ConsumerErrorCode.CAPABILITY_UNAVAILABLE,
    "backend_unavailable": ConsumerErrorCode.BACKEND_UNAVAILABLE,
    "contract_version_mismatch": ConsumerErrorCode.CONTRACT_VERSION_MISMATCH,
    "internal_failure": ConsumerErrorCode.INTERNAL_FAILURE,
    "unsupported_operation": ConsumerErrorCode.INVALID_INPUT,
}


@dataclass(frozen=True, slots=True)
class ConsumerError(Exception):
    """Fail-closed consumer error; never treat UNAVAILABLE as EMPTY."""

    code: ConsumerErrorCode
    message: str
    details: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, ConsumerErrorCode):
            object.__setattr__(self, "code", ConsumerErrorCode(self.code))
        msg = self.message.strip()
        if not msg:
            raise ValueError("message must not be blank")
        object.__setattr__(self, "message", msg)
        object.__setattr__(self, "details", dict(self.details or {}))

    def __str__(self) -> str:
        return f"{self.code.value}: {self.message}"

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code.value,
            "message": self.message,
            "details": dict(self.details or {}),
        }


def map_protocol_error_code(code: str | None) -> ConsumerErrorCode:
    if not code:
        return ConsumerErrorCode.INTERNAL_FAILURE
    return _PROTOCOL_TO_CONSUMER.get(str(code), ConsumerErrorCode.INTERNAL_FAILURE)


__all__ = [
    "ConsumerError",
    "ConsumerErrorCode",
    "map_protocol_error_code",
]
