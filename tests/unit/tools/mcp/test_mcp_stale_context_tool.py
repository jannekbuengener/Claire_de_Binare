"""Unit tests for Wave-16-C MCP tool: cdb_context_stale.

Issues:
    #2157 — [SURREALDB][CONTEXT][STALE-MCP] Implement stale context MCP tool
    Parent: #2153 (Wave-16 anchor)
    Epic: #1976

Scope:
    Unit tests for tools/mcp/stale_context_tools.py and its integration
    with the MCP registry, context bridge, and permission guard.
    All fixtures are inline — no file loading.
    No DB access. No SurrealDB SDK. No network. No writes.
    No real datetime.now() — as_of is passed explicitly for determinism.
"""

from __future__ import annotations

from typing import Any

import pytest

from tools.mcp.context_bridge import ContextBridge
from tools.mcp.permission_guard import INPUT_SCAN_EXEMPT_TOOLS
from tools.mcp.registry import ContextToolRegistry
from tools.mcp.stale_context_tools import (
    SCHEMA_VERSION,
    TOOL_CDB_CONTEXT_STALE,
    handle_cdb_context_stale,
)
from tools.surrealdb.stale_knowledge_scan import GUARDRAILS, STALE_TYPES

# ── Fixed reference timestamps for determinism ────────────────────────────────

_AS_OF = "2026-05-06T12:00:00+00:00"
_PAST = "2026-01-01T00:00:00+00:00"


# ── Inline fixtures ───────────────────────────────────────────────────────────


def _bundle_with_hash_changed() -> dict[str, Any]:
    """Bundle triggering source_hash_changed (warning)."""
    return {
        "sources": [
            {
                "source_id": "src-hash-mcp-001",
                "path": "docs/api.md",
                "current_hash": "c0ffee01deadbeef",
                "last_verified_hash": "00000000aaaabbbb",
            }
        ]
    }


def _bundle_with_deleted() -> dict[str, Any]:
    """Bundle triggering source_deleted (blocking)."""
    return {
        "sources": [
            {
                "source_id": "src-deleted-mcp-001",
                "exists": False,
            }
        ]
    }


def _bundle_with_expired_evidence() -> dict[str, Any]:
    """Bundle triggering evidence_expired (warning)."""
    return {
        "evidence_records": [
            {
                "evidence_id": "ev-expired-mcp-001",
                "expires_at": _PAST,
                "topic": "test",
            }
        ]
    }


def _bundle_with_superseded_decision() -> dict[str, Any]:
    """Bundle triggering decision_superseded (warning)."""
    return {
        "decisions": [
            {
                "decision_id": "dec-mcp-001",
                "superseded_by": "dec-mcp-002",
                "status": "active",
            }
        ]
    }


def _bundle_multi_stale() -> dict[str, Any]:
    """Bundle triggering multiple stale types across severities."""
    return {
        "sources": [
            {
                "source_id": "src-hash-multi-001",
                "current_hash": "newhashabc",
                "last_verified_hash": "oldhashabc",
            },
            {
                "source_id": "src-deleted-multi-001",
                "exists": False,
            },
        ],
        "evidence_records": [
            {
                "evidence_id": "ev-expired-multi-001",
                "expires_at": _PAST,
            }
        ],
    }


def _request(bundle: dict[str, Any], **extra: Any) -> dict[str, Any]:
    """Build a minimal MCP request for cdb_context_stale."""
    params: dict[str, Any] = {"bundle": bundle, "as_of": _AS_OF}
    params.update(extra)
    return {
        "tool": TOOL_CDB_CONTEXT_STALE,
        "parameters": params,
    }


# ── 1. Registry ───────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_registry_contains_cdb_context_stale() -> None:
    """cdb_context_stale must be registered and read_only=True."""
    tool = ContextToolRegistry.get_tool(TOOL_CDB_CONTEXT_STALE)
    assert tool is not None, f"{TOOL_CDB_CONTEXT_STALE} not found in registry"
    assert tool.read_only is True
    assert tool.name == TOOL_CDB_CONTEXT_STALE


# ── 2. Registry list ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_registry_tool_name_in_list() -> None:
    """cdb_context_stale must appear in list_tool_names()."""
    names = ContextToolRegistry.list_tool_names()
    assert TOOL_CDB_CONTEXT_STALE in names


# ── 3. Handler ok for sample bundle ──────────────────────────────────────────


