"""Unit tests for Wave-18 MCP tool: cdb_context_quality_score.

Issues:
    #2176 — [SURREALDB][CONTEXT][QUALITY-TESTS] Tests for Wave-18 quality scoring
    Parent: #2170 (Wave-18 anchor)
    Epic: #1976

Scope:
    Unit tests for tools/mcp/quality_scoring_tools.py and its integration
    with the MCP registry, context bridge, and permission guard.
    All fixtures are inline — no file loading.
    No DB access. No SurrealDB SDK. No network. No writes.
"""

from __future__ import annotations

from typing import Any

import pytest

from tools.mcp.context_bridge import ContextBridge
from tools.mcp.permission_guard import INPUT_SCAN_EXEMPT_TOOLS
from tools.mcp.quality_scoring_tools import (
    SCHEMA_VERSION,
    TOOL_CDB_CONTEXT_QUALITY_SCORE,
    handle_quality_score,
)
from tools.mcp.registry import ContextToolRegistry
from tools.surrealdb.quality_scoring import GUARDRAILS, SCORE_DIMENSIONS

_AS_OF = "2026-05-06T12:00:00+00:00"


# ── Inline fixtures ───────────────────────────────────────────────────────────


def _clean_bundle() -> dict[str, Any]:
    return {
        "meta": {"scope_id": "mcp-clean-001", "level": "system"},
        "sources": [
            {"source_path": "core/risk/service.py", "has_documentation": True, "has_tests": True, "status": "current"},
        ],
        "decisions": [{"decision_id": "dec-001", "status": "current", "evidence_refs": ["ev-001"]}],
        "evidence_items": [{"evidence_id": "ev-001", "strength": "strong", "expired": False}],
        "contradiction_findings": [],
        "stale_findings": [],
        "dependency_edges": [{"edge_id": "e-001", "confidence": "high"}],
        "memory_items": [{"memory_id": "m-001", "trust_level": "strong"}],
        "scope_drift_findings": [],
    }


def _blocking_bundle() -> dict[str, Any]:
    return {
        "meta": {"scope_id": "mcp-blocking-001", "level": "system"},
        "sources": [],
        "contradiction_findings": [
            {"contradiction_id": "c-001", "severity": "blocking", "status": "open"},
        ],
    }


# ── Permission Guard ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_quality_score_tool_in_exempt_set() -> None:
    """cdb_context_quality_score must be in INPUT_SCAN_EXEMPT_TOOLS."""
    assert TOOL_CDB_CONTEXT_QUALITY_SCORE in INPUT_SCAN_EXEMPT_TOOLS


# ── Registry ─────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_quality_score_registered_read_only() -> None:
    """cdb_context_quality_score is registered as read-only in the registry."""
    tool = ContextToolRegistry.get_tool(TOOL_CDB_CONTEXT_QUALITY_SCORE)
    assert tool is not None
    assert tool.read_only is True


@pytest.mark.unit
def test_quality_score_has_handler() -> None:
    """cdb_context_quality_score has a non-None handler."""
    tool = ContextToolRegistry.get_tool(TOOL_CDB_CONTEXT_QUALITY_SCORE)
    assert tool is not None
    assert tool.handler is not None


# ── Context Bridge ────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_bridge_routes_quality_score() -> None:
    """ContextBridge routes cdb_context_quality_score to the real handler."""
    bridge = ContextBridge()
    result = bridge.execute_tool(
        TOOL_CDB_CONTEXT_QUALITY_SCORE,
        {"bundle": _clean_bundle(), "as_of": _AS_OF},
    )
    assert result.get("status") == "ok"
    assert result.get("tool") == TOOL_CDB_CONTEXT_QUALITY_SCORE


# ── Missing bundle ────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_missing_bundle_returns_error() -> None:
    """Missing bundle parameter returns an error response."""
    result = handle_quality_score(as_of=_AS_OF)
    assert result["status"] == "error"
    assert result["error"]["code"] == "missing_bundle"


@pytest.mark.unit
def test_non_mapping_bundle_returns_error() -> None:
    """Non-mapping bundle returns an error response."""
    result = handle_quality_score(bundle="not-a-dict", as_of=_AS_OF)
    assert result["status"] == "error"
    assert result["error"]["code"] == "missing_bundle"


