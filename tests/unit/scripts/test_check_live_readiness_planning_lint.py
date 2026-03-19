"""Tests for check_live_readiness_planning_lint.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "governance"))

from check_live_readiness_planning_lint import (
    ISSUES_PATH,
    ROADMAP_PATH,
    TASKS_PATH,
    lint,
    main,
)


def test_current_repo_planning_lint_passes() -> None:
    assert lint() == []
    assert main() == 0


def test_lint_detects_missing_phase_mapping_and_issue_index_drift(
    tmp_path: Path,
) -> None:
    roadmap = tmp_path / "ROADMAP.yaml"
    roadmap.write_text(
        """
goal: "Live Readiness"
phases:
  - id: P0
    name: Preconditions
    issues: [LR-001, LR-002, LR-003]
  - id: P1
    name: Tests
    issues: [LR-010]
""".strip(),
        encoding="utf-8",
    )

    tasks = tmp_path / "LR-TASKS.yaml"
    tasks.write_text(
        """
spec_version: "1.0"
tasks:
  - task_id: "LR-001"
    task_title: "P0 Governance CI/CD Shield"
  - task_id: "LR-004"
    task_title: "P0 Deterministic Completion Mechanism"
  - task_id: "LR-006"
    task_title: "P0 Deterministic Decision Traceability Contract"
""".strip(),
        encoding="utf-8",
    )

    issues = tmp_path / "ISSUES.md"
    issues.write_text(
        """
Derived planning index only. Canonical phase order and issue membership live in
`ROADMAP.yaml`. Do not use this file as task-status source; use
`LR-TASKS.yaml` + `LR-*-STATE.yaml`.

LR-001 – Enforce CI Required Checks (no bypass)
LR-010 – Risk Engine Unit Test Coverage
""".strip(),
        encoding="utf-8",
    )

    failures = lint(roadmap_path=roadmap, tasks_path=tasks, issues_path=issues)

    assert any("LR-004 has explicit phase P0" in failure for failure in failures)
    assert any("LR-006 has explicit phase P0" in failure for failure in failures)
    assert any("roadmap-derived issue order drift" in failure for failure in failures)


def test_lint_detects_missing_issues_pointer_markers(tmp_path: Path) -> None:
    roadmap = tmp_path / "ROADMAP.yaml"
    roadmap.write_text(ROADMAP_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    tasks = tmp_path / "LR-TASKS.yaml"
    tasks.write_text(TASKS_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    issues = tmp_path / "ISSUES.md"
    issues.write_text("LR-001 – Example only\n", encoding="utf-8")

    failures = lint(roadmap_path=roadmap, tasks_path=tasks, issues_path=issues)

    assert any(
        "missing marker 'Derived planning index only.'" in failure
        for failure in failures
    )
    assert any("missing marker 'ROADMAP.yaml'" in failure for failure in failures)