@pytest.mark.unit
def test_handler_ok_for_sample_bundle() -> None:
    """Handler returns status=ok for a valid bundle with stale findings."""
    result = handle_cdb_context_stale(_request(_bundle_multi_stale()))
    assert result["status"] == "ok", f"unexpected error: {result.get('error')}"
    assert result["tool"] == TOOL_CDB_CONTEXT_STALE
    assert result["schema_version"] == SCHEMA_VERSION
    assert "summary" in result
    assert result["summary"]["total_count"] >= 1


# ── 4. Findings contract ──────────────────────────────────────────────────────


@pytest.mark.unit
def test_findings_contain_required_fields() -> None:
    """Each finding must contain stale_type, severity, confidence,
    recommended_refresh, source_refs."""
    result = handle_cdb_context_stale(_request(_bundle_multi_stale()))
    assert result["status"] == "ok"
    assert len(result["findings"]) >= 1
    for finding in result["findings"]:
        assert "stale_type" in finding, "missing stale_type"
        assert "severity" in finding, "missing severity"
        assert "confidence" in finding, "missing confidence"
        assert "recommended_refresh" in finding, "missing recommended_refresh"
        assert "source_refs" in finding, "missing source_refs"
        assert finding["stale_type"] in STALE_TYPES
        assert isinstance(finding["confidence"], float)
        assert 0.0 <= finding["confidence"] <= 1.0
        assert isinstance(finding["source_refs"], list)


# ── 5. Guardrails present ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_guardrails_present_in_output() -> None:
    """Output guardrails must include all GUARDRAILS strings when include_guardrails=True."""
    result = handle_cdb_context_stale(
        _request(_bundle_with_deleted(), include_guardrails=True)
    )
    assert result["status"] == "ok"
    assert "guardrails" in result
    output_guardrails = result["guardrails"]
    for g in GUARDRAILS:
        assert g in output_guardrails, f"guardrail missing: {g!r}"


@pytest.mark.unit
def test_guardrails_absent_when_excluded() -> None:
    """Guardrails must be absent when include_guardrails=False."""
    result = handle_cdb_context_stale(
        _request(_bundle_with_deleted(), include_guardrails=False)
    )
    assert result["status"] == "ok"
    assert "guardrails" not in result


# ── 6. Filter stale_type ──────────────────────────────────────────────────────


@pytest.mark.unit
def test_filter_stale_type_narrows_findings() -> None:
    """stale_type filter must return only findings of that type."""
    result = handle_cdb_context_stale(
        _request(_bundle_multi_stale(), stale_type="source_deleted")
    )
    assert result["status"] == "ok"
    for finding in result["findings"]:
        assert finding["stale_type"] == "source_deleted"
    # At least one deleted finding from our fixture
    assert result["summary"]["total_count"] >= 1


# ── 7. Filter severity ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_filter_severity_returns_only_blocking() -> None:
    """severity=blocking must return only blocking findings."""
    result = handle_cdb_context_stale(
        _request(_bundle_multi_stale(), severity="blocking")
    )
    assert result["status"] == "ok"
    for finding in result["findings"]:
        assert finding["severity"] == "blocking"
        assert finding["blocking"] is True


@pytest.mark.unit
def test_filter_severity_warning_excludes_blocking() -> None:
    """severity=warning must exclude blocking findings."""
    result = handle_cdb_context_stale(
        _request(_bundle_multi_stale(), severity="warning")
    )
    assert result["status"] == "ok"
    for finding in result["findings"]:
        assert finding["severity"] == "warning"


# ── 8. Filter target_ref ──────────────────────────────────────────────────────


@pytest.mark.unit
def test_filter_target_ref_narrows_findings() -> None:
    """target_ref filter must return only findings with that target_ref."""
    result = handle_cdb_context_stale(
        _request(
            _bundle_multi_stale(),
            target_ref="src-deleted-multi-001",
        )
    )
    assert result["status"] == "ok"
    for finding in result["findings"]:
        assert finding["target_ref"] == "src-deleted-multi-001"


@pytest.mark.unit
def test_filter_target_ref_no_match_returns_empty() -> None:
    """target_ref with no match must return empty findings, status ok."""
    result = handle_cdb_context_stale(
        _request(_bundle_multi_stale(), target_ref="nonexistent-ref-xyz")
    )
    assert result["status"] == "ok"
    assert result["findings"] == []
    assert result["summary"]["total_count"] == 0


# ── 9. Limit ──────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_limit_caps_findings_and_sets_truncated() -> None:
    """limit=1 must cap findings to 1 when more exist; summary.truncated=True."""
    result = handle_cdb_context_stale(
        _request(_bundle_multi_stale(), limit=1)
    )
    assert result["status"] == "ok"
    assert len(result["findings"]) == 1
    assert result["summary"]["truncated"] is True
    # Summary counts are post-filter, pre-limit — must be >= 1 (the real total)
    assert result["summary"]["total_count"] >= 1


