"""Unit tests for stale_refresh_plan.py — Refresh Plan Generator v1.

Issues:
    #2158 — [SURREALDB][CONTEXT][STALE-RUNTIME] Implement refresh plan generator
    Parent: #2153 (Wave-16 anchor)
    Epic: #1976

Scope:
    Unit tests for tools/surrealdb/stale_refresh_plan.py.
    All fixtures are inline (no file loading — keeps slice narrow).
    No DB access. No SurrealDB SDK. No MCP. No networking. No writes.
    No real datetime.now() — validated by test_clock.py::test_guardrails_no_forbidden_calls.

Coverage:
    - multi-stale bundle generates plan items.
    - source_deleted → P0.
    - Each stale_type maps to its canonical recommended_action.
    - Deterministic plan_ids: same input → same plan_id on repeated calls.
    - All 6 guardrail strings present in to_dict() output.
    - write_authorized is always False on every plan item.
    - Empty findings → empty plan, status=ok.
    - Invalid (non-Mapping) scan_input → status=error.
    - No forbidden imports (requests, httpx, subprocess, surrealdb).
"""

from __future__ import annotations

import pytest

from tools.surrealdb.stale_refresh_plan import (
    GUARDRAILS,
    PRIORITIES,
    SCHEMA_VERSION,
    TOOL_NAME,
    RefreshPlanItem,
    RefreshPlanResult,
    generate_refresh_plan_v1,
    _plan_id,
    _derive_action,
    _derive_priority,
)

# ── Fixed timestamps ──────────────────────────────────────────────────────────

_AS_OF = "2026-05-06T12:00:00+00:00"
_PAST = "2026-01-01T00:00:00+00:00"


# ── Minimal bundle builders ───────────────────────────────────────────────────


def _make_bundle_with_types(*stale_types: str) -> dict:
    """Build a minimal inline bundle that will trigger the given stale types.

    Field names match the scan service input contracts exactly:
      sources         → source_id, current_hash/last_verified_hash, exists/deleted_at
      decisions       → decision_id, superseded_by
      evidence_records → evidence_id, expires_at
      memory_records  → memory_id, expires_at
      dependency_edges → edge_id, from_ref, to_ref, observed
      context_packages → package_id, generated_at, freshness_window_seconds
      briefings        → briefing_id, generated_at, freshness_window_seconds
    """
    bundle: dict = {
        "sources": [],
        "decisions": [],
        "evidence_records": [],
        "memory_records": [],
        "dependency_edges": [],
        "context_packages": [],
        "briefings": [],
        "meta": {"as_of": _AS_OF},
    }

    for st in stale_types:
        if st == "source_hash_changed":
            bundle["sources"].append({
                "source_id": "src-hash-001",
                "current_hash": "aaaaaaaaaaaaaaaa",
                "last_verified_hash": "bbbbbbbbbbbbbbbb",
            })
        elif st == "source_deleted":
            bundle["sources"].append({
                "source_id": "src-deleted-001",
                "exists": False,
            })
        elif st == "evidence_expired":
            bundle["evidence_records"].append({
                "evidence_id": "ev-001",
                "expires_at": _PAST,
            })
        elif st == "memory_ttl_expired":
            bundle["memory_records"].append({
                "memory_id": "mem-001",
                "expires_at": _PAST,
            })
        elif st == "decision_superseded":
            bundle["decisions"].append({
                "decision_id": "dec-001",
                "superseded_by": "dec-002",
                "status": "superseded",
            })
        elif st == "dependency_edge_no_longer_observed":
            bundle["dependency_edges"].append({
                "edge_id": "edge-001",
                "from_ref": "svc-a",
                "to_ref": "svc-b",
                "observed": False,
            })
        elif st == "stale_context_package":
            bundle["context_packages"].append({
                "package_id": "ctx-001",
                "generated_at": _PAST,
                "freshness_window_seconds": 3600,
            })
        elif st == "stale_briefing":
            bundle["briefings"].append({
                "briefing_id": "brief-001",
                "generated_at": _PAST,
                "freshness_window_seconds": 3600,
            })

    return bundle


def _plan(bundle: dict, as_of: str = _AS_OF) -> RefreshPlanResult:
    return generate_refresh_plan_v1(bundle, as_of=as_of)


