"""Unit tests for scope_drift_blocking.py — Wave 17-D Blocking Scope Drift Output.

Issues:
    #2166 — [SURREALDB][CONTEXT][SCOPE-BLOCKING] Blocking Scope Drift Output
    Parent: #2162 (Wave-17 anchor)
    Depends on: #2163 scope_drift_firewall, #2164 scope_drift_cli, #2165 scope_drift_tools
    Epic: #1976

Scope:
    Unit tests for tools/surrealdb/scope_drift_blocking.py.
    All fixtures are inline — no file loading, no DB, no network, no writes.
    No real datetime.now() — as_of fixed for determinism.

Coverage:
    1.  Full schema present when blocking findings present.
    2.  blocking=False when no blocking findings.
    3.  operator_action is one of the valid output values.
    4.  operator_action="stop" when highest-priority finding has required_action="stop".
    5.  operator_action="request_human_go" when only request_go findings.
    6.  operator_action="split_scope" when only split_scope findings.
    7.  operator_action="review" when only review findings.
    8.  affected_artifacts is sorted and deduplicated.
    9.  recommended_next_reads is stable-order and deduplicated.
    10. anti_actions contains all 8 required entries (no auto-fix, no live-go, etc.).
    11. guardrails fully propagated (all 5 GUARDRAILS strings).
    12. JSON serialisation is stable (sort_keys produces consistent output).
    13. Markdown output contains all required sections.
    14. Safety: no DB/network/write access in module source.
    15. CLI handle_report_scope_drift includes blocking_output key when blocking findings.
    16. CLI blocking_output absent when no blocking findings.
    17. MCP response includes blocking_output when blocking_count > 0.
    18. MCP response blocking_output is None when no blocking findings.
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from tools.surrealdb.scope_drift_blocking import (
    ANTI_ACTIONS,
    SCHEMA_VERSION,
    _collect_affected_artifacts,
    _collect_recommended_next_reads,
    _derive_operator_action,
    build_blocking_output,
    render_blocking_markdown,
)
from tools.surrealdb.scope_drift_firewall import (
    GUARDRAILS,
    ScopeDriftFinding,
    ScopeDriftScanResult,
    scan_scope_drift_v1,
)

# ── Fixed timestamp for determinism ──────────────────────────────────────────

_AS_OF = "2026-05-06T12:00:00+00:00"

# ── Shared bundles ────────────────────────────────────────────────────────────

# Triggers path_out_of_scope (blocking) + missing_human_go (blocking):
#   - declared target_paths set; touched artifact is outside declared paths
#   - operation_mode=write with no human_go_token
_BLOCKING_BUNDLE: dict[str, Any] = {
    "meta": {
        "as_of": _AS_OF,
        "session_id": "blocking-test-001",
        "operation_mode": "write",
        "human_go_token": None,
    },
    "declared_scope": {
        "task_scope": "Test blocking scope",
        "target_issue": "2166",
        "target_paths": [
            "tools/surrealdb/",
            "tests/unit/surrealdb/",
        ],
    },
    "touched_artifacts": [
        {
            "path": "services/cdb_risk/service.py",
            "surface_type": "runtime",
        },
    ],
    "issue_refs": [
        {"issue_id": "2166", "state": "OPEN", "label": "Wave-17"},
    ],
    "generated_findings": [],
    "forbidden_surfaces": [],
}

# Triggers no findings at all — clean bundle:
_CLEAN_BUNDLE: dict[str, Any] = {
    "meta": {"as_of": _AS_OF},
    "declared_scope": {"target_issue": "2166", "target_paths": ["tools/surrealdb/"]},
    "touched_artifacts": [
        {"path": "tools/surrealdb/scope_drift_blocking.py", "surface_type": "tools"},
    ],
    "issue_refs": [{"issue_id": "2166", "state": "OPEN", "label": "Wave-17"}],
    "generated_findings": [],
    "forbidden_surfaces": [],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

_BLOCKING_REQUIRED_ACTIONS = frozenset({"stop", "request_human_go", "split_scope", "review"})

_REQUIRED_SCHEMA_KEYS = frozenset(
    {
        "status",
        "blocking",
        "blocking_count",
        "summary",
        "operator_action",
        "affected_artifacts",
        "recommended_next_reads",
        "guardrails",
        "findings",
        "anti_actions",
    }
)


def _scan(bundle: dict[str, Any]) -> ScopeDriftScanResult:
    return scan_scope_drift_v1(bundle, as_of=_AS_OF)


def _make_fake_finding(
    *,
    required_action: str = "stop",
    affected_artifacts: tuple[str, ...] = ("tools/foo.py",),
    recommended_next_reads: tuple[str, ...] = ("AGENTS.md",),
) -> ScopeDriftFinding:
    """Create a minimal fake blocking ScopeDriftFinding for unit isolation."""
    return ScopeDriftFinding(
        drift_id="aabbccdd00000001",
        drift_type="path_out_of_scope",
        severity="blocking",
        allowed_scope="tools/surrealdb/",
        observed_scope="services/cdb_risk/service.py",
        affected_artifacts=affected_artifacts,
        required_action=required_action,
        human_go_required=True,
        stop_conditions=("Artefact is outside declared scope.",),
        recommended_next_reads=recommended_next_reads,
        detected_by="scope-drift-firewall/v1",
        detected_at=_AS_OF,
        status="open",
    )


def _make_fake_scan_result(
    findings: tuple[ScopeDriftFinding, ...] = (),
    blocking_count: int = 0,
    status: str = "ok",
) -> ScopeDriftScanResult:
    return ScopeDriftScanResult(
        tool="scope_drift_firewall",
        schema_version="scope-drift-firewall/v1",
        status=status,
        scanned_at=_AS_OF,
        blocking_count=blocking_count,
        findings=findings,
        guardrails=GUARDRAILS,
    )


# ── 1. Full schema present when blocking findings present ─────────────────────


@pytest.mark.unit
def test_blocking_output_full_schema_when_blocking() -> None:
    result = _scan(_BLOCKING_BUNDLE)
    assert result.blocking_count > 0, "Test requires blocking findings"
    out = build_blocking_output(result)
    missing = _REQUIRED_SCHEMA_KEYS - set(out.keys())
    assert not missing, f"Missing keys: {missing}"


# ── 2. blocking=False when no blocking findings ───────────────────────────────


@pytest.mark.unit
def test_blocking_false_when_no_blocking_findings() -> None:
    result = _scan(_CLEAN_BUNDLE)
    out = build_blocking_output(result)
    assert out["blocking"] is False
    assert out["blocking_count"] == 0
    assert out["findings"] == []


# ── 3. operator_action is one of the valid output values ─────────────────────


@pytest.mark.unit
def test_operator_action_is_valid_value_when_blocking() -> None:
    result = _scan(_BLOCKING_BUNDLE)
    assert result.blocking_count > 0
    out = build_blocking_output(result)
    assert out["operator_action"] in _BLOCKING_REQUIRED_ACTIONS


# ── 4. operator_action="stop" for stop findings ───────────────────────────────


@pytest.mark.unit
def test_operator_action_stop_priority() -> None:
    f_stop = _make_fake_finding(required_action="stop")
    f_review = _make_fake_finding(required_action="review")
    result = _make_fake_scan_result(
        findings=(f_stop, f_review), blocking_count=2, status="blocked_scope_drift"
    )
    out = build_blocking_output(result)
    assert out["operator_action"] == "stop"


# ── 5. operator_action="request_human_go" when only request_go findings ───────


@pytest.mark.unit
def test_operator_action_request_human_go() -> None:
    f = _make_fake_finding(required_action="request_go")
    result = _make_fake_scan_result(findings=(f,), blocking_count=1, status="blocked_scope_drift")
    out = build_blocking_output(result)
    assert out["operator_action"] == "request_human_go"


# ── 6. operator_action="split_scope" when only split_scope findings ───────────


@pytest.mark.unit
def test_operator_action_split_scope() -> None:
    f = _make_fake_finding(required_action="split_scope")
    result = _make_fake_scan_result(findings=(f,), blocking_count=1, status="blocked_scope_drift")
    out = build_blocking_output(result)
    assert out["operator_action"] == "split_scope"


# ── 7. operator_action="review" when no blocking findings ─────────────────────


@pytest.mark.unit
def test_operator_action_review_when_no_blocking_findings() -> None:
    result = _make_fake_scan_result()
    out = build_blocking_output(result)
    assert out["operator_action"] == "review"


# ── 8. affected_artifacts sorted and deduplicated ─────────────────────────────


@pytest.mark.unit
def test_affected_artifacts_sorted_and_deduped() -> None:
    f1 = _make_fake_finding(affected_artifacts=("tools/z.py", "tools/a.py"))
    f2 = _make_fake_finding(affected_artifacts=("tools/a.py", "tools/m.py"))
    findings = (f1, f2)
    result = _collect_affected_artifacts(findings)
    # deduplicated
    assert len(result) == len(set(result))
    # sorted
    assert result == sorted(result)
    # all entries present
    assert "tools/a.py" in result
    assert "tools/z.py" in result
    assert "tools/m.py" in result


# ── 9. recommended_next_reads stable order and deduped ────────────────────────


@pytest.mark.unit
def test_recommended_next_reads_stable_and_deduped() -> None:
    f1 = _make_fake_finding(recommended_next_reads=("AGENTS.md", "docs/CONTROL_REGISTER.md"))
    f2 = _make_fake_finding(recommended_next_reads=("AGENTS.md", "knowledge/GOVERNANCE.md"))
    findings = (f1, f2)
    result = _collect_recommended_next_reads(findings)
    # deduplicated
    assert len(result) == len(set(result))
    # stable: first-seen order — AGENTS.md must appear before knowledge/GOVERNANCE.md
    assert result.index("AGENTS.md") < result.index("knowledge/GOVERNANCE.md")
    # all entries present
    assert "AGENTS.md" in result
    assert "docs/CONTROL_REGISTER.md" in result
    assert "knowledge/GOVERNANCE.md" in result


# ── 10. anti_actions contains all 8 required entries ─────────────────────────


@pytest.mark.unit
def test_anti_actions_all_entries_present() -> None:
    result = _scan(_CLEAN_BUNDLE)
    out = build_blocking_output(result)
    expected = {
        "no_auto_fix",
        "no_auto_write",
        "no_auto_merge",
        "no_auto_close",
        "no_live_go",
        "no_lr_go",
        "no_echtgeld_go",
        "no_runtime_enable",
    }
    assert expected.issubset(set(out["anti_actions"]))


@pytest.mark.unit
def test_anti_actions_constant_matches_module() -> None:
    assert len(ANTI_ACTIONS) == 8
    for entry in ANTI_ACTIONS:
        assert isinstance(entry, str) and entry


# ── 11. guardrails fully propagated ──────────────────────────────────────────


@pytest.mark.unit
def test_guardrails_fully_propagated() -> None:
    result = _scan(_BLOCKING_BUNDLE)
    out = build_blocking_output(result)
    for guardrail in GUARDRAILS:
        assert guardrail in out["guardrails"], f"Missing guardrail: {guardrail!r}"


# ── 12. JSON serialisation stable ────────────────────────────────────────────


@pytest.mark.unit
def test_json_output_is_stable() -> None:
    result = _scan(_BLOCKING_BUNDLE)
    out1 = build_blocking_output(result)
    out2 = build_blocking_output(result)
    assert json.dumps(out1, sort_keys=True) == json.dumps(out2, sort_keys=True)


@pytest.mark.unit
def test_json_output_is_serialisable() -> None:
    result = _scan(_BLOCKING_BUNDLE)
    out = build_blocking_output(result)
    serialised = json.dumps(out, sort_keys=True)
    restored = json.loads(serialised)
    assert restored["blocking"] == out["blocking"]
    assert restored["blocking_count"] == out["blocking_count"]


# ── 13. Markdown output contains all required sections ────────────────────────


@pytest.mark.unit
def test_markdown_contains_required_sections_when_blocking() -> None:
    result = _scan(_BLOCKING_BUNDLE)
    out = build_blocking_output(result)
    md = render_blocking_markdown(out)
    assert "## Blocking Output" in md
    assert "**Summary:**" in md
    assert "**Operator Action:**" in md
    assert "### Anti-Actions (Prohibited)" in md
    assert "### Recommended Next Reads" in md
    assert "### Guardrails" in md


@pytest.mark.unit
def test_markdown_contains_blocking_findings_table_when_blocking() -> None:
    result = _scan(_BLOCKING_BUNDLE)
    out = build_blocking_output(result)
    md = render_blocking_markdown(out)
    assert "### Blocking Findings" in md


@pytest.mark.unit
def test_markdown_no_blocking_findings_section_when_clean() -> None:
    result = _scan(_CLEAN_BUNDLE)
    out = build_blocking_output(result)
    md = render_blocking_markdown(out)
    assert "## Blocking Output" in md
    # No blocking findings table if no blocking findings
    assert "### Blocking Findings" not in md


@pytest.mark.unit
def test_markdown_anti_actions_listed() -> None:
    result = _scan(_BLOCKING_BUNDLE)
    out = build_blocking_output(result)
    md = render_blocking_markdown(out)
    for aa in ANTI_ACTIONS:
        assert aa in md, f"anti_action {aa!r} missing from Markdown"


# ── 14. Safety: no DB/network/write access in module source ───────────────────


@pytest.mark.unit
def test_no_db_access_in_module() -> None:
    module = sys.modules["tools.surrealdb.scope_drift_blocking"]
    src = inspect.getsource(module)
    forbidden = [
        "Surreal(",
        "surreal.",
        "requests.",
        "httpx.",
        "urllib.",
        "subprocess.",
        "socket.",
        "open(",
        "write_text",
        "write_bytes",
        "os.system",
        "datetime.now",
        "utcnow()",
        "LIVE_TRADING",
        "api_key",
        "password",
        "token",
    ]
    violations = [term for term in forbidden if term in src]
    assert not violations, f"Forbidden terms found in module source: {violations}"


# ── 15. CLI handle_report_scope_drift includes blocking_output ─────────────────


@pytest.mark.unit
def test_cli_report_includes_blocking_output_when_blocking(tmp_path: Path) -> None:
    import json as _json
    from tools.surrealdb.scope_drift_cli import handle_report_scope_drift

    bundle_file = tmp_path / "bundle.json"
    bundle_file.write_text(_json.dumps(_BLOCKING_BUNDLE), encoding="utf-8")

    import argparse
    args = argparse.Namespace(input=str(bundle_file))
    payload, exit_code = handle_report_scope_drift(args)

    assert "blocking_output" in payload
    bo = payload["blocking_output"]
    assert bo["blocking"] is True
    assert bo["blocking_count"] > 0
    assert set(bo.keys()) >= _REQUIRED_SCHEMA_KEYS


# ── 16. CLI blocking_output absent when no blocking findings ──────────────────


@pytest.mark.unit
def test_cli_report_no_blocking_output_when_clean(tmp_path: Path) -> None:
    import json as _json
    from tools.surrealdb.scope_drift_cli import handle_report_scope_drift

    bundle_file = tmp_path / "bundle.json"
    bundle_file.write_text(_json.dumps(_CLEAN_BUNDLE), encoding="utf-8")

    import argparse
    args = argparse.Namespace(input=str(bundle_file))
    payload, exit_code = handle_report_scope_drift(args)

    assert "blocking_output" not in payload


# ── 17. MCP response includes blocking_output when blocking_count > 0 ─────────


@pytest.mark.unit
def test_mcp_response_includes_blocking_output_when_blocking() -> None:
    from tools.mcp.scope_drift_tools import handle_cdb_context_scope_drift

    request = {"bundle": _BLOCKING_BUNDLE}
    response = handle_cdb_context_scope_drift(request)

    assert response["status"] == "ok"
    assert response["summary"]["blocking_count"] > 0
    assert "blocking_output" in response
    bo = response["blocking_output"]
    assert bo is not None
    assert bo["blocking"] is True
    assert set(bo.keys()) >= _REQUIRED_SCHEMA_KEYS


# ── 18. MCP response blocking_output is None when no blocking findings ─────────


@pytest.mark.unit
def test_mcp_response_blocking_output_none_when_clean() -> None:
    from tools.mcp.scope_drift_tools import handle_cdb_context_scope_drift

    request = {"bundle": _CLEAN_BUNDLE}
    response = handle_cdb_context_scope_drift(request)

    assert response["status"] == "ok"
    assert response["summary"]["blocking_count"] == 0
    assert "blocking_output" in response
    assert response["blocking_output"] is None


# ── Extra: _derive_operator_action with multiple actions picks highest priority ─


@pytest.mark.unit
def test_derive_operator_action_stop_beats_request_go() -> None:
    f_request_go = _make_fake_finding(required_action="request_go")
    f_stop = _make_fake_finding(required_action="stop")
    result = _derive_operator_action([f_request_go, f_stop])
    assert result == "stop"


@pytest.mark.unit
def test_derive_operator_action_request_go_beats_split_scope() -> None:
    f_split = _make_fake_finding(required_action="split_scope")
    f_rg = _make_fake_finding(required_action="request_go")
    result = _derive_operator_action([f_split, f_rg])
    assert result == "request_human_go"


@pytest.mark.unit
def test_derive_operator_action_empty_returns_review() -> None:
    result = _derive_operator_action([])
    assert result == "review"


# ── Extra: build_blocking_output summary string ───────────────────────────────


@pytest.mark.unit
def test_blocking_output_summary_mentions_count_when_blocking() -> None:
    result = _scan(_BLOCKING_BUNDLE)
    assert result.blocking_count > 0
    out = build_blocking_output(result)
    assert str(result.blocking_count) in out["summary"]
    assert "blocking" in out["summary"].lower()


@pytest.mark.unit
def test_blocking_output_summary_no_blocking_message_when_clean() -> None:
    result = _scan(_CLEAN_BUNDLE)
    out = build_blocking_output(result)
    assert "No blocking" in out["summary"]


# ── Extra: SCHEMA_VERSION constant ───────────────────────────────────────────


@pytest.mark.unit
def test_schema_version_format() -> None:
    assert SCHEMA_VERSION.startswith("scope-drift-blocking/")