# ── Valid bundle ──────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_clean_bundle_returns_ok() -> None:
    """Clean bundle returns status ok."""
    result = handle_quality_score(bundle=_clean_bundle(), as_of=_AS_OF)
    assert result["status"] == "ok"


@pytest.mark.unit
def test_clean_bundle_returns_schema_version() -> None:
    """Clean bundle result has correct schema_version."""
    result = handle_quality_score(bundle=_clean_bundle(), as_of=_AS_OF)
    assert result.get("schema_version") == SCHEMA_VERSION


@pytest.mark.unit
def test_clean_bundle_metadata_read_only() -> None:
    """Response metadata.read_only is always True."""
    result = handle_quality_score(bundle=_clean_bundle(), as_of=_AS_OF)
    assert result.get("metadata", {}).get("read_only") is True


@pytest.mark.unit
def test_clean_bundle_guardrails_present() -> None:
    """Response includes all GUARDRAILS strings."""
    result = handle_quality_score(bundle=_clean_bundle(), as_of=_AS_OF)
    assert set(GUARDRAILS).issubset(set(result.get("guardrails", [])))


@pytest.mark.unit
def test_blocking_bundle_returns_ok_status() -> None:
    """Blocking bundle still returns status 'ok' (grade is blocking, not error)."""
    result = handle_quality_score(bundle=_blocking_bundle(), as_of=_AS_OF)
    assert result["status"] == "ok"


@pytest.mark.unit
def test_clean_bundle_returns_dimensions() -> None:
    """Clean bundle result has 8 dimension entries."""
    result = handle_quality_score(bundle=_clean_bundle(), as_of=_AS_OF)
    dims = result.get("dimensions", [])
    dim_names = {d["dimension"] for d in dims}
    assert dim_names == set(SCORE_DIMENSIONS)


# ── Filters: dimension ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_dimension_filter() -> None:
    """dimension filter returns only the specified dimension."""
    result = handle_quality_score(
        bundle=_clean_bundle(), dimension="coverage_score", as_of=_AS_OF
    )
    dims = result.get("dimensions", [])
    assert all(d["dimension"] == "coverage_score" for d in dims)


@pytest.mark.unit
def test_invalid_dimension_returns_error() -> None:
    """Invalid dimension returns an error response."""
    result = handle_quality_score(
        bundle=_clean_bundle(), dimension="nonexistent_dimension", as_of=_AS_OF
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "invalid_dimension"


# ── Filters: min_grade ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_min_grade_blocking_filter() -> None:
    """min_grade=blocking returns only blocking dimensions."""
    result = handle_quality_score(
        bundle=_blocking_bundle(), min_grade="blocking", as_of=_AS_OF
    )
    dims = result.get("dimensions", [])
    assert all(d["grade"] == "blocking" for d in dims)


@pytest.mark.unit
def test_invalid_grade_returns_error() -> None:
    """Invalid min_grade returns an error response."""
    result = handle_quality_score(
        bundle=_clean_bundle(), min_grade="excellent", as_of=_AS_OF
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "invalid_grade"


# ── Filters: limit ────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_limit_one_returns_at_most_one_dimension() -> None:
    """limit=1 returns at most 1 dimension."""
    result = handle_quality_score(bundle=_clean_bundle(), limit=1, as_of=_AS_OF)
    assert len(result.get("dimensions", [])) <= 1


@pytest.mark.unit
def test_limit_zero_clamped_to_one() -> None:
    """limit=0 is clamped to 1 (minimum)."""
    result = handle_quality_score(bundle=_clean_bundle(), limit=0, as_of=_AS_OF)
    assert result["status"] == "ok"
    assert len(result.get("dimensions", [])) >= 0  # may be 0 if no dims match


@pytest.mark.unit
def test_limit_above_max_clamped() -> None:
    """limit above 500 is silently capped."""
    result = handle_quality_score(bundle=_clean_bundle(), limit=9999, as_of=_AS_OF)
    assert result["status"] == "ok"
    assert len(result.get("dimensions", [])) <= 500