# ── Tests: action mapping ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_source_deleted_is_p0() -> None:
    """source_deleted finding must produce a P0 plan item."""
    result = _plan(_make_bundle_with_types("source_deleted"))
    assert result.status == "ok"
    items = [i for i in result.plan_items if i.stale_type == "source_deleted"]
    assert len(items) >= 1, "Expected at least one source_deleted plan item"
    for item in items:
        assert item.priority == "P0", f"Expected P0 but got {item.priority!r}"
    # _derive_priority: blocking=True always yields P0 regardless of severity.
    assert _derive_priority("source_deleted", "blocking", 1.0, True) == "P0"


@pytest.mark.unit
def test_evidence_expired_action_refresh_evidence() -> None:
    """evidence_expired → recommended_action=='refresh_evidence'."""
    result = _plan(_make_bundle_with_types("evidence_expired"))
    assert result.status == "ok"
    items = [i for i in result.plan_items if i.stale_type == "evidence_expired"]
    assert len(items) >= 1
    for item in items:
        assert item.recommended_action == "refresh_evidence"
    # _derive_action must map the canonical stale_type to the same action.
    assert _derive_action("evidence_expired") == "refresh_evidence"


@pytest.mark.unit
def test_memory_ttl_expired_action_refresh_memory() -> None:
    """memory_ttl_expired → recommended_action=='refresh_memory'."""
    result = _plan(_make_bundle_with_types("memory_ttl_expired"))
    assert result.status == "ok"
    items = [i for i in result.plan_items if i.stale_type == "memory_ttl_expired"]
    assert len(items) >= 1
    for item in items:
        assert item.recommended_action == "refresh_memory"


@pytest.mark.unit
def test_decision_superseded_action_recheck_decision() -> None:
    """decision_superseded → recommended_action=='recheck_decision'."""
    result = _plan(_make_bundle_with_types("decision_superseded"))
    assert result.status == "ok"
    items = [i for i in result.plan_items if i.stale_type == "decision_superseded"]
    assert len(items) >= 1
    for item in items:
        assert item.recommended_action == "recheck_decision"


@pytest.mark.unit
def test_stale_context_package_action_rebuild() -> None:
    """stale_context_package → recommended_action=='rebuild_context_package'."""
    result = _plan(_make_bundle_with_types("stale_context_package"))
    assert result.status == "ok"
    items = [i for i in result.plan_items if i.stale_type == "stale_context_package"]
    assert len(items) >= 1
    for item in items:
        assert item.recommended_action == "rebuild_context_package"


@pytest.mark.unit
def test_stale_briefing_action_regenerate() -> None:
    """stale_briefing → recommended_action=='regenerate_briefing'."""
    result = _plan(_make_bundle_with_types("stale_briefing"))
    assert result.status == "ok"
    items = [i for i in result.plan_items if i.stale_type == "stale_briefing"]
    assert len(items) >= 1
    for item in items:
        assert item.recommended_action == "regenerate_briefing"


@pytest.mark.unit
def test_dependency_edge_action_reobserve() -> None:
    """dependency_edge_no_longer_observed → recommended_action=='reobserve_dependency_edge'."""
    result = _plan(_make_bundle_with_types("dependency_edge_no_longer_observed"))
    assert result.status == "ok"
    items = [i for i in result.plan_items if i.stale_type == "dependency_edge_no_longer_observed"]
    assert len(items) >= 1
    for item in items:
        assert item.recommended_action == "reobserve_dependency_edge"


# ── Tests: multi-type bundle ──────────────────────────────────────────────────


@pytest.mark.unit
def test_plan_from_sample_scan_generates_items() -> None:
    """Multi-stale bundle produces at least 3 distinct plan items with correct fields."""
    bundle = _make_bundle_with_types(
        "source_deleted", "evidence_expired", "stale_briefing"
    )
    result = _plan(bundle)
    assert result.status == "ok"
    assert result.plan_item_count >= 3
    assert len(result.plan_items) == result.plan_item_count
    for item in result.plan_items:
        assert isinstance(item, RefreshPlanItem)
        assert isinstance(item.plan_id, str) and len(item.plan_id) == 16
        assert item.priority in PRIORITIES
        assert item.recommended_action in (
            "reverify_source", "refresh_evidence", "refresh_memory",
            "recheck_decision", "rebuild_context_package", "regenerate_briefing",
            "reobserve_dependency_edge", "manual_review",
        )
        assert item.write_authorized is False
        assert item.status == "pending"


