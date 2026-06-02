"""Unit tests for context operator certification proof pack (#2776)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.mcp.registry import ContextToolRegistry, ToolDefinition
from tools.surrealdb import context_certify as certify

pytestmark = pytest.mark.unit

REQUIRED_TOP_LEVEL_KEYS = {
    "timestamp",
    "git_sha",
    "branch",
    "worktree_clean",
    "tool_count",
    "doctor_status",
    "bridge_status",
    "mcp_readonly_summary",
    "permission_guard_summary",
    "test_results",
    "gate_matrix",
    "skipped_checks_with_reason",
    "blocked_checks_with_reason",
    "safety_flags",
    "lr_note",
    "final_verdict",
}


def test_build_report_certified_by_default(tmp_path: Path) -> None:
    report = certify.build_report(tmp_path)
    payload = report.to_dict()
    assert REQUIRED_TOP_LEVEL_KEYS <= set(payload.keys())
    assert report.final_verdict == "certified"
    assert report.tool_count >= 1
    assert report.safety_flags["PERSIST_ALLOWED"] is False
    assert report.safety_flags["MUTATION_ALLOWED"] is False
    assert report.safety_flags["includes_context_smoke_db"] is False
    assert report.lr_note == "NO-GO"
    assert any(
        gate.check_id == "registry_all_read_only" and gate.status == "pass"
        for gate in report.gate_matrix
    )
    assert report.skipped_checks_with_reason
    assert not report.blocked_checks_with_reason


def test_compute_exit_code() -> None:
    ok = certify.CertifyReport(
        timestamp="2026-06-01T00:00:00Z",
        git_sha="abc",
        branch="main",
        worktree_clean=True,
        tool_count=27,
        doctor_status={},
        bridge_status={},
        mcp_readonly_summary={},
        permission_guard_summary={},
        test_results={},
        final_verdict="certified",
    )
    fail = certify.CertifyReport(
        timestamp="2026-06-01T00:00:00Z",
        git_sha="abc",
        branch="main",
        worktree_clean=True,
        tool_count=27,
        doctor_status={},
        bridge_status={},
        mcp_readonly_summary={},
        permission_guard_summary={},
        test_results={},
        final_verdict="fail",
    )
    assert certify.compute_exit_code(ok) == 0
    assert certify.compute_exit_code(fail) == 1


def test_format_json_roundtrip(tmp_path: Path) -> None:
    report = certify.build_report(tmp_path)
    text = certify.format_report(report, "json")
    certify._validate_output_safe(text)
    parsed = json.loads(text)
    assert parsed["final_verdict"] == "certified"
    assert isinstance(parsed["gate_matrix"], list)


def test_main_exit_code_zero(tmp_path: Path) -> None:
    code = certify.main(["--repo-root", str(tmp_path), "--format", "json"])
    assert code == 0


def test_registry_failure_marks_fail(tmp_path: Path) -> None:
    bad_tool = ToolDefinition(
        name="context.bad_write",
        description="injected for certify test",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        read_only=False,
    )
    bridge_status = {
        "enforced": True,
        "tools_count": 1,
        "read_only_tools": [],
        "description": "mock",
    }
    with patch.object(ContextToolRegistry, "list_tools", return_value=[bad_tool]):
        with patch.object(
            ContextToolRegistry,
            "assert_read_only_consistency",
            side_effect=ValueError("non-read-only tools found"),
        ):
            with patch("tools.surrealdb.context_certify.create_bridge") as mock_bridge:
                mock_bridge.return_value.get_read_only_status.return_value = (
                    bridge_status
                )
                report = certify.build_report(tmp_path)
    assert report.final_verdict == "fail"
    assert report.blocked_checks_with_reason
    assert certify.compute_exit_code(report) == 1


def test_git_metadata_detects_dirty(tmp_path: Path) -> None:
    with patch.object(certify, "_git_metadata") as mock_git:
        mock_git.return_value = {
            "git_sha": "deadbeef",
            "branch": "feat/test",
            "worktree_clean": False,
            "git_available": True,
        }
        report = certify.build_report(tmp_path)
    assert report.git_sha == "deadbeef"
    assert report.worktree_clean is False


def test_test_command_suggestions_present(tmp_path: Path) -> None:
    report = certify.build_report(tmp_path)
    suggestions = report.test_results["test_command_suggestions"]
    assert any("test_context_certify" in cmd for cmd in suggestions)
    assert any("test_context_onboarding_doctor" in cmd for cmd in suggestions)
