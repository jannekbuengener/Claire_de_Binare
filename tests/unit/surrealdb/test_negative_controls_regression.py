"""Regression suite for write-intent and mutation negative controls (#2854)."""

from __future__ import annotations

import json

import pytest

from tests.fixtures.surrealdb.negative_controls_matrix import (
    NEGATIVE_CONTROL_MATRIX,
    NegativeControlCase,
)
from tools.mcp.context_bridge import ContextBridge
from tools.mcp.memory_write_intent_tools import (
    MUTATION_ALLOWED,
    handle_cdb_context_memory_write_intent,
)
from tools.surrealdb import negative_controls as nc
from tools.surrealdb.db_record_evidence_contract import (
    build_example_claim,
    classify_trust,
    compute_determinism_hash,
)
from tools.surrealdb.memory_write_gate import (
    PERSIST_ALLOWED,
    PERSIST_ENV_VAR,
    approved_for_persist,
)
from tools.surrealdb.memory_write_gate import (
    MemoryWriteAuthorization,
    PROOF_SCOPE_HGW_2759,
)
from tools.surrealdb.scope_drift_firewall import scan_scope_drift_v1
from tools.surrealdb.negative_controls_matrix import case_by_id

pytestmark = pytest.mark.unit


def _valid_record(**overrides) -> dict:
    base: dict = {
        "scope": "agent:TEST/cursor",
        "namespace": "session",
        "memory_type": "working_memory",
        "content": "Negative control regression record",
        "source_refs": ["docs/AGENTS.md@abc123"],
        "evidence_refs": ["ev-2854"],
        "confidence": 0.9,
        "ttl": 3600,
        "expires_at": "2026-05-30T00:00:00+00:00",
        "created_by": "cursor-agent-v1",
        "created_at": "2026-05-29T04:00:00+00:00",
    }
    base.update(overrides)
    return base


def _valid_auth() -> dict:
    return {
        "human_go_token": "GO-2026-05-29-slice5",
        "authorized_by": "jannekbuengener",
        "authorized_at": "2026-05-29T11:00:00+00:00",
        "scope": "agent:TEST/cursor",
        "target_issue": "2854",
        "evidence_refs": ["github:issue/2854"],
        "operation": "create",
    }


def _hgw_auth(**overrides) -> MemoryWriteAuthorization:
    base = dict(
        human_go_token="GO-2026-05-31-hgw",
        authorized_by="jannekbuengener",
        authorized_at="2026-05-31T12:00:00+00:00",
        scope=f"memory_write_path_t4:{PROOF_SCOPE_HGW_2759}",
        target_issue="2759",
        evidence_refs=("github:issue/2759",),
        operation="create",
    )
    base.update(overrides)
    return MemoryWriteAuthorization(**base)


def _invoke_write_intent(case: NegativeControlCase) -> dict:
    params: dict = {"record": _valid_record()}
    if case.include_authorization:
        params["authorization"] = _valid_auth()
    if case.operation_mode:
        params["operation_mode"] = case.operation_mode
    if case.mutation_flag:
        params[case.mutation_flag] = True
    if case.parameters:
        params.update(case.parameters)
    return handle_cdb_context_memory_write_intent(
        {"tool": "cdb_context_memory_write_intent", "parameters": params}
    )


@pytest.mark.unit
def test_safety_defaults_off() -> None:
    assert nc.assert_safety_defaults_off() == []
    assert PERSIST_ALLOWED is False
    assert MUTATION_ALLOWED is False


@pytest.mark.unit
def test_negative_control_matrix_summary_machine_readable() -> None:
    summary = nc.negative_control_matrix_summary()
    assert summary["schema"] == "negative-controls-matrix/v1"
    assert summary["issue_ref"] == "2854"
    assert len(summary["cases"]) == len(NEGATIVE_CONTROL_MATRIX)
    assert summary["safety_flags"]["PERSIST_ALLOWED"] is False
    assert summary["safety_flags"]["MUTATION_ALLOWED"] is False