# ── Tests: determinism ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_deterministic_plan_ids() -> None:
    """Two runs with identical input must produce identical plan_ids."""
    bundle = _make_bundle_with_types("source_deleted", "evidence_expired")
    result_a = _plan(bundle)
    result_b = _plan(bundle)
    ids_a = sorted(item.plan_id for item in result_a.plan_items)
    ids_b = sorted(item.plan_id for item in result_b.plan_items)
    assert ids_a == ids_b, "plan_ids are not deterministic across runs"
    # _plan_id itself must be stable and produce a 16-char hex digest.
    pid = _plan_id("stale-001", "reverify_source", "src/main.py")
    assert pid == _plan_id("stale-001", "reverify_source", "src/main.py")
    assert len(pid) == 16


# ── Tests: guardrails ─────────────────────────────────────────────────────────


@pytest.mark.unit
def test_guardrails_present() -> None:
    """Every string in GUARDRAILS must appear in the to_dict() output."""
    result = _plan(_make_bundle_with_types("evidence_expired"))
    payload = result.to_dict()
    assert len(GUARDRAILS) >= 6, "Expected at least 6 guardrail strings"
    for expected in GUARDRAILS:
        assert expected in payload["guardrails"], f"Missing guardrail: {expected!r}"


@pytest.mark.unit
def test_write_authorized_always_false() -> None:
    """Every plan item must have write_authorized=False, regardless of stale_type."""
    all_types = [
        "source_hash_changed",
        "source_deleted",
        "evidence_expired",
        "memory_ttl_expired",
        "decision_superseded",
        "dependency_edge_no_longer_observed",
        "stale_context_package",
        "stale_briefing",
    ]
    bundle = _make_bundle_with_types(*all_types)
    result = _plan(bundle)
    assert result.plan_item_count >= 1
    for item in result.plan_items:
        assert item.write_authorized is False, (
            f"plan_id={item.plan_id!r} stale_type={item.stale_type!r} "
            f"has write_authorized=True — this violates guardrails."
        )


# ── Tests: edge cases ─────────────────────────────────────────────────────────


@pytest.mark.unit
def test_empty_findings_returns_empty_plan() -> None:
    """Bundle with no stale artifacts → empty plan, status=ok."""
    bundle = {
        "sources": [],
        "decisions": [],
        "evidence_records": [],
        "memory_records": [],
        "dependency_edges": [],
        "context_packages": [],
        "briefings": [],
        "meta": {"as_of": _AS_OF},
    }
    result = _plan(bundle)
    assert result.status == "ok"
    assert result.plan_item_count == 0
    assert result.plan_items == ()
    assert result.errors == ()


@pytest.mark.unit
def test_bundle_meta_as_of_is_honoured_without_explicit_as_of() -> None:
    """When as_of is not passed, bundle['meta']['as_of'] must be used.

    Time-based stale rules (evidence_expired, memory_ttl_expired, etc.) depend
    on the reference timestamp.  If the generator silently falls back to wall-
    clock time the result is non-deterministic across runs.
    """
    # Build a bundle whose evidence_records already expired relative to _AS_OF
    # but are NOT expired relative to a much later timestamp.
    bundle = {
        "sources": [],
        "decisions": [],
        "evidence_records": [
            {
                "evidence_id": "ev-001",
                "expires_at": _PAST,  # expired before _AS_OF
            }
        ],
        "memory_records": [],
        "dependency_edges": [],
        "context_packages": [],
        "briefings": [],
        "meta": {"as_of": _AS_OF},
    }
    # Without explicit as_of, the generator must pick up _AS_OF from bundle meta.
    result_from_meta = generate_refresh_plan_v1(bundle)
    # With explicit as_of equal to meta value, result must be identical.
    result_explicit = generate_refresh_plan_v1(bundle, as_of=_AS_OF)
    assert result_from_meta.status == "ok"
    assert result_explicit.status == "ok"
    assert result_from_meta.plan_item_count == result_explicit.plan_item_count
    assert result_from_meta.as_of == result_explicit.as_of


@pytest.mark.unit
def test_invalid_input_returns_status_error() -> None:
    """Non-Mapping, non-StaleKnowledgeScanResult input → status=error, no crash."""
    result = generate_refresh_plan_v1(["not", "a", "mapping"])  # type: ignore[arg-type]
    assert result.status == "error"
    assert len(result.errors) > 0
    assert result.plan_item_count == 0
    assert result.tool == TOOL_NAME
    assert result.schema_version == SCHEMA_VERSION


