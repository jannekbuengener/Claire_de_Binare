"""Unit tests for CDB Context Refresh Report Generator.

#3287
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.context.generate_context_refresh_report import (
    build_context_delta,
    build_validation_report,
    build_summary_md,
    build_safety_boundaries,
    SCHEMA_VERSION,
    VALIDATION_SCHEMA_VERSION,
)


def test_build_safety_boundaries() -> None:
    sb = build_safety_boundaries()
    assert sb["lr_status"] == "NO-GO"
    assert sb["board_stage_is_live_go"] is False
    assert sb["real_money_go"] is False
    assert sb["productive_db_writes_allowed"] is False
    assert sb["secrets_in_outputs_allowed"] is False
    assert sb["trading_state_ingestion_allowed"] is False


def test_build_context_delta_shape(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    delta = build_context_delta(
        repo_path=str(repo_dir),
        base_ref="origin/main",
        head_ref="HEAD",
        repo_name="Claire_de_Binare",
        utc_now="2026-06-17T12:00:00Z",
    )

    assert delta["schema_version"] == SCHEMA_VERSION
    assert delta["generated_at_utc"] == "2026-06-17T12:00:00Z"
    assert delta["base_ref"] == "origin/main"
    assert delta["head_ref"] == "HEAD"
    assert delta["repo"] == "Claire_de_Binare"

    assert "open_issues_summary" in delta
    assert "open_prs_summary" in delta
    assert "changed_canon_paths_if_available" in delta
    assert "limitations" in delta
    assert "safety_boundaries" in delta
    assert delta["safety_boundaries"]["lr_status"] == "NO-GO"


def test_build_context_delta_handles_empty_git(tmp_path: Path) -> None:
    repo_dir = tmp_path / "no-git"
    repo_dir.mkdir()

    delta = build_context_delta(
        repo_path=str(repo_dir),
        base_ref="origin/main",
        head_ref="HEAD",
        repo_name="Claire_de_Binare",
        utc_now="2026-06-17T12:00:00Z",
    )

    assert isinstance(delta["head_commit"], str)
    assert isinstance(delta["base_commit"], str)
    assert len(delta["limitations"]) >= 0


def test_build_validation_report_pass() -> None:
    delta = {
        "head_commit": "abc123",
        "base_commit": "def456",
        "open_issues_summary": {"issues": [{"number": 1, "title": "test"}]},
        "open_prs_summary": {"prs": [{"number": 2, "title": "test"}]},
        "limitations": [],
    }
    report = build_validation_report(delta, "/tmp/out")
    assert report["schema_version"] == VALIDATION_SCHEMA_VERSION
    assert report["status"] == "PASS"
    assert (
        report["validator_used"] == "tools/context/generate_context_refresh_report.py"
    )
    assert report["blocked_reasons"] == []
    assert "artifact_paths" in report


def test_build_validation_report_with_limitations() -> None:
    delta = {
        "head_commit": "abc123",
        "base_commit": "def456",
        "open_issues_summary": {"issues": []},
        "open_prs_summary": {"prs": []},
        "limitations": ["gh CLI not available"],
    }
    report = build_validation_report(delta, "/tmp/out")
    assert report["status"] == "PASS_WITH_LIMITATIONS"
    assert report["warnings"] != []


def test_build_summary_md_shape() -> None:
    delta = {
        "repo": "Claire_de_Binare",
        "base_ref": "origin/main",
        "head_ref": "HEAD",
        "base_commit": "abc123def456",
        "head_commit": "7890abcdef",
        "changed_canon_paths_if_available": ["AGENTS.md"],
        "open_issues_summary": {
            "total_count": 1,
            "issues": [
                {
                    "number": 1,
                    "title": "test issue",
                    "state": "OPEN",
                    "labels": ["type:docs"],
                    "updated_at": "",
                }
            ],
        },
        "open_prs_summary": {"total_count": 0, "prs": []},
        "limitations": [],
        "safety_boundaries": build_safety_boundaries(),
    }
    validation = build_validation_report(delta, "/tmp/out")
    md = build_summary_md(delta, validation, "2026-06-17T12:00:00Z")

    assert "# CDB Context Refresh Report" in md
    assert "2026-06-17T12:00:00Z" in md
    assert "Monday/Thursday" in md
    assert "NO-GO" in md
    assert "No Live-Go" in md
    assert "No Echtgeld-Go" in md
    assert "LR remains NO-GO" in md
    assert "#1" in md
    assert "test issue" in md
    assert "Changed canon paths" in md


def test_build_summary_md_contains_safety() -> None:
    delta = {
        "repo": "Claire_de_Binare",
        "base_ref": "origin/main",
        "head_ref": "HEAD",
        "base_commit": "a" * 40,
        "head_commit": "b" * 40,
        "changed_canon_paths_if_available": [],
        "open_issues_summary": {"total_count": 0, "issues": []},
        "open_prs_summary": {"total_count": 0, "prs": []},
        "limitations": [],
        "safety_boundaries": build_safety_boundaries(),
    }
    validation = build_validation_report(delta, "/tmp/out")
    md = build_summary_md(delta, validation, "2026-06-17T12:00:00Z")

    assert "lr_status" in md
    assert "NO-GO" in md
    assert "board_stage_is_live_go" in md


def test_context_delta_json_serializable(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    delta = build_context_delta(
        repo_path=str(repo_dir),
        base_ref="origin/main",
        head_ref="HEAD",
        repo_name="Claire_de_Binare",
        utc_now="2026-06-17T12:00:00Z",
    )

    json_str = json.dumps(delta, indent=2, ensure_ascii=False)
    parsed = json.loads(json_str)
    assert parsed["schema_version"] == SCHEMA_VERSION


def test_validation_report_json_serializable() -> None:
    delta = {
        "head_commit": "abc",
        "base_commit": "def",
        "open_issues_summary": {"issues": []},
        "open_prs_summary": {"prs": []},
        "limitations": [],
    }
    report = build_validation_report(delta, "/tmp/out")
    json_str = json.dumps(report, indent=2, ensure_ascii=False)
    parsed = json.loads(json_str)
    assert parsed["schema_version"] == VALIDATION_SCHEMA_VERSION


def test_summary_md_contains_berlin_time_reference() -> None:
    delta = {
        "repo": "Claire_de_Binare",
        "base_ref": "origin/main",
        "head_ref": "HEAD",
        "base_commit": "a" * 40,
        "head_commit": "b" * 40,
        "changed_canon_paths_if_available": [],
        "open_issues_summary": {"total_count": 0, "issues": []},
        "open_prs_summary": {"total_count": 0, "prs": []},
        "limitations": [],
        "safety_boundaries": build_safety_boundaries(),
    }
    validation = build_validation_report(delta, "/tmp/out")
    md = build_summary_md(delta, validation, "2026-06-17T08:00:00Z")
    assert "Europe/Berlin" in md
    assert "CEST" in md or "CET" in md


def test_no_live_go_in_summary() -> None:
    delta = {
        "repo": "Claire_de_Binare",
        "base_ref": "origin/main",
        "head_ref": "HEAD",
        "base_commit": "a" * 40,
        "head_commit": "b" * 40,
        "changed_canon_paths_if_available": [],
        "open_issues_summary": {"total_count": 0, "issues": []},
        "open_prs_summary": {"total_count": 0, "prs": []},
        "limitations": [],
        "safety_boundaries": build_safety_boundaries(),
    }
    validation = build_validation_report(delta, "/tmp/out")
    md = build_summary_md(delta, validation, "2026-06-17T08:00:00Z")
    assert "No Live-Go" in md
    assert "No Echtgeld-Go" in md
