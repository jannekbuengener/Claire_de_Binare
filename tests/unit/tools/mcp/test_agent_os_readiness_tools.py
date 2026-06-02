"""Unit tests for Agent OS Readiness MCP Tool v1 (#2192, #2194)."""

from __future__ import annotations

from typing import Any

import pytest

from tools.mcp.agent_os_readiness_tools import (
    SCHEMA_VERSION,
    TOOL_CDB_AGENT_OS_READINESS,
    handle_agent_os_readiness,
)

pytestmark = pytest.mark.unit

_AS_OF = "2026-05-08T12:00:00+00:00"


def _minimal_bundle(scope_id: str = "mcp-test-scope") -> dict[str, Any]:
    return {"meta": {"scope_id": scope_id, "level": "domain"}}


def _clean_bundle() -> dict[str, Any]:
    return {
        "meta": {"scope_id": "mcp-clean-scope", "level": "domain"},
        "sources": [
            {
                "path": "tools/mcp/agent_os_readiness_tools.py",
                "has_documentation": True,
                "has_tests": True,
                "owner": "cdb-mcp",
            }
        ],
        "decisions": [
            {
                "decision_id": "D-MCP-001",
                "title": "MCP tool design",
                "status": "active",
                "evidence_refs": ["E-MCP-001"],
            }
        ],
        "evidence_items": [
            {
                "evidence_id": "E-MCP-001",
                "strength": "strong",
                "expires_at": "2027-01-01T00:00:00+00:00",
            }
        ],
        "contradiction_findings": [],
        "stale_findings": [],
        "scope_drift_findings": [],
        "memory_items": [],
        "dependency_edges": [],
    }


# ── Fail-closed / error path tests ───────────────────────────────────────────


class TestHandleAgentOsReadinessErrors:
    def test_missing_bundle_returns_error(self) -> None:
        result = handle_agent_os_readiness()
        assert result["status"] == "error"
        assert result["error"]["code"] == "missing_bundle"
        assert result["tool"] == TOOL_CDB_AGENT_OS_READINESS

    def test_none_bundle_returns_error(self) -> None:
        result = handle_agent_os_readiness(bundle=None)
        assert result["status"] == "error"
        assert result["error"]["code"] == "missing_bundle"

    def test_invalid_bundle_not_dict_returns_error(self) -> None:
        result = handle_agent_os_readiness(bundle="not-a-dict")
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_bundle"

    def test_invalid_bundle_list_returns_error(self) -> None:
        result = handle_agent_os_readiness(bundle=[])
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_bundle"

    def test_missing_scope_id_returns_evaluator_error(self) -> None:
        result = handle_agent_os_readiness(bundle={"meta": {}})
        assert result["status"] == "error"
        assert result["error"]["code"] == "evaluator_error"
        assert "scope_id" in result["error"]["message"].lower()

    def test_error_response_includes_guardrails(self) -> None:
        result = handle_agent_os_readiness(bundle=None)
        assert "guardrails" in result
        assert len(result["guardrails"]) > 0

    def test_error_response_has_tool_name(self) -> None:
        result = handle_agent_os_readiness(bundle=None)
        assert result["tool"] == TOOL_CDB_AGENT_OS_READINESS

    def test_error_response_has_schema_version(self) -> None:
        result = handle_agent_os_readiness(bundle=None)
        assert result["schema_version"] == SCHEMA_VERSION


# ── Happy-path tests ──────────────────────────────────────────────────────────


class TestHandleAgentOsReadinessOk:
    def test_valid_bundle_returns_ok(self) -> None:
        result = handle_agent_os_readiness(bundle=_clean_bundle(), as_of=_AS_OF)
        assert result["status"] == "ok"

    def test_valid_bundle_has_readiness_level(self) -> None:
        result = handle_agent_os_readiness(bundle=_clean_bundle(), as_of=_AS_OF)
        assert "readiness_level" in result
        assert result["readiness_level"] in {"blocked", "weak", "acceptable", "strong"}

    def test_valid_bundle_has_result(self) -> None:
        result = handle_agent_os_readiness(bundle=_clean_bundle(), as_of=_AS_OF)
        assert "result" in result
        assert isinstance(result["result"], dict)

    def test_valid_bundle_has_guardrails(self) -> None:
        result = handle_agent_os_readiness(bundle=_clean_bundle(), as_of=_AS_OF)
        assert "guardrails" in result
        assert len(result["guardrails"]) == 6

    def test_valid_bundle_has_metadata(self) -> None:
        result = handle_agent_os_readiness(bundle=_clean_bundle(), as_of=_AS_OF)
        assert "metadata" in result
        meta = result["metadata"]
        for key in ("readiness_id", "target_scope", "generated_at", "confidence"):
            assert key in meta, f"metadata missing key: {key}"

    def test_tool_name_in_result(self) -> None:
        result = handle_agent_os_readiness(bundle=_clean_bundle(), as_of=_AS_OF)
        assert result["tool"] == TOOL_CDB_AGENT_OS_READINESS

    def test_schema_version_present(self) -> None:
        result = handle_agent_os_readiness(bundle=_clean_bundle(), as_of=_AS_OF)
        assert result["schema_version"] == SCHEMA_VERSION

    def test_clean_bundle_readiness_level_strong(self) -> None:
        result = handle_agent_os_readiness(bundle=_clean_bundle(), as_of=_AS_OF)
        assert result["readiness_level"] == "strong"

    def test_blocking_finding_produces_blocked_level(self) -> None:
        bundle = {
            **_clean_bundle(),
            "scope_drift_findings": [
                {
                    "drift_id": "sd-001",
                    "drift_type": "path_out_of_scope",
                    "severity": "blocking",
                    "status": "open",
                }
            ],
        }
        result = handle_agent_os_readiness(bundle=bundle, as_of=_AS_OF)
        assert result["status"] == "ok"
        assert result["readiness_level"] == "blocked"

    def test_guardrails_include_no_live_readiness_go(self) -> None:
        result = handle_agent_os_readiness(bundle=_clean_bundle(), as_of=_AS_OF)
        joined = " ".join(result["guardrails"])
        assert "No Live-Readiness-Go" in joined

    def test_guardrails_include_no_trading_console(self) -> None:
        result = handle_agent_os_readiness(bundle=_clean_bundle(), as_of=_AS_OF)
        joined = " ".join(result["guardrails"])
        assert "No trading console" in joined