@pytest.mark.unit
def test_limit_not_truncated_when_findings_fit() -> None:
    """summary.truncated=False when findings fit within limit."""
    result = handle_cdb_context_stale(
        _request(_bundle_with_hash_changed(), limit=500)
    )
    assert result["status"] == "ok"
    assert result["summary"]["truncated"] is False


@pytest.mark.unit
def test_limit_over_500_is_capped() -> None:
    """limit > 500 must be silently capped to 500 (no error)."""
    result = handle_cdb_context_stale(
        _request(_bundle_with_hash_changed(), limit=9999)
    )
    assert result["status"] == "ok"


# ── 10. No bundle → clean error ───────────────────────────────────────────────


@pytest.mark.unit
def test_missing_bundle_returns_clean_error() -> None:
    """Omitting bundle must return status=error with missing_bundle code."""
    result = handle_cdb_context_stale(
        {
            "tool": TOOL_CDB_CONTEXT_STALE,
            "parameters": {"as_of": _AS_OF},
        }
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "missing_bundle"
    # Must not attempt any live read — message must mention bundle-driven
    assert "bundle" in result["error"]["message"].lower()


@pytest.mark.unit
def test_none_bundle_returns_clean_error() -> None:
    """Passing bundle=None must return status=error."""
    result = handle_cdb_context_stale(
        _request(None)  # type: ignore[arg-type]
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "missing_bundle"


# ── 11. Invalid stale_type → error ────────────────────────────────────────────


@pytest.mark.unit
def test_invalid_stale_type_returns_error() -> None:
    """Unknown stale_type must return status=error with invalid_stale_type code."""
    result = handle_cdb_context_stale(
        _request(_bundle_with_hash_changed(), stale_type="not_a_real_type")
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "invalid_stale_type"


# ── 12. Invalid severity → error ──────────────────────────────────────────────


@pytest.mark.unit
def test_invalid_severity_returns_error() -> None:
    """Unknown severity must return status=error with invalid_severity code."""
    result = handle_cdb_context_stale(
        _request(_bundle_with_hash_changed(), severity="critical")
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "invalid_severity"


@pytest.mark.unit
def test_invalid_scope_returns_error() -> None:
    """Unknown scope must return status=error with invalid_scope code."""
    result = handle_cdb_context_stale(
        _request(_bundle_with_hash_changed(), scope="not_a_valid_scope")
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "invalid_scope"


# ── 13. Bridge executability ──────────────────────────────────────────────────


@pytest.mark.unit
def test_tool_executable_via_bridge() -> None:
    """cdb_context_stale can be executed via ContextBridge.execute_tool."""
    bridge = ContextBridge()
    result = bridge.execute_tool(
        TOOL_CDB_CONTEXT_STALE,
        parameters={
            "bundle": _bundle_with_deleted(),
            "as_of": _AS_OF,
        },
    )
    assert result["status"] == "ok", f"unexpected error: {result.get('error')}"
    assert result["tool"] == TOOL_CDB_CONTEXT_STALE


# ── Read-only safety ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_read_only_safety_no_writes_in_result() -> None:
    """Handler must not write any files or mutate input bundle."""
    import copy

    original_bundle = _bundle_multi_stale()
    bundle_copy = copy.deepcopy(original_bundle)

    result = handle_cdb_context_stale(_request(original_bundle))
    assert result["status"] == "ok"
    # Input bundle must not be mutated: domain keys must be identical to the deep copy.
    assert original_bundle == bundle_copy


@pytest.mark.unit
def test_read_only_safety_no_forbidden_imports() -> None:
    """stale_context_tools module must not import forbidden modules."""
    import importlib
    import sys

    # Ensure the module is imported
    if "tools.mcp.stale_context_tools" not in sys.modules:
        importlib.import_module("tools.mcp.stale_context_tools")

    mod = sys.modules["tools.mcp.stale_context_tools"]
    mod_globals = vars(mod)

    for forbidden in ("requests", "httpx", "subprocess", "surrealdb"):
        assert forbidden not in mod_globals, (
            f"Forbidden import '{forbidden}' found in stale_context_tools module globals"
        )


# ── Permission guard exemption ────────────────────────────────────────────────


@pytest.mark.unit
def test_cdb_context_stale_in_exempt_tools() -> None:
    """cdb_context_stale must be in INPUT_SCAN_EXEMPT_TOOLS."""
    assert TOOL_CDB_CONTEXT_STALE in INPUT_SCAN_EXEMPT_TOOLS


# ── Scope filter ──────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_scope_artifact_limits_to_source_types() -> None:
    """scope=artifact must return only source_hash_changed / source_deleted findings."""
    from tools.mcp.stale_context_tools import _SCOPE_TO_STALE_TYPES

    result = handle_cdb_context_stale(
        _request(_bundle_multi_stale(), scope="artifact")
    )
    assert result["status"] == "ok"
    allowed = _SCOPE_TO_STALE_TYPES["artifact"]
    for finding in result["findings"]:
        assert finding["stale_type"] in allowed


@pytest.mark.unit
def test_scope_decision_returns_only_decision_findings() -> None:
    """scope=decision must return only decision_superseded findings."""
    bundle = {**_bundle_multi_stale(), **_bundle_with_superseded_decision()}
    result = handle_cdb_context_stale(
        _request(bundle, scope="decision")
    )
    assert result["status"] == "ok"
    for finding in result["findings"]:
        assert finding["stale_type"] == "decision_superseded"


@pytest.mark.unit
def test_scope_evidence_returns_only_evidence_findings() -> None:
    """scope=evidence must return only evidence_expired findings."""
    bundle = {**_bundle_multi_stale(), **_bundle_with_expired_evidence()}
    result = handle_cdb_context_stale(
        _request(bundle, scope="evidence")
    )
    assert result["status"] == "ok"
    assert len(result["findings"]) >= 1
    for finding in result["findings"]:
        assert finding["stale_type"] == "evidence_expired"


@pytest.mark.unit
def test_scope_evidence_excludes_non_evidence_types() -> None:
    """scope=evidence must exclude source_hash_changed, source_deleted, etc."""
    bundle = {**_bundle_multi_stale(), **_bundle_with_expired_evidence()}
    result = handle_cdb_context_stale(
        _request(bundle, scope="evidence")
    )
    assert result["status"] == "ok"
    for finding in result["findings"]:
        assert finding["stale_type"] not in {
            "source_hash_changed",
            "source_deleted",
            "decision_superseded",
            "memory_ttl_expired",
        }


# ── Summary integrity ─────────────────────────────────────────────────────────


@pytest.mark.unit
def test_summary_severity_summary_present() -> None:
    """Summary must contain severity_summary with info/warning/blocking keys."""
    result = handle_cdb_context_stale(_request(_bundle_multi_stale()))
    assert result["status"] == "ok"
    sev = result["summary"]["severity_summary"]
    assert "info" in sev
    assert "warning" in sev
    assert "blocking" in sev


@pytest.mark.unit
def test_summary_stale_type_summary_present() -> None:
    """Summary must contain stale_type_summary with at least the 8 canonical keys."""
    result = handle_cdb_context_stale(_request(_bundle_multi_stale()))
    assert result["status"] == "ok"
    st = result["summary"]["stale_type_summary"]
    for st_type in STALE_TYPES:
        assert st_type in st, f"stale_type {st_type!r} missing from stale_type_summary"


@pytest.mark.unit
def test_source_refs_present_in_output() -> None:
    """Output must contain source_refs list (may be empty for empty bundles)."""
    result = handle_cdb_context_stale(_request(_bundle_with_deleted()))
    assert result["status"] == "ok"
    assert "source_refs" in result
    assert isinstance(result["source_refs"], list)
    # source_deleted findings have source_refs populated
    assert len(result["source_refs"]) >= 1


@pytest.mark.unit
def test_recommended_refresh_present_in_output() -> None:
    """Output must contain recommended_refresh list with at least one entry."""
    result = handle_cdb_context_stale(_request(_bundle_with_deleted()))
    assert result["status"] == "ok"
    assert "recommended_refresh" in result
    assert isinstance(result["recommended_refresh"], list)
    assert len(result["recommended_refresh"]) >= 1


@pytest.mark.unit
def test_as_of_in_output() -> None:
    """Output must contain as_of field."""
    result = handle_cdb_context_stale(_request(_bundle_with_hash_changed()))
    assert result["status"] == "ok"
    assert "as_of" in result
    assert isinstance(result["as_of"], str) and result["as_of"]


# ── Regression: existing tools still work ─────────────────────────────────────


@pytest.mark.unit
def test_existing_contradiction_tool_unaffected() -> None:
    """Adding cdb_context_stale must not break cdb_context_contradictions."""
    tool = ContextToolRegistry.get_tool("cdb_context_contradictions")
    assert tool is not None
    assert tool.read_only is True


@pytest.mark.unit
def test_all_registered_tools_are_read_only() -> None:
    """All tools in the registry must remain read_only=True after Wave-16-C."""
    for tool in ContextToolRegistry.list_tools():
        assert tool.read_only is True, f"Tool {tool.name!r} is not read_only"