@pytest.mark.unit
@pytest.mark.parametrize(
    "case_id",
    [c.case_id for c in NEGATIVE_CONTROL_MATRIX if c.category == "write_intent"],
)
def test_write_intent_matrix_cases(case_id: str) -> None:
    case = case_by_id(case_id)
    response = _invoke_write_intent(case)
    if case.operation_mode == "dry_run" and case.include_authorization:
        assert response["status"] == "ok"
        assert response["result"]["gate_status"] == "approved_dry_run"
        assert response["result"]["persist_allowed"] is False
    elif not case.include_authorization:
        assert response["status"] == "ok"
        assert response["result"]["gate_status"] == "blocked_no_authorization"
    else:
        assert response["status"] == "refused"
    safe, issues = nc.refusal_output_is_safe(response)
    assert safe, issues


@pytest.mark.unit
@pytest.mark.parametrize(
    "case_id",
    [c.case_id for c in NEGATIVE_CONTROL_MATRIX if c.category == "mutation_gate"],
)
def test_mutation_gate_matrix_cases(case_id: str) -> None:
    case = case_by_id(case_id)
    response = _invoke_write_intent(case)
    if case.parameters and "query" in case.parameters:
        assert response["status"] == "error"
        assert response["error"]["code"] == "unsafe_input"
    else:
        assert response["status"] == "error"
        assert response["error"]["code"] == "mutation_blocked_by_default"
    safe, _ = nc.refusal_output_is_safe(response)
    assert safe


@pytest.mark.unit
def test_productive_persist_blocked_without_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(PERSIST_ENV_VAR, raising=False)
    assert approved_for_persist(_hgw_auth(), human_go_tier="HG-W") is False
    assert PERSIST_ALLOWED is False


@pytest.mark.unit
def test_fake_brain_source_classified_invalid_fake_db() -> None:
    claim = build_example_claim(
        record_source="surrealdb-local",
        trust_classification="invalid_fake_db",
        record_ids=[],
        record_hashes_or_content_fingerprints=[],
        caller_evidence={"brain_source": "surrealdb-local"},
        limitations=["caller brain_source ignored"],
    )
    claim["determinism_hash"] = compute_determinism_hash(claim)
    assert classify_trust(claim) == "invalid_fake_db"


@pytest.mark.unit
def test_scope_drift_blocks_write_intent_without_go() -> None:
    bundle = {
        "human_go_token": "",
        "generated_findings": [
            {
                "write_intent": True,
                "content": "persist this finding to agent_memory",
            }
        ],
    }
    result = scan_scope_drift_v1(bundle)
    types = {f.drift_type for f in result.findings}
    assert "unauthorized_write_intent" in types


@pytest.mark.unit
def test_harness_classify_bridge_refused_is_pass() -> None:
    from tools.surrealdb import context_live_invocation_harness as harness

    result = {
        "status": "refused",
        "code": "agent_memory_write_not_activated",
    }
    assert (
        harness.classify_tool_result("cdb_context_memory_write_intent", result)
        == "PASS"
    )
    assert (
        nc.classify_memory_write_intent_negative_control(
            result, invocation_path="bridge"
        )
        == "PASS"
    )


@pytest.mark.unit
def test_harness_classify_mcp_blocked_safety_not_fail() -> None:
    result = {
        "status": "error",
        "error": {
            "code": "blocked_safety",
            "message": "Smart Mode blocked write-intent MCP call",
        },
    }
    assert (
        nc.classify_memory_write_intent_negative_control(result, invocation_path="mcp")
        == "BLOCKED_SAFETY"
    )


@pytest.mark.unit
def test_bridge_execute_write_intent_refusal_no_secrets() -> None:
    bridge = ContextBridge()
    response = bridge.execute_tool(
        "cdb_context_memory_write_intent",
        {
            "record": _valid_record(),
            "authorization": _valid_auth(),
            "operation_mode": "agent_memory_write",
        },
    )
    assert response["status"] == "refused"
    assert response["code"] == "agent_memory_write_not_activated"
    serialized = json.dumps(response)
    assert "GO-2026-05-29-slice5" not in serialized
    assert '"human_go_token"' not in serialized


@pytest.mark.unit
def test_matrix_case_mcp_smart_mode_blocked_safety_entry() -> None:
    case = case_by_id("mcp_smart_mode_blocked_safety")
    assert case.expected_verdict == "BLOCKED_SAFETY"
    simulated = {
        "status": "error",
        "error": {"code": case.mcp_simulated_code, "message": "Smart Mode policy"},
    }
    assert (
        nc.classify_memory_write_intent_negative_control(
            simulated, invocation_path="mcp"
        )
        == case.expected_verdict
    )
