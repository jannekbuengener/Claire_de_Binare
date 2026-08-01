"""Provider protocol and MockProvider for #4253 (no live/network/shell)."""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Protocol

from tools.agent_control.errors import DispatchError

PROVIDER_STATUSES = (
    "QUEUED",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
    "UNKNOWN",
)

_SECRET_HINT = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|bearer)\b\s*[:=]\s*\S+"
)


@dataclass
class ProviderRequest:
    run_id: str
    contract_id: str
    contract_digest: str
    agent_id: str
    scenario: str = "success"
    delivery_receipt: dict[str, Any] | None = None
    cancel_reason: str | None = None


@dataclass
class ProviderResult:
    provider_id: str
    provider_run_id: str
    normalized_status: str
    usage: dict[str, int] = field(default_factory=dict)
    result_refs: dict[str, Any] = field(default_factory=dict)
    error_category: str | None = None
    error_code: str | None = None
    delivery_receipt: dict[str, Any] | None = None
    cancel_confirmed: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_run_id": self.provider_run_id,
            "normalized_status": self.normalized_status,
            "usage": dict(self.usage),
            "result_refs": deepcopy(self.result_refs),
            "error_category": self.error_category,
            "error_code": self.error_code,
            "delivery_receipt": deepcopy(self.delivery_receipt),
            "cancel_confirmed": self.cancel_confirmed,
        }


class Provider(Protocol):
    provider_id: str

    def dispatch(self, request: ProviderRequest) -> ProviderResult: ...

    def watch(self, provider_run_id: str) -> ProviderResult: ...

    def cancel(self, provider_run_id: str, reason: str) -> ProviderResult: ...


def _reject_secret_payload(node: Any, *, path: str = "$") -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            _reject_secret_payload(value, path=f"{path}.{key}")
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            _reject_secret_payload(value, path=f"{path}[{idx}]")
    elif isinstance(node, str) and _SECRET_HINT.search(node):
        raise DispatchError(
            "DISPATCH_PROVIDER_SECRET_PAYLOAD",
            f"secret-like provider payload rejected at {path}",
        )


def sanitize_provider_result(result: ProviderResult) -> ProviderResult:
    if result.normalized_status not in PROVIDER_STATUSES:
        raise DispatchError(
            "DISPATCH_PROVIDER_STATUS_UNKNOWN",
            f"unknown provider status: {result.normalized_status!r}",
        )
    _reject_secret_payload(result.as_dict())
    return result


@dataclass
class _MockInternal:
    scenario: str
    status: str
    usage: dict[str, int]
    delivery_receipt: dict[str, Any] | None
    watch_ticks: int = 0
    cancel_requested: bool = False
    cancel_confirmed: bool | None = None
    request: ProviderRequest | None = None


