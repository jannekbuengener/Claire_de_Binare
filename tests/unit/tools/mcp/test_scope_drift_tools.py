"""Unit tests for Wave-17-C MCP tool: cdb_context_scope_drift.

Issues:
    #2165 — [SURREALDB][CONTEXT][SCOPE-MCP] Implement scope drift MCP tool
    Parent: #2162 (Wave-17 anchor)
    Epic: #1976

Scope:
    Unit tests for tools/mcp/scope_drift_tools.py and its integration
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
from tools.mcp.scope_drift_tools import (
    SCHEMA_VERSION,
    TOOL_CDB_CONTEXT_SCOPE_DRIFT,
    handle_cdb_context_scope_drift,
)
from tools.surrealdb.scope_drift_firewall import GUARDRAILS

# ── Fixed reference timestamps for determinism ────────────────────────────────

_AS_OF = "2026-05-06T12:00:00+00:00"


# ── Inline bundle fixtures ────────────────────────────────────────────────────


def _bundle_clean() -> dict[str, Any]:
    """Empty bundle — no touched artifacts, no issues — produces zero findings."""
    return {}


def _bundle_path_out_of_scope() -> dict[str, Any]:
    """Bundle with an out-of-scope path → path_out_of_scope (blocking)."""
    return {
        "declared_scope": {
            "target_paths": ["tools/mcp/"],
        },
        "touched_artifacts": [
            {"path": "services/risk/some_file.py"},
        ],
    }


def _bundle_domain_out_of_scope() -> dict[str, Any]:
    """Bundle with a mismatched domain → domain_out_of_scope (warning)."""
    return {
        "declared_scope": {
            "allowed_domains": ["docs"],
        },
        "touched_artifacts": [
            {"path": "services/risk/some_file.py", "surface_type": "runtime"},
        ],
    }


def _bundle_issue_out_of_scope() -> dict[str, Any]:
    """Bundle with an out-of-scope issue ref → issue_out_of_scope (warning)."""
    return {
        "declared_scope": {
            "target_issue": "2165",
        },
        "issue_refs": [
            {"issue_id": "9999"},
        ],
    }


def _bundle_multi() -> dict[str, Any]:
    """Bundle triggering multiple findings of different types and severities."""
    return {
        "declared_scope": {
            "target_paths": ["tools/mcp/"],
            "allowed_domains": ["docs"],
            "target_issue": "2165",
        },
        "touched_artifacts": [
            # path_out_of_scope (blocking) + runtime_surface_touched (blocking)
            {"path": "services/risk/some_file.py", "surface_type": "runtime"},
            # domain_out_of_scope (warning) for a docs-declared scope
            {"path": "tools/mcp/widget.py", "surface_type": "service"},
        ],
        "issue_refs": [
            {"issue_id": "9999"},  # issue_out_of_scope (warning)
        ],
    }


def _bundle_with_write_intent() -> dict[str, Any]:
    """Bundle whose generated_findings contain write-intent keyword without GO token.

    This exercises the unauthorized_write_intent rule (blocking).
    """
    return {
        "generated_findings": [
            {
                "type": "suggestion",
                "content": "git push origin main",
                "source": "agent",
                "write_intent": True,
                "human_go_token": None,
            }
        ]
    }


def _request(bundle: dict[str, Any], **extra: Any) -> dict[str, Any]:
    """Build a minimal MCP request for cdb_context_scope_drift."""
    params: dict[str, Any] = {"bundle": bundle, "as_of": _AS_OF}
    params.update(extra)
    return {
        "tool": TOOL_CDB_CONTEXT_SCOPE_DRIFT,
        "parameters": params,
    }


# ── 1. Registry ───────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_tool_in_registry_is_read_only() -> None:
    """Tool must be registered and read_only=True."""
    tool = ContextToolRegistry.get_tool(TOOL_CDB_CONTEXT_SCOPE_DRIFT)
    assert tool is not None, f"{TOOL_CDB_CONTEXT_SCOPE_DRIFT} not found in registry"
    assert tool.read_only is True
    assert tool.name == TOOL_CDB_CONTEXT_SCOPE_DRIFT


@pytest.mark.unit
def test_tool_in_registry_tool_names() -> None:
    """Tool name appears in registry tool list."""
    names = ContextToolRegistry.list_tool_names()
    assert TOOL_CDB_CONTEXT_SCOPE_DRIFT in names


# ── 2. Bridge ─────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_tool_executable_via_bridge() -> None:
    """Tool can be executed via ContextBridge.execute_tool and returns status ok."""
    bridge = ContextBridge()
    result = bridge.execute_tool(TOOL_CDB_CONTEXT_SCOPE_DRIFT, {"bundle": {}, "as_of": _AS_OF})
    assert isinstance(result, dict)
    assert result.get("status") == "ok", f"expected ok, got: {result}"
    assert result.get("tool") == TOOL_CDB_CONTEXT_SCOPE_DRIFT


# ── 3. Permission guard ───────────────────────────────────────────────────────


@pytest.mark.unit
def test_tool_in_permission_guard_exempt() -> None:
    """Tool must be in INPUT_SCAN_EXEMPT_TOOLS (bundle content contains write-intent keywords)."""
    assert TOOL_CDB_CONTEXT_SCOPE_DRIFT in INPUT_SCAN_EXEMPT_TOOLS


# ── 4. Clean bundle → ok result ───────────────────────────────────────────────


@pytest.mark.unit
def test_clean_bundle_returns_ok() -> None:
    """Empty bundle produces a valid ok response with zero findings."""
    result = handle_cdb_context_scope_drift(_request(_bundle_clean()))
    assert result["status"] == "ok"
    assert result["tool"] == TOOL_CDB_CONTEXT_SCOPE_DRIFT
    assert result["schema_version"] == SCHEMA_VERSION
    assert result["summary"]["total_count"] == 0
    assert result["summary"]["blocking_count"] == 0
    assert result["findings"] == []
    assert isinstance(result["guardrails"], list)
    assert len(result["guardrails"]) > 0


# ── 5. Blocking bundle → blocking findings ────────────────────────────────────


@pytest.mark.unit
def test_blocking_bundle_returns_blocking_findings() -> None:
    """Bundle with out-of-scope path produces a blocking finding."""
    result = handle_cdb_context_scope_drift(_request(_bundle_path_out_of_scope()))
    assert result["status"] == "ok"
    assert result["summary"]["blocking_count"] > 0
    assert any(f["severity"] == "blocking" for f in result["findings"])
    assert any(f["human_go_required"] is True for f in result["findings"])


# ── 6. severity filter ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_severity_filter_blocking_only() -> None:
    """severity=blocking returns only blocking findings."""
    result = handle_cdb_context_scope_drift(
        _request(_bundle_multi(), severity="blocking")
    )
    assert result["status"] == "ok"
    for f in result["findings"]:
        assert f["severity"] == "blocking", f"unexpected severity in finding: {f}"


@pytest.mark.unit
def test_severity_filter_warning_only() -> None:
    """severity=warning returns only warning findings."""
    result = handle_cdb_context_scope_drift(
        _request(_bundle_multi(), severity="warning")
    )
    assert result["status"] == "ok"
    for f in result["findings"]:
        assert f["severity"] == "warning", f"unexpected severity in finding: {f}"


@pytest.mark.unit
def test_severity_filter_excludes_others() -> None:
    """When severity=blocking, no warning or info findings are returned."""
    result = handle_cdb_context_scope_drift(
        _request(_bundle_multi(), severity="blocking")
    )
    assert not any(f["severity"] in ("warning", "info") for f in result["findings"])


# ── 7. scope_type filter ──────────────────────────────────────────────────────


@pytest.mark.unit
def test_scope_type_filter_path_out_of_scope() -> None:
    """scope_type=path_out_of_scope returns only path_out_of_scope findings."""
    result = handle_cdb_context_scope_drift(
        _request(_bundle_multi(), scope_type="path_out_of_scope")
    )
    assert result["status"] == "ok"
    for f in result["findings"]:
        assert f["drift_type"] == "path_out_of_scope", f"unexpected drift_type: {f}"


@pytest.mark.unit
def test_scope_type_filter_issue_out_of_scope() -> None:
    """scope_type=issue_out_of_scope filters to only those drift types."""
    result = handle_cdb_context_scope_drift(
        _request(_bundle_multi(), scope_type="issue_out_of_scope")
    )
    assert result["status"] == "ok"
    for f in result["findings"]:
        assert f["drift_type"] == "issue_out_of_scope"


# ── 8. target_ref filter ──────────────────────────────────────────────────────


@pytest.mark.unit
def test_target_ref_filter_match() -> None:
    """target_ref filters to findings where affected_artifacts contains the ref."""
    bundle = _bundle_path_out_of_scope()
    result = handle_cdb_context_scope_drift(
        _request(bundle, target_ref="services/risk/some_file.py")
    )
    assert result["status"] == "ok"
    assert result["summary"]["total_count"] > 0
    for f in result["findings"]:
        assert "services/risk/some_file.py" in f["affected_artifacts"]


@pytest.mark.unit
def test_target_ref_filter_no_match() -> None:
    """target_ref that matches nothing returns zero findings (not an error)."""
    bundle = _bundle_path_out_of_scope()
    result = handle_cdb_context_scope_drift(
        _request(bundle, target_ref="totally/unrelated/path.py")
    )
    assert result["status"] == "ok"
    assert result["summary"]["total_count"] == 0
    assert result["findings"] == []


# ── 9. blocking filter ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_blocking_true_filter() -> None:
    """blocking=True returns only findings with human_go_required=True."""
    result = handle_cdb_context_scope_drift(
        _request(_bundle_multi(), blocking=True)
    )
    assert result["status"] == "ok"
    for f in result["findings"]:
        assert f["human_go_required"] is True, f"unexpected non-blocking finding: {f}"


@pytest.mark.unit
def test_blocking_false_filter() -> None:
    """blocking=False returns only findings with human_go_required=False."""
    result = handle_cdb_context_scope_drift(
        _request(_bundle_multi(), blocking=False)
    )
    assert result["status"] == "ok"
    for f in result["findings"]:
        assert f["human_go_required"] is False, f"unexpected blocking finding: {f}"


@pytest.mark.unit
def test_blocking_true_filter_string_input() -> None:
    """blocking='true' (string) is treated the same as blocking=True."""
    result_bool = handle_cdb_context_scope_drift(
        _request(_bundle_multi(), blocking=True)
    )
    result_str = handle_cdb_context_scope_drift(
        _request(_bundle_multi(), blocking="true")
    )
    assert result_bool["summary"]["total_count"] == result_str["summary"]["total_count"]


# ── 10. limit / truncation ────────────────────────────────────────────────────


@pytest.mark.unit
def test_limit_truncates_findings() -> None:
    """limit=1 returns at most 1 finding and sets truncated=True when more exist."""
    result = handle_cdb_context_scope_drift(
        _request(_bundle_multi(), limit=1)
    )
    assert result["status"] == "ok"
    assert len(result["findings"]) <= 1
    # multi bundle produces >1 finding; if so truncated must be True
    if result["summary"]["total_count"] > 1:
        assert result["summary"]["truncated"] is True


@pytest.mark.unit
def test_limit_no_truncation_when_few_findings() -> None:
    """limit above total finding count → truncated=False."""
    result = handle_cdb_context_scope_drift(
        _request(_bundle_path_out_of_scope(), limit=500)
    )
    assert result["status"] == "ok"
    assert result["summary"]["truncated"] is False


@pytest.mark.unit
def test_truncation_total_count_is_pre_limit() -> None:
    """summary.total_count reflects pre-limit count even when truncated."""
    result_unlimited = handle_cdb_context_scope_drift(
        _request(_bundle_multi(), as_of=_AS_OF)
    )
    total = result_unlimited["summary"]["total_count"]

    if total >= 2:
        result_limited = handle_cdb_context_scope_drift(
            _request(_bundle_multi(), limit=1)
        )
        assert result_limited["summary"]["total_count"] == total
        assert len(result_limited["findings"]) == 1
        assert result_limited["summary"]["truncated"] is True


# ── 11. Error handling ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_missing_bundle_returns_error() -> None:
    """Missing bundle produces a structured error response, not an exception."""
    result = handle_cdb_context_scope_drift(
        {"tool": TOOL_CDB_CONTEXT_SCOPE_DRIFT, "parameters": {}}
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "missing_bundle"
    assert "bundle" in result["error"]["message"]


@pytest.mark.unit
def test_invalid_bundle_non_dict_returns_error() -> None:
    """Non-dict bundle produces a structured error response, not an exception."""
    result = handle_cdb_context_scope_drift(
        {"tool": TOOL_CDB_CONTEXT_SCOPE_DRIFT, "parameters": {"bundle": "not-a-dict"}}
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "missing_bundle"


@pytest.mark.unit
def test_invalid_severity_returns_error() -> None:
    """Unknown severity value returns a structured error response."""
    result = handle_cdb_context_scope_drift(
        _request(_bundle_clean(), severity="critical")
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "invalid_severity"


@pytest.mark.unit
def test_invalid_scope_type_returns_error() -> None:
    """Unknown scope_type value returns a structured error response."""
    result = handle_cdb_context_scope_drift(
        _request(_bundle_clean(), scope_type="not_a_real_drift_type")
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "invalid_scope_type"


@pytest.mark.unit
def test_wrong_tool_name_returns_error() -> None:
    """Mismatched tool name returns an invalid_tool error."""
    result = handle_cdb_context_scope_drift(
        {"tool": "some_other_tool", "parameters": {"bundle": {}}}
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "invalid_tool"


# ── 12. Guardrails ────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_guardrails_present_in_response() -> None:
    """Guardrail strings are always present in a successful response."""
    result = handle_cdb_context_scope_drift(_request(_bundle_clean()))
    assert result["status"] == "ok"
    assert "guardrails" in result
    guardrails = result["guardrails"]
    assert isinstance(guardrails, list)
    assert len(guardrails) > 0
    # All canonical guardrails from the service must be present
    for g in GUARDRAILS:
        assert g in guardrails, f"missing guardrail: {g!r}"


# ── 13. Output contract / metadata ────────────────────────────────────────────


@pytest.mark.unit
def test_response_metadata_read_only_true() -> None:
    """metadata.read_only must be True in every successful response."""
    result = handle_cdb_context_scope_drift(_request(_bundle_clean()))
    assert result["status"] == "ok"
    assert result["metadata"]["read_only"] is True
    assert result["metadata"]["source"] == "in_memory"


@pytest.mark.unit
def test_response_includes_scan_status_and_scanned_at() -> None:
    """scan_status and scanned_at must be present in a successful response."""
    result = handle_cdb_context_scope_drift(_request(_bundle_clean()))
    assert result["status"] == "ok"
    assert "scan_status" in result
    assert result["scan_status"] in ("ok", "blocked_scope_drift")
    assert "scanned_at" in result
    assert isinstance(result["scanned_at"], str)


@pytest.mark.unit
def test_response_schema_version() -> None:
    """schema_version must match the adapter constant."""
    result = handle_cdb_context_scope_drift(_request(_bundle_clean()))
    assert result.get("schema_version") == SCHEMA_VERSION


@pytest.mark.unit
def test_filters_applied_populated_when_filter_active() -> None:
    """summary.filters_applied must reflect every active filter."""
    result = handle_cdb_context_scope_drift(
        _request(_bundle_clean(), severity="blocking", scope_type="path_out_of_scope")
    )
    assert result["status"] == "ok"
    fa = result["summary"]["filters_applied"]
    assert fa.get("severity") == "blocking"
    assert fa.get("scope_type") == "path_out_of_scope"


@pytest.mark.unit
def test_filters_applied_empty_when_no_filter() -> None:
    """summary.filters_applied is empty dict when no optional filters are set."""
    result = handle_cdb_context_scope_drift(_request(_bundle_clean()))
    assert result["status"] == "ok"
    assert result["summary"]["filters_applied"] == {}


# ── 14. Safety: no writes, no network, no subprocess ─────────────────────────


@pytest.mark.unit
def test_response_is_plain_dict_no_side_effects() -> None:
    """Tool returns a plain serialisable dict; no exceptions escape."""
    result = handle_cdb_context_scope_drift(_request(_bundle_multi()))
    assert isinstance(result, dict)
    # Verify findings are plain dicts (not dataclass instances)
    for f in result.get("findings", []):
        assert isinstance(f, dict)


@pytest.mark.unit
def test_no_db_no_network_no_write_bundle_write_keywords() -> None:
    """Bundle with write-intent keywords is handled safely (no leak, no crash)."""
    result = handle_cdb_context_scope_drift(
        _request(_bundle_with_write_intent())
    )
    # Must return a valid dict response (error or ok — no exception)
    assert isinstance(result, dict)
    assert "status" in result


# ── 15. Benchmark #2 minimal bundles (#2844) ─────────────────────────────────


def _bundle_benchmark_minimal() -> dict[str, Any]:
    """Operator-style minimal bundle from Benchmark #2 live invocation."""
    return {
        "meta": {"scope_id": "bench", "level": "system"},
        "declared_scope": "benchmark",
        "touched_artifacts": [],
        "issue_refs": [],
        "generated_findings": [],
        "forbidden_surfaces": [],
    }