# ── include_report tests (#2193) ──────────────────────────────────────────────


class TestIncludeReport:
    def test_include_report_false_by_default(self) -> None:
        result = handle_agent_os_readiness(bundle=_clean_bundle(), as_of=_AS_OF)
        assert "report_markdown" not in result

    def test_include_report_true_returns_markdown(self) -> None:
        result = handle_agent_os_readiness(
            bundle=_clean_bundle(), as_of=_AS_OF, include_report=True
        )
        assert "report_markdown" in result
        assert isinstance(result["report_markdown"], str)
        assert len(result["report_markdown"]) > 0

    def test_report_markdown_contains_scope_id(self) -> None:
        result = handle_agent_os_readiness(
            bundle=_clean_bundle(), as_of=_AS_OF, include_report=True
        )
        assert "mcp-clean-scope" in result["report_markdown"]

    def test_report_markdown_contains_guardrails(self) -> None:
        result = handle_agent_os_readiness(
            bundle=_clean_bundle(), as_of=_AS_OF, include_report=True
        )
        assert "No Live-Readiness-Go" in result["report_markdown"]
        assert "NO-GO" in result["report_markdown"]


# ── ContextBridge / registry integration tests ────────────────────────────────


class TestBridgeIntegration:
    def test_bridge_registered_read_only(self) -> None:
        from tools.mcp.registry import ContextToolRegistry

        tool = ContextToolRegistry.get_tool(TOOL_CDB_AGENT_OS_READINESS)
        assert tool is not None, "cdb_agent_os_readiness must be registered"
        assert tool.read_only is True

    def test_bridge_executes_cdb_agent_os_readiness(self) -> None:
        from tools.mcp.context_bridge import ContextBridge

        bridge = ContextBridge()
        result = bridge.execute_tool(
            TOOL_CDB_AGENT_OS_READINESS,
            {"bundle": _clean_bundle(), "as_of": _AS_OF},
        )
        assert result["status"] == "ok"
        assert result["readiness_level"] in {"blocked", "weak", "acceptable", "strong"}

    def test_bridge_fail_closed_missing_bundle(self) -> None:
        from tools.mcp.context_bridge import ContextBridge

        bridge = ContextBridge()
        result = bridge.execute_tool(TOOL_CDB_AGENT_OS_READINESS, {})
        assert result["status"] == "error"

    def test_permission_guard_exempt(self) -> None:
        from tools.mcp.permission_guard import INPUT_SCAN_EXEMPT_TOOLS

        assert TOOL_CDB_AGENT_OS_READINESS in INPUT_SCAN_EXEMPT_TOOLS

    def test_registry_consistency_holds(self) -> None:
        """assert_read_only_consistency() must not raise after ContextBridge init."""
        from tools.mcp.context_bridge import ContextBridge

        bridge = ContextBridge()
        # If we get here without ValueError the registry is consistent
        status = bridge.get_read_only_status()
        assert status["enforced"] is True

    def test_tool_count_increased(self) -> None:
        """Registry should contain at least 26 tools (25 Wave-19 + 1 new)."""
        from tools.mcp.registry import ContextToolRegistry

        tool_names = ContextToolRegistry.list_tool_names()
        assert TOOL_CDB_AGENT_OS_READINESS in tool_names
        assert len(tool_names) >= 26


def test_mcp_passes_operator_certification_through_bundle() -> None:
    bundle = _clean_bundle()
    bundle["operator_certification"] = {
        "final_verdict": "certified",
        "gate_matrix": [
            {
                "check_id": "registry_all_read_only",
                "status": "pass",
                "blocking": True,
                "detail": "ok",
            }
        ],
    }
    result = handle_agent_os_readiness(bundle=bundle, as_of=_AS_OF)
    assert result["status"] == "ok"
    assert result["readiness_level"] == "strong"
    assert not any(
        "operator_certification" in item for item in result["result"]["missing_inputs"]
    )
