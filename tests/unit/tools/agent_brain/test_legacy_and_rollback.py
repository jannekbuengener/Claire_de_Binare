"""Legacy path preservation and explicit rollback (no dual-run / #18 parity)."""

from __future__ import annotations

import pytest

from tools.agent_brain.adapter import AgentBrainAdapter, ConsumerResult
from tools.agent_brain.consumer import read_context, rollback_to_legacy
from tools.agent_brain.errors import ConsumerError, ConsumerErrorCode
from tools.agent_brain.legacy import LegacyContextPath
from tools.agent_brain.path_selection import ConsumerPath

pytestmark = pytest.mark.unit


def _artifact() -> dict[str, object]:
    return {
        "artifact_id": "docs/onboarding/repo_brain_context_intelligence.md",
        "artifact_type": "doc",
        "summary": "legacy path smoke artifact",
    }


def test_legacy_path_still_builds_context_package() -> None:
    result = LegacyContextPath().context_read(
        target_scope="issue:13-legacy",
        artifacts=[_artifact()],
    )
    assert result.ok is True
    assert result.path == "legacy"
    assert result.data is not None
    assert "package" in result.data
    assert result.data["legacy_owner"] == "tools.surrealdb.context_package_v2"
    assert result.data["claire_policy"]["policy_owner"] == "claire_de_binare"


def test_path_selection_legacy_vs_agent_brain() -> None:
    legacy = read_context(
        target_scope="issue:13-path",
        artifacts=[_artifact()],
        path=ConsumerPath.LEGACY,
    )
    assert legacy.path == "legacy"

    def invoke(operation: str, payload=None):
        from dataclasses import dataclass

        @dataclass
        class R:
            ok: bool
            data: dict | None = None
            error: object | None = None
            limitations: tuple = ()

        if operation == "capabilities":
            return R(
                ok=True,
                data={"capabilities": [{"capability": "context_read", "state": "available"}]},
            )
        return R(ok=True, data={"via": "agent_brain"})

    brain = read_context(
        target_scope="issue:13-path",
        artifacts=[_artifact()],
        path=ConsumerPath.AGENT_BRAIN,
        adapter=AgentBrainAdapter(invoke_fn=invoke, verify_pin=False),
    )
    assert brain.path == "agent_brain"
    assert brain.ok is True


def test_rollback_to_legacy_after_agent_brain_failure() -> None:
    class BoomAdapter(AgentBrainAdapter):
        def context_read(self, **kwargs):  # type: ignore[no-untyped-def]
            return ConsumerResult(
                ok=False,
                operation="context_read",
                path="agent_brain",
                error={
                    "code": ConsumerErrorCode.BACKEND_UNAVAILABLE.value,
                    "message": "simulated unavailable",
                    "details": {},
                },
            )

    failed = read_context(
        target_scope="issue:13-rollback",
        artifacts=[_artifact()],
        path=ConsumerPath.AGENT_BRAIN,
        adapter=BoomAdapter(invoke_fn=lambda *_a, **_k: None, verify_pin=False),
    )
    assert failed.ok is False
    assert failed.error["code"] == "backend_unavailable"

    # Explicit rollback selection — not silent fallback, not git revert.
    assert rollback_to_legacy() is ConsumerPath.LEGACY
    recovered = read_context(
        target_scope="issue:13-rollback",
        artifacts=[_artifact()],
        path=ConsumerPath.LEGACY,
    )
    assert recovered.ok is True
    assert recovered.path == "legacy"


def test_policy_stays_outside_agent_brain_on_legacy() -> None:
    with pytest.raises(ConsumerError) as exc:
        LegacyContextPath().context_read(target_scope="live-trade", artifacts=[_artifact()])
    assert exc.value.code is ConsumerErrorCode.POLICY_BLOCKED