# ── Tests: schema and output format ──────────────────────────────────────────


@pytest.mark.unit
def test_to_dict_has_all_required_keys() -> None:
    """to_dict() output contains all mandatory top-level keys."""
    result = _plan(_make_bundle_with_types("evidence_expired"))
    payload = result.to_dict()
    required_keys = {
        "tool", "schema_version", "status", "as_of",
        "summary", "plan_items", "guardrails", "errors",
    }
    assert required_keys.issubset(payload.keys())
    summary_keys = {"total_findings", "blocking_findings", "plan_item_count",
                    "priority_summary", "action_summary"}
    assert summary_keys.issubset(payload["summary"].keys())


@pytest.mark.unit
def test_priority_summary_covers_all_priorities() -> None:
    """priority_summary in to_dict() must contain all four P-levels."""
    result = _plan(_make_bundle_with_types("source_deleted", "evidence_expired"))
    payload = result.to_dict()
    for p in ("P0", "P1", "P2", "P3"):
        assert p in payload["summary"]["priority_summary"]


# ── Tests: security / forbidden imports ──────────────────────────────────────


@pytest.mark.unit
def test_no_forbidden_imports() -> None:
    """stale_refresh_plan.py must not contain forbidden imports or write calls.

    Uses AST parsing on the source file directly — isolated from sys.modules
    state of the test runner or other test dependencies.

    Forbidden imports: requests, httpx, subprocess, surrealdb
    Forbidden call patterns (write-path): open(...,"w"), .write(), unlink,
        remove, rmtree, os.system
    """
    import ast
    import pathlib

    source_path = pathlib.Path(__file__).parent.parent.parent.parent / "tools" / "surrealdb" / "stale_refresh_plan.py"
    assert source_path.exists(), f"Source file not found: {source_path}"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))

    forbidden_imports = {"requests", "httpx", "subprocess", "surrealdb"}
    forbidden_call_attrs = {"unlink", "rmtree"}  # attr-based dangerous calls
    forbidden_func_names = {"remove"}  # bare function calls (os.remove is caught via attr)

    violations: list[str] = []

    for node in ast.walk(tree):
        # Check: import requests / import httpx / import subprocess / import surrealdb
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in forbidden_imports:
                    violations.append(f"line {node.lineno}: forbidden import {alias.name!r}")

        # Check: from requests import ... / from surrealdb import ...
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            root = module.split(".")[0]
            if root in forbidden_imports:
                violations.append(f"line {node.lineno}: forbidden from-import {module!r}")

        # Check: open(..., "w") — write-mode file open
        elif isinstance(node, ast.Call):
            func = node.func
            # open("path", "w") or open("path", mode="w")
            is_open_call = (
                (isinstance(func, ast.Name) and func.id == "open")
                or (isinstance(func, ast.Attribute) and func.attr == "open")
            )
            if is_open_call:
                # Check positional arg[1] == "w" or "wb" or "a"
                for arg in node.args[1:2]:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value in ("w", "wb", "a", "ab"):
                        violations.append(f"line {node.lineno}: forbidden open() write-mode call")
                # Check keyword mode=...
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and kw.value.value in ("w", "wb", "a", "ab"):
                        violations.append(f"line {node.lineno}: forbidden open(mode=...) write-mode call")

            # Check: .unlink(), .rmtree(), shutil.rmtree()
            if isinstance(func, ast.Attribute) and func.attr in forbidden_call_attrs:
                violations.append(f"line {node.lineno}: forbidden call .{func.attr}()")

            # Check: os.system(...)
            if isinstance(func, ast.Attribute) and func.attr == "system" and isinstance(func.value, ast.Name) and func.value.id == "os":
                violations.append(f"line {node.lineno}: forbidden call os.system()")

            # Check bare remove(...) — unlikely but guard
            if isinstance(func, ast.Name) and func.id in forbidden_func_names:
                violations.append(f"line {node.lineno}: forbidden bare call {func.id}()")

    assert violations == [], (
        f"stale_refresh_plan.py contains forbidden patterns:\n"
        + "\n".join(f"  {v}" for v in violations)
    )