class MockProvider:
    """In-process mock provider. Never performs shell/network/GitHub actions."""

    provider_id = "mock"

    def __init__(self) -> None:
        self._runs: dict[str, _MockInternal] = {}
        self.dispatch_calls = 0
        self.watch_calls = 0
        self.cancel_calls = 0

    def _provider_run_id(self, request: ProviderRequest) -> str:
        digest = hashlib.sha256(
            f"{request.run_id}:{request.contract_digest}:{request.scenario}".encode()
        ).hexdigest()[:16]
        return f"mock-{digest}"

    def dispatch(self, request: ProviderRequest) -> ProviderResult:
        self.dispatch_calls += 1
        provider_run_id = self._provider_run_id(request)
        if provider_run_id in self._runs:
            # Idempotent replay of identical dispatch.
            internal = self._runs[provider_run_id]
            return sanitize_provider_result(
                ProviderResult(
                    provider_id=self.provider_id,
                    provider_run_id=provider_run_id,
                    normalized_status=internal.status,
                    usage=dict(internal.usage),
                    result_refs={"replay": True},
                    delivery_receipt=deepcopy(internal.delivery_receipt),
                )
            )

        scenario = request.scenario or "success"
        if scenario == "malformed":
            raise DispatchError(
                "DISPATCH_PROVIDER_MALFORMED",
                "mock provider produced malformed response",
            )

        status = "QUEUED"
        usage = {"iterations": 0, "tool_calls": 0}
        receipt = deepcopy(request.delivery_receipt)
        cancel_confirmed: bool | None = None

        if scenario == "fail_on_dispatch":
            status = "FAILED"
        elif scenario == "unknown_status":
            status = "UNKNOWN"
        elif scenario == "budget_exceeded":
            status = "QUEUED"
            usage = {"iterations": 10_000, "tool_calls": 10_000}

        internal = _MockInternal(
            scenario=scenario,
            status=status,
            usage=usage,
            delivery_receipt=receipt,
            cancel_confirmed=cancel_confirmed,
            request=request,
        )
        self._runs[provider_run_id] = internal
        return sanitize_provider_result(
            ProviderResult(
                provider_id=self.provider_id,
                provider_run_id=provider_run_id,
                normalized_status=status,
                usage=dict(usage),
                result_refs={"scenario": scenario},
                error_category="provider" if status == "FAILED" else None,
                error_code="MOCK_DISPATCH_FAILED" if status == "FAILED" else None,
                delivery_receipt=deepcopy(receipt),
            )
        )

    def watch(self, provider_run_id: str) -> ProviderResult:
        self.watch_calls += 1
        internal = self._runs.get(provider_run_id)
        if internal is None:
            raise DispatchError(
                "DISPATCH_PROVIDER_RUN_NOT_FOUND",
                f"unknown provider_run_id: {provider_run_id}",
            )
        internal.watch_ticks += 1
        scenario = internal.scenario

        if internal.cancel_requested:
            if scenario == "timeout_cancel_unconfirmed":
                internal.cancel_confirmed = False
                internal.status = "RUNNING"
            else:
                internal.cancel_confirmed = True
                internal.status = "CANCELLED"
        elif scenario == "fail_on_watch" and internal.watch_ticks >= 1:
            internal.status = "FAILED"
            internal.usage = {"iterations": 1, "tool_calls": 1}
        elif scenario == "unknown_status":
            internal.status = "UNKNOWN"
        elif scenario == "budget_exceeded":
            internal.status = "RUNNING"
            internal.usage = {"iterations": 10_000, "tool_calls": 10_000}
        elif scenario in {"success", "timeout_cancel_confirmed"}:
            if internal.watch_ticks == 1:
                internal.status = "RUNNING"
                internal.usage = {"iterations": 1, "tool_calls": 1}
            else:
                internal.status = "SUCCEEDED"
                internal.usage = {"iterations": 2, "tool_calls": 3}
        elif scenario in {"stay_running", "timeout_cancel_unconfirmed"}:
            internal.status = "RUNNING"
            internal.usage = {"iterations": internal.watch_ticks, "tool_calls": 1}

        error_code = None
        error_category = None
        if internal.status == "FAILED":
            error_category = "provider"
            error_code = "MOCK_WATCH_FAILED"
        elif internal.status == "UNKNOWN":
            error_category = "provider"
            error_code = "MOCK_UNKNOWN_STATUS"

        return sanitize_provider_result(
            ProviderResult(
                provider_id=self.provider_id,
                provider_run_id=provider_run_id,
                normalized_status=internal.status,
                usage=dict(internal.usage),
                result_refs={"scenario": scenario, "watch_ticks": internal.watch_ticks},
                error_category=error_category,
                error_code=error_code,
                delivery_receipt=deepcopy(internal.delivery_receipt),
                cancel_confirmed=internal.cancel_confirmed,
            )
        )

    def cancel(self, provider_run_id: str, reason: str) -> ProviderResult:
        self.cancel_calls += 1
        internal = self._runs.get(provider_run_id)
        if internal is None:
            raise DispatchError(
                "DISPATCH_PROVIDER_RUN_NOT_FOUND",
                f"unknown provider_run_id: {provider_run_id}",
            )
        internal.cancel_requested = True
        if internal.scenario == "timeout_cancel_unconfirmed":
            internal.cancel_confirmed = False
            status = "RUNNING"
        else:
            internal.cancel_confirmed = True
            internal.status = "CANCELLED"
            status = "CANCELLED"
        return sanitize_provider_result(
            ProviderResult(
                provider_id=self.provider_id,
                provider_run_id=provider_run_id,
                normalized_status=status,
                usage=dict(internal.usage),
                result_refs={"cancel_reason": reason},
                error_category=None,
                error_code=None,
                delivery_receipt=deepcopy(internal.delivery_receipt),
                cancel_confirmed=internal.cancel_confirmed,
            )
        )


_PROVIDERS: dict[str, type] = {
    "mock": MockProvider,
}


def get_provider(provider_id: str) -> Provider:
    if provider_id != "mock":
        raise DispatchError(
            "PROVIDER_LIVE_DISPATCH_FORBIDDEN",
            f"live provider {provider_id!r} forbidden in #4253; only mock allowed",
        )
    return MockProvider()


def provider_registry() -> dict[str, str]:
    return {key: cls.__name__ for key, cls in sorted(_PROVIDERS.items())}