def _bundle_valid_minimal_structured() -> dict[str, Any]:
    """Structured declared_scope with explicit empty constraint lists."""
    return {
        "meta": {"scope_id": "bench", "as_of": _AS_OF},
        "declared_scope": {
            "target_paths": [],
            "allowed_domains": [],
        },
        "touched_artifacts": [],
        "issue_refs": [],
        "generated_findings": [],
        "forbidden_surfaces": [],
    }


@pytest.mark.unit
def test_benchmark_minimal_bundle_no_scan_error() -> None:
    """#2844: string declared_scope must not raise scan_error / AttributeError."""
    result = handle_cdb_context_scope_drift(_request(_bundle_benchmark_minimal()))
    assert result["status"] == "ok"
    assert result.get("error") is None
    assert result["scan_status"] == "ok"
    assert result["summary"]["total_count"] == 0


@pytest.mark.unit
def test_benchmark_minimal_bundle_via_bridge() -> None:
    """Bridge path matches direct handler for minimal benchmark bundle."""
    bridge = ContextBridge()
    result = bridge.execute_tool(
        TOOL_CDB_CONTEXT_SCOPE_DRIFT,
        {"bundle": _bundle_benchmark_minimal(), "as_of": _AS_OF},
    )
    assert result["status"] == "ok"
    assert "scan_error" not in str(result.get("error", {}))


@pytest.mark.unit
def test_empty_bundle_lists_ok() -> None:
    """Empty artifact lists with empty declared_scope object → ok, zero findings."""
    result = handle_cdb_context_scope_drift(
        _request(
            {
                "declared_scope": {},
                "touched_artifacts": [],
                "issue_refs": [],
                "generated_findings": [],
                "forbidden_surfaces": [],
            }
        )
    )
    assert result["status"] == "ok"
    assert result["summary"]["total_count"] == 0


@pytest.mark.unit
def test_malformed_declared_scope_type_returns_invalid_bundle() -> None:
    """Non-string/non-mapping declared_scope → invalid_bundle, not scan_error."""
    result = handle_cdb_context_scope_drift(
        _request({"declared_scope": ["not", "a", "mapping"]})
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "invalid_bundle"
    assert "declared_scope" in result["error"]["message"]


@pytest.mark.unit
def test_valid_minimal_structured_bundle_deterministic() -> None:
    """Structured minimal bundle returns stable ok response with explicit as_of."""
    result = handle_cdb_context_scope_drift(_request(_bundle_valid_minimal_structured()))
    assert result["status"] == "ok"
    assert result["scanned_at"] == _AS_OF
    assert result["summary"]["total_count"] == 0
