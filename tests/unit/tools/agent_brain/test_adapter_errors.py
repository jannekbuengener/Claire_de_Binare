"""Adapter structured-error and capability handling (mocked protocol surface)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from tools.agent_brain.adapter import AgentBrainAdapter
from tools.agent_brain.errors import ConsumerError, ConsumerErrorCode
from tools.agent_brain.pin import PINNED_AGENT_BRAIN_VERSION

pytestmark = pytest.mark.unit


@dataclass
class _FakeError:
    code: str
    message: str
    details: dict[str, Any] | None = None


@dataclass
class _FakeResponse:
    ok: bool
    data: dict[str, Any] | None = None
    error: _FakeError | None = None
    limitations: tuple[str, ...] = ()


def test_pin_mismatch_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tools.agent_brain.pin.installed_version",
        lambda: "0.1.0",
    )
    adapter = AgentBrainAdapter(invoke_fn=lambda *_a, **_k: _FakeResponse(ok=True, data={}))
    with pytest.raises(ConsumerError) as exc:
        adapter.verify_pin()
    assert exc.value.code is ConsumerErrorCode.CONTRACT_VERSION_MISMATCH
    assert exc.value.details["expected"] == PINNED_AGENT_BRAIN_VERSION
    assert exc.value.details["runtime"] == "0.1.0"


def test_capability_unavailable_not_empty_success() -> None:
    def invoke(operation: str, payload: dict[str, Any] | None = None) -> _FakeResponse:
        if operation == "capabilities":
            return _FakeResponse(
                ok=True,
                data={
                    "capabilities": [
                        {"capability": "context_read", "state": "unavailable"},
                    ]
                },
            )
        raise AssertionError(f"unexpected op {operation}")

    adapter = AgentBrainAdapter(
        invoke_fn=invoke,
        verify_pin=False,
    )
    with pytest.raises(ConsumerError) as exc:
        adapter.require_capability("context_read")
    assert exc.value.code is ConsumerErrorCode.CAPABILITY_UNAVAILABLE


@pytest.mark.parametrize(
    "code",
    [
        "invalid_input",
        "invalid_scope",
        "capability_unavailable",
        "backend_unavailable",
        "contract_version_mismatch",
        "internal_failure",
    ],
)
def test_structured_protocol_errors_mapped(code: str) -> None:
    def invoke(operation: str, payload: dict[str, Any] | None = None) -> _FakeResponse:
        return _FakeResponse(
            ok=False,
            error=_FakeError(code=code, message=f"boom:{code}", details={"k": 1}),
        )

    adapter = AgentBrainAdapter(invoke_fn=invoke, verify_pin=False)
    result = adapter.health()
    assert result.ok is False
    assert result.error is not None
    assert result.error["code"] == code
    assert "EMPTY" not in result.error["message"].upper()


def test_backend_unavailable_is_failure_not_empty_data() -> None:
    def invoke(operation: str, payload: dict[str, Any] | None = None) -> _FakeResponse:
        return _FakeResponse(
            ok=False,
            error=_FakeError(
                code="backend_unavailable",
                message="surreal backend unavailable",
            ),
        )

    adapter = AgentBrainAdapter(invoke_fn=invoke, verify_pin=False)
    result = adapter.health()
    assert result.ok is False
    assert result.data is None
    assert result.error["code"] == "backend_unavailable"


def test_happy_path_context_read_attaches_claire_policy() -> None:
    def invoke(operation: str, payload: dict[str, Any] | None = None) -> _FakeResponse:
        if operation == "capabilities":
            return _FakeResponse(
                ok=True,
                data={
                    "capabilities": [
                        {"capability": "context_read", "state": "available"},
                    ]
                },
            )
        if operation == "context_read":
            return _FakeResponse(ok=True, data={"package": {"ok": True}})
        raise AssertionError(operation)

    adapter = AgentBrainAdapter(invoke_fn=invoke, verify_pin=False)
    result = adapter.context_read(target_scope="issue:13-cutover")
    assert result.ok is True
    assert result.path == "agent_brain"
    assert result.data is not None
    assert result.data["claire_policy"]["policy_owner"] == "claire_de_binare"
    assert result.data["claire_policy"]["live_or_echtgeld"] is False
