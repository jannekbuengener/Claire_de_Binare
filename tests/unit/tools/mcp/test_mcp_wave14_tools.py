"""Unit tests for Wave-14 MCP tools: evidence_resolve, claim_resolve, memory_get, trust_summary.

Issues:
    #2126 — Add tests and fixtures for evidence, decision, and memory retrieval
    #2123 — Implement evidence resolve MCP tool v1
    #2125 — Implement scoped memory read MCP tool v1
    Parent: #2115 (Wave-14), Epic: #1976
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.mcp.context_evidence_memory_tools import (
    TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
    TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
    TOOL_CDB_CONTEXT_MEMORY_GET,
    TOOL_CDB_CONTEXT_TRUST_SUMMARY,
    handle_cdb_context_evidence_resolve,
    handle_cdb_context_claim_resolve,
    handle_cdb_context_memory_get,
    handle_cdb_context_trust_summary,
)


FIXTURE_PATH = Path("tests/fixtures/surrealdb/wave14/wave14_v1.json")


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


# ── Evidence Resolve MCP ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_mcp_evidence_resolve_ok() -> None:
    fx = _load_fixture()
    request = {
        "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
        "parameters": {
            "mode": "by_artifact",
            "artifact": "tools/surrealdb/context_stop_resolver.py",
            "evidence_records": fx["evidence_records"],
        },
    }
    result = handle_cdb_context_evidence_resolve(request)
    assert result["status"] == "ok"
    assert result["tool"] == TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE
    assert result["metadata"]["read_only"] is True
    matched = result["result"]["matched_evidence"]
    assert any(e["evidence_id"] == "ev-001" for e in matched)


@pytest.mark.unit
def test_mcp_evidence_resolve_no_records() -> None:
    result = handle_cdb_context_evidence_resolve({
        "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
        "parameters": {
            "mode": "by_artifact",
            "artifact": "some/path",
        },
    })
    assert result["status"] == "error"
    assert result["error"]["code"] == "missing_evidence_records"


@pytest.mark.unit
def test_mcp_evidence_resolve_wrong_tool() -> None:
    result = handle_cdb_context_evidence_resolve({
        "tool": "wrong_tool",
        "parameters": {},
    })
    assert result["status"] == "error"
    assert result["error"]["code"] == "invalid_tool"


@pytest.mark.unit
def test_mcp_evidence_resolve_no_echtgeld_go() -> None:
    fx = _load_fixture()
    result = handle_cdb_context_evidence_resolve({
        "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
        "parameters": {
            "mode": "by_run_id",
            "run_id": "run-2024-001",
            "evidence_records": fx["evidence_records"],
        },
    })
    assert result["status"] == "ok"
    assert result["result"]["approval_semantics"]["no_echtgeld_go"] is True


# ── Claim Resolve MCP ─────────────────────────────────────────────────────────


@pytest.mark.unit
def test_mcp_claim_resolve_ok() -> None:
    fx = _load_fixture()
    request = {
        "tool": TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
        "parameters": {
            "mode": "by_topic",
            "topic": "stop_conditions",
            "claim_records": fx["claim_records"],
        },
    }
    result = handle_cdb_context_claim_resolve(request)
    assert result["status"] == "ok"
    assert result["tool"] == TOOL_CDB_CONTEXT_CLAIM_RESOLVE
    matched = result["result"]["matched_claims"]
    assert any(c["claim_id"] == "claim-001" for c in matched)


@pytest.mark.unit
def test_mcp_claim_resolve_no_records() -> None:
    result = handle_cdb_context_claim_resolve({
        "tool": TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
        "parameters": {"mode": "by_topic", "topic": "x"},
    })
    assert result["status"] == "error"
    assert result["error"]["code"] == "missing_claim_records"


@pytest.mark.unit
def test_mcp_claim_resolve_disputed_surfaces() -> None:
    fx = _load_fixture()
    result = handle_cdb_context_claim_resolve({
        "tool": TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
        "parameters": {
            "mode": "by_status",
            "status": "disputed",
            "claim_records": fx["claim_records"],
        },
    })
    assert result["status"] == "ok"
    assert "claim-004" in result["result"]["disputed_claim_ids"]


@pytest.mark.unit
def test_mcp_claim_resolve_no_echtgeld_go() -> None:
    fx = _load_fixture()
    result = handle_cdb_context_claim_resolve({
        "tool": TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
        "parameters": {
            "mode": "by_status",
            "status": "supported",
            "claim_records": fx["claim_records"],
        },
    })
    assert result["status"] == "ok"
    assert result["result"]["approval_semantics"]["no_echtgeld_go"] is True


# ── Memory Get MCP ────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_mcp_memory_get_ok() -> None:
    fx = _load_fixture()
    result = handle_cdb_context_memory_get({
        "tool": TOOL_CDB_CONTEXT_MEMORY_GET,
        "parameters": {
            "mode": "by_scope",
            "scope": "wave14",
            "memory_records": fx["memory_records"],
        },
    })
    assert result["status"] == "ok"
    assert result["tool"] == TOOL_CDB_CONTEXT_MEMORY_GET
    ids = {m["memory_id"] for m in result["result"]["matched_memory"]}
    assert "mem-001" in ids
    assert "mem-002" in ids


@pytest.mark.unit
def test_mcp_memory_get_no_records() -> None:
    result = handle_cdb_context_memory_get({
        "tool": TOOL_CDB_CONTEXT_MEMORY_GET,
        "parameters": {"mode": "by_scope", "scope": "x"},
    })
    assert result["status"] == "error"
    assert result["error"]["code"] == "missing_memory_records"


@pytest.mark.unit
def test_mcp_memory_get_stale_flagged() -> None:
    fx = _load_fixture()
    result = handle_cdb_context_memory_get({
        "tool": TOOL_CDB_CONTEXT_MEMORY_GET,
        "parameters": {
            "mode": "by_scope",
            "scope": "wave10",
            "memory_records": fx["memory_records"],
        },
    })
    assert result["status"] == "ok"
    assert "mem-003" in result["result"]["stale_memory_ids"]


@pytest.mark.unit
def test_mcp_memory_get_no_echtgeld_go() -> None:
    fx = _load_fixture()
    result = handle_cdb_context_memory_get({
        "tool": TOOL_CDB_CONTEXT_MEMORY_GET,
        "parameters": {
            "mode": "by_scope",
            "scope": "wave14",
            "memory_records": fx["memory_records"],
        },
    })
    assert result["status"] == "ok"
    assert result["result"]["approval_semantics"]["no_echtgeld_go"] is True
    assert result["result"]["approval_semantics"]["no_write"] is True


# ── Trust Summary MCP ─────────────────────────────────────────────────────────


@pytest.mark.unit
def test_mcp_trust_summary_ok() -> None:
    result = handle_cdb_context_trust_summary({
        "tool": TOOL_CDB_CONTEXT_TRUST_SUMMARY,
        "parameters": {
            "scope": "wave14",
            "topic": "context_tools",
        },
    })
    assert result["status"] == "ok"
    assert result["tool"] == TOOL_CDB_CONTEXT_TRUST_SUMMARY
    assert result["result"]["trust_level"] in ("blocked", "weak", "acceptable", "strong")


@pytest.mark.unit
def test_mcp_trust_summary_missing_scope() -> None:
    result = handle_cdb_context_trust_summary({
        "tool": TOOL_CDB_CONTEXT_TRUST_SUMMARY,
        "parameters": {},
    })
    assert result["status"] == "error"
    assert result["error"]["code"] == "missing_scope"


@pytest.mark.unit
def test_mcp_trust_summary_blocked_on_missing_evidence() -> None:
    result = handle_cdb_context_trust_summary({
        "tool": TOOL_CDB_CONTEXT_TRUST_SUMMARY,
        "parameters": {
            "scope": "wave14",
            "evidence_result": {
                "evidence_summary": {"overall_strength": "blocking_missing"},
                "blocking_missing_ids": ["ev-004"],
                "stale_evidence_ids": [],
            },
        },
    })
    assert result["status"] == "ok"
    assert result["result"]["trust_level"] == "blocked"


@pytest.mark.unit
def test_mcp_trust_summary_no_echtgeld_go() -> None:
    result = handle_cdb_context_trust_summary({
        "tool": TOOL_CDB_CONTEXT_TRUST_SUMMARY,
        "parameters": {"scope": "wave14"},
    })
    assert result["status"] == "ok"
    assert result["result"]["approval_semantics"]["no_echtgeld_go"] is True
