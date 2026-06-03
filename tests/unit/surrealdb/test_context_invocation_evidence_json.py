"""Unit tests for machine-readable invocation JSON evidence (#2850)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from tools.surrealdb import context_invocation_evidence_json as evidence_json
from tools.surrealdb import context_live_invocation_harness as harness
from tools.surrealdb.db_record_evidence_contract import (
    ACCEPTED_LIMITATION_CODES,
    validate_db_record_evidence_claim,
)

pytestmark = pytest.mark.unit

_REQUIRED_TOP_LEVEL = frozenset(
    {
        "schema_version",
        "run_id_or_invocation_id",
        "profile",
        "final_verdict",
        "started_at_or_observed_at",
        "tool_invocations",
        "evidence_claims",
        "limits",
        "accepted_limitations",
        "missing_evidence_codes",
        "summary_counts",
        "determinism_hash",
        "redaction_summary",
        "limitations",
    }
)


def _mock_matrix(
    monkeypatch: pytest.MonkeyPatch,
    *,
    profile: harness.InvocationProfile,
    execute_fn,
) -> harness.HarnessReport:
    registry_names = sorted(harness.invocations_for_profile(profile).keys())
    bridge = MagicMock()
    bridge.list_tools.return_value = [{"name": n} for n in registry_names]
    bridge.execute_tool.side_effect = execute_fn
    monkeypatch.setattr(harness, "create_bridge", lambda: bridge)
    monkeypatch.setattr(
        harness,
        "_git_metadata",
        lambda _root: {
            "git_sha": "deadbeefdeadbeef",
            "branch": "test",
            "worktree_clean": True,
            "git_available": True,
        },
    )
    return harness.run_matrix(
        live=True,
        profile=profile,
        fail_on_limits=profile == "full",
    )


def test_minimal_json_pass_with_limits_and_six_accepted_limitations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _execute(tool_name: str, parameters: dict) -> dict:
        if tool_name == "cdb_context_memory_write_intent":
            return {"status": "refused", "code": "agent_memory_write_not_activated"}
        if tool_name in harness.BENCHMARK_FULL_RECORD_OVERRIDES:
            code = "missing_records"
            if tool_name == "cdb_context_evidence_resolve":
                code = "missing_evidence_records"
            elif tool_name == "cdb_context_claim_resolve":
                code = "missing_claim_records"
            elif tool_name == "cdb_context_memory_get":
                code = "missing_memory_records"
            elif tool_name.startswith("cdb_context_decision"):
                code = "missing_decision_events"
            return {"status": "error", "error": {"code": code}}
        return {"status": "ok", "tool": tool_name}

    report = _mock_matrix(monkeypatch, profile="minimal", execute_fn=_execute)
    doc = evidence_json.build_invocation_evidence(report)

    assert doc["schema_version"] == evidence_json.SCHEMA_VERSION
    assert doc["profile"] == "minimal"
    assert doc["final_verdict"] == "PASS_WITH_LIMITS"
    assert set(_REQUIRED_TOP_LEVEL) <= set(doc.keys())
    assert len(doc["accepted_limitations"]) == 6
    assert len(doc["evidence_claims"]) == 6
    assert set(doc["missing_evidence_codes"]) <= set(ACCEPTED_LIMITATION_CODES)
    for claim in doc["evidence_claims"]:
        assert not validate_db_record_evidence_claim(claim)
        assert claim["trust_classification"] == "accepted_limitation"
        assert claim["record_source"] in ("in_memory", "repo-only")
        assert not claim.get("record_ids")


def test_full_json_pass_zero_accepted_limitations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _execute(tool_name: str, parameters: dict) -> dict:
        if tool_name == "cdb_context_memory_write_intent":
            return {
                "status": "refused",
                "code": "agent_memory_write_not_activated",
            }
        return {"status": "ok", "tool": tool_name}

    report = _mock_matrix(monkeypatch, profile="full", execute_fn=_execute)
    doc = evidence_json.build_invocation_evidence(report)

    assert doc["final_verdict"] == "PASS"
    assert doc["accepted_limitations"] == []
    assert doc["evidence_claims"] == []
    assert doc["missing_evidence_codes"] == []
    assert report.summary.get("PASS_WITH_LIMITS", 0) == 0


def test_determinism_hash_stable_for_equivalent_report() -> None:
    base = harness.HarnessReport(
        timestamp="2026-06-03T12:00:00Z",
        git_sha="abc123",
        branch="main",
        worktree_clean=True,
        tool_count=27,
        expected_tool_count=27,
        profile="minimal",
        matrix=[
            harness.MatrixRow(
                tool_name="cdb_context_evidence_resolve",
                call={"evidence_id": "ev1"},
                expected="fail-closed",
                actual="missing_evidence_records",
                status="PASS_WITH_LIMITS",
                error_code="missing_evidence_records",
            )
        ],
        summary={"PASS": 21, "PASS_WITH_LIMITS": 6, "FAIL": 0, "BLOCKED_SAFETY": 0},
        final_verdict="pass",
    )
    doc_a = evidence_json.build_invocation_evidence(base)
    other = harness.HarnessReport(
        timestamp="2026-06-04T99:99:99Z",
        git_sha=base.git_sha,
        branch=base.branch,
        worktree_clean=base.worktree_clean,
        tool_count=base.tool_count,
        expected_tool_count=base.expected_tool_count,
        profile=base.profile,
        matrix=base.matrix,
        summary=base.summary,
        final_verdict=base.final_verdict,
    )
    doc_b = evidence_json.build_invocation_evidence(other)
    assert doc_a["determinism_hash"] == doc_b["determinism_hash"]
    assert doc_a[
        "determinism_hash"
    ] == evidence_json.compute_aggregate_determinism_hash(doc_a)


def test_json_output_has_no_secret_substrings() -> None:
    report = harness.HarnessReport(
        timestamp="2026-06-03T00:00:00Z",
        git_sha="abc",
        branch="main",
        worktree_clean=True,
        tool_count=1,
        expected_tool_count=27,
        matrix=[
            harness.MatrixRow(
                tool_name="context.search",
                call={"query": "benchmark"},
                expected="ok",
                actual="status=ok",
                status="PASS",
            )
        ],
    )
    payload = evidence_json.serialize_invocation_evidence(report)
    lowered = payload.lower()
    assert "password=" not in lowered
    assert "api_key=" not in lowered
    assert "bearer " not in lowered


def test_format_report_json_emits_evidence_schema() -> None:
    report = harness.HarnessReport(
        timestamp="2026-06-03T00:00:00Z",
        git_sha="abc",
        branch="main",
        worktree_clean=True,
        tool_count=1,
        expected_tool_count=27,
        matrix=[
            harness.MatrixRow(
                tool_name="context.search",
                call={"query": "x"},
                expected="ok",
                actual="status=ok",
                status="PASS",
            )
        ],
    )
    payload = harness.format_report(report, "json")
    doc = json.loads(payload)
    assert doc["schema_version"] == evidence_json.SCHEMA_VERSION
    assert "determinism_hash" in doc
