"""Unit tests for context live invocation regression harness (#2849)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tools.surrealdb import context_live_invocation_harness as harness

pytestmark = pytest.mark.unit


def test_benchmark_manifest_covers_expected_tool_count() -> None:
    assert len(harness.BENCHMARK_SAFE_INVOCATIONS) == harness.EXPECTED_TOOL_COUNT
    assert (
        len(harness.invocations_for_profile("minimal")) == harness.EXPECTED_TOOL_COUNT
    )
    assert len(harness.invocations_for_profile("full")) == harness.EXPECTED_TOOL_COUNT


def test_full_profile_overrides_six_wave14_tools() -> None:
    assert len(harness.BENCHMARK_FULL_RECORD_OVERRIDES) == 6
    minimal = harness.invocations_for_profile("minimal")
    full = harness.invocations_for_profile("full")
    for tool in harness.BENCHMARK_FULL_RECORD_OVERRIDES:
        assert minimal[tool] != full[tool]


def test_classify_ok_and_limits() -> None:
    assert (
        harness.classify_tool_result(
            "context.search", {"tool": "context.search", "status": "ok"}
        )
        == "PASS"
    )
    assert (
        harness.classify_tool_result(
            "cdb_context_evidence_resolve",
            {
                "status": "error",
                "error": {"code": "missing_evidence_records"},
            },
        )
        == "PASS_WITH_LIMITS"
    )
    assert (
        harness.classify_tool_result(
            "cdb_context_memory_write_intent",
            {"status": "refused", "code": "agent_memory_write_not_activated"},
        )
        == "PASS"
    )
    assert (
        harness.classify_tool_result(
            "cdb_context_scope_drift",
            {
                "status": "error",
                "error": {"code": "scan_error", "message": "boom"},
            },
        )
        == "FAIL"
    )
    assert (
        harness.classify_tool_result(
            "context.briefing",
            {"status": "error", "error": {"code": "invalid_task_id"}},
        )
        == "FAIL"
    )


def test_compute_exit_code_pass_and_fail() -> None:
    ok = harness.HarnessReport(
        timestamp="2026-06-03T00:00:00Z",
        git_sha="abc",
        branch="main",
        worktree_clean=True,
        tool_count=27,
        expected_tool_count=27,
        final_verdict="pass",
    )
    fail = harness.HarnessReport(
        timestamp="2026-06-03T00:00:00Z",
        git_sha="abc",
        branch="main",
        worktree_clean=True,
        tool_count=27,
        expected_tool_count=27,
        final_verdict="fail",
    )
    assert harness.compute_exit_code(ok) == 0
    assert harness.compute_exit_code(fail) == 1


def test_run_matrix_live_mock_all_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    registry_names = sorted(harness.BENCHMARK_SAFE_INVOCATIONS.keys())
    bridge = MagicMock()
    bridge.list_tools.return_value = [{"name": n} for n in registry_names]

    def _execute(tool_name: str, parameters: dict) -> dict:
        if tool_name == "cdb_context_memory_write_intent":
            return {"status": "refused", "code": "agent_memory_write_not_activated"}
        if tool_name in {
            "cdb_context_evidence_resolve",
            "cdb_context_claim_resolve",
            "cdb_context_memory_get",
            "cdb_context_decision_history",
            "cdb_context_decision_replay",
            "cdb_context_contradictions",
        }:
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

    bridge.execute_tool.side_effect = _execute
    monkeypatch.setattr(harness, "create_bridge", lambda: bridge)
    monkeypatch.setattr(
        harness,
        "_git_metadata",
        lambda _root: {
            "git_sha": "deadbeef",
            "branch": "test",
            "worktree_clean": True,
            "git_available": True,
        },
    )

    report = harness.run_matrix(live=True, profile="minimal")
    assert report.final_verdict == "pass"
    assert report.tool_count == 27
    assert report.summary.get("FAIL", 0) == 0
    assert report.profile == "minimal"
    assert report.safety_flags["PERSIST_ALLOWED"] is False
    assert report.safety_flags["MUTATION_ALLOWED"] is False


def test_run_matrix_full_profile_mock_all_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    registry_names = sorted(harness.invocations_for_profile("full").keys())
    bridge = MagicMock()
    bridge.list_tools.return_value = [{"name": n} for n in registry_names]

    def _execute(tool_name: str, parameters: dict) -> dict:
        if tool_name == "cdb_context_memory_write_intent":
            return {
                "status": "refused",
                "code": "agent_memory_write_not_activated",
            }
        return {"status": "ok", "tool": tool_name}

    bridge.execute_tool.side_effect = _execute
    monkeypatch.setattr(harness, "create_bridge", lambda: bridge)
    monkeypatch.setattr(
        harness,
        "_git_metadata",
        lambda _root: {
            "git_sha": "deadbeef",
            "branch": "test",
            "worktree_clean": True,
            "git_available": True,
        },
    )
    report = harness.run_matrix(live=True, profile="full", fail_on_limits=True)
    assert report.final_verdict == "pass"
    assert report.summary.get("PASS_WITH_LIMITS", 0) == 0


def test_run_matrix_fails_when_registry_missing_manifest_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge = MagicMock()
    bridge.list_tools.return_value = [
        {"name": "context.search"},
        {"name": "context.unlisted_tool"},
    ]
    bridge.execute_tool.return_value = {"status": "ok"}
    monkeypatch.setattr(harness, "create_bridge", lambda: bridge)
    monkeypatch.setattr(
        harness,
        "_git_metadata",
        lambda _root: {
            "git_sha": "x",
            "branch": "main",
            "worktree_clean": True,
            "git_available": True,
        },
    )
    report = harness.run_matrix(live=True, profile="minimal")
    assert report.final_verdict == "fail"
    assert report.missing_from_manifest == ["context.unlisted_tool"]


def test_format_report_json_emits_machine_readable_evidence() -> None:
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
    assert "tool-invocation-evidence/v1" in payload
    assert '"context.search"' in payload
    assert "determinism_hash" in payload
