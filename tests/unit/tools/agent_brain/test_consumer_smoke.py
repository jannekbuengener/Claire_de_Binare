"""Real Claire consumer smoke against the immutable Agent Brain pin (#13).

Requires ``requirements-agent-brain.txt`` (git tag ``v0.2.0``) to be installed.
Exercises public ``agent_brain.protocol`` only — no private Agent Brain imports.
"""

from __future__ import annotations

import importlib

import pytest

from tools.agent_brain.adapter import AgentBrainAdapter
from tools.agent_brain.consumer import read_context, rollback_to_legacy
from tools.agent_brain.errors import ConsumerError, ConsumerErrorCode
from tools.agent_brain.path_selection import ConsumerPath
from tools.agent_brain.pin import (
    PINNED_AGENT_BRAIN_VERSION,
    PINNED_REQUIREMENT,
    verify_runtime_pin,
)

pytestmark = pytest.mark.unit


def _require_pinned_agent_brain() -> None:
    try:
        importlib.import_module("agent_brain.protocol")
    except ImportError as exc:  # pragma: no cover - environment gate
        pytest.skip(f"agent-brain not installed ({PINNED_REQUIREMENT}): {exc}")


def test_exact_pin_and_runtime_version_match() -> None:
    _require_pinned_agent_brain()
    runtime = verify_runtime_pin()
    assert runtime == PINNED_AGENT_BRAIN_VERSION

    import agent_brain
    from agent_brain.protocol import invoke

    # Public surface only.
    response = invoke("version")
    assert response.ok is True
    assert response.data is not None
    assert response.data["agent_brain_version"] == PINNED_AGENT_BRAIN_VERSION
    assert agent_brain.__version__ == PINNED_AGENT_BRAIN_VERSION


def test_wrong_expected_version_fail_closed() -> None:
    _require_pinned_agent_brain()
    with pytest.raises(ConsumerError) as exc:
        verify_runtime_pin(expected="9.9.9")
    assert exc.value.code is ConsumerErrorCode.CONTRACT_VERSION_MISMATCH
    assert exc.value.details["expected"] == "9.9.9"
    assert exc.value.details["runtime"] == PINNED_AGENT_BRAIN_VERSION


def test_consumer_smoke_public_surface_context_read() -> None:
    _require_pinned_agent_brain()
    adapter = AgentBrainAdapter()
    health = adapter.health()
    assert health.ok is True
    caps = adapter.capabilities()
    assert caps.ok is True

    artifact = {
        "ref": {
            "schema_version": "artifact-ref/v1",
            "artifact_id": "claire-smoke-1",
            "source_id": "repo",
            "source_path": "AGENTS.md",
            "source_hash": "claire-cutover-smoke",
        },
        "artifact_type": "doc",
        "summary": "claire consumer smoke",
        "payload": {"note": "read-only"},
    }
    result = adapter.context_read(
        target_scope="claire:agent-brain-cutover-smoke",
        artifacts=[artifact],
    )
    assert result.ok is True
    assert result.path == "agent_brain"
    assert result.data is not None
    assert result.data["claire_policy"]["live_or_echtgeld"] is False
    assert result.agent_brain_version == PINNED_AGENT_BRAIN_VERSION


def test_consumer_smoke_error_shape_and_no_private_imports() -> None:
    _require_pinned_agent_brain()
    adapter = AgentBrainAdapter()
    # Invalid scope / missing store must be structured failure, not empty success.
    failure = adapter._call(  # noqa: SLF001 — intentional protocol error probe
        "memory_read",
        {"scope": None, "as_of": "2026-10-31T12:00:00Z"},
    )
    assert failure.ok is False
    assert failure.error is not None
    assert failure.error["code"] in {
        "capability_unavailable",
        "invalid_scope",
        "backend_unavailable",
        "invalid_input",
    }

    # Cross-repo contract: public protocol module must exist; private shortcut forbidden.
    import agent_brain.protocol as protocol

    assert hasattr(protocol, "invoke")
    with pytest.raises(ImportError):
        importlib.import_module("agent_brain.protocol._private_not_a_module")


def test_dispatch_both_paths_and_rollback() -> None:
    _require_pinned_agent_brain()
    artifact = {
        "artifact_id": "AGENTS.md",
        "artifact_type": "doc",
        "summary": "path switch smoke",
    }
    legacy = read_context(
        target_scope="claire:path-switch",
        artifacts=[artifact],
        path=ConsumerPath.LEGACY,
    )
    assert legacy.ok is True
    assert legacy.path == "legacy"

    brain = read_context(
        target_scope="claire:path-switch",
        artifacts=[
            {
                "ref": {
                    "schema_version": "artifact-ref/v1",
                    "artifact_id": "claire-path-1",
                    "source_id": "repo",
                    "source_path": "AGENTS.md",
                    "source_hash": "path-switch",
                },
                "artifact_type": "doc",
                "summary": "path switch",
                "payload": {},
            }
        ],
        path=ConsumerPath.AGENT_BRAIN,
    )
    assert brain.ok is True
    assert brain.path == "agent_brain"
    assert rollback_to_legacy() is ConsumerPath.LEGACY
