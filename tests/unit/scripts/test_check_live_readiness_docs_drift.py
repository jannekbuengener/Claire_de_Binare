"""Tests for check_live_readiness_docs_drift.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "governance"))

from check_live_readiness_docs_drift import (
    GO_NO_GO_PATH,
    LR004_EVIDENCE_PATH,
    LR007_STATUS_PATH,
    README_PATH,
    ROOT,
    latest_audit_snapshot,
    main,
    require_markers,
)


def test_current_repo_live_readiness_pointers_pass() -> None:
    assert (
        require_markers(
            README_PATH,
            [
                "## Canonical Sources",
                "ROADMAP.yaml",
                "LR-TASKS.yaml",
                "LR-*-STATE.yaml",
                "## Derived Views",
                "GO_NO_GO.md",
                "LR-AUDIT-STATUS-*.md",
                "## Update Rule",
            ],
        )
        == []
    )
    assert (
        require_markers(
            GO_NO_GO_PATH,
            [
                "abgeleitete Entscheidungsansicht",
                "ROADMAP.yaml",
                "LR-TASKS.yaml",
                "LR-*-STATE.yaml",
                "Do not edit task state in this file.",
            ],
        )
        == []
    )
    assert (
        require_markers(
            LR004_EVIDENCE_PATH,
            [
                "Historical implementation snapshot only.",
                "Canonical task status lives in",
                "LR-004-STATE.yaml",
            ],
        )
        == []
    )
    assert (
        require_markers(
            LR007_STATUS_PATH,
            [
                "Historical task snapshot only.",
                "This file is not the global live-readiness",
                "Global Verdict Source:",
                "LR-AUDIT-STATUS-*.md",
            ],
        )
        == []
    )
    assert (
        require_markers(
            latest_audit_snapshot(ROOT),
            [
                "Historical snapshot only.",
                "LR-TASKS.yaml",
                "LR-*-STATE.yaml",
                "Do not edit task state here.",
            ],
        )
        == []
    )
    assert main() == 0


def test_require_markers_reports_missing_pointer(tmp_path: Path) -> None:
    sample = tmp_path / "README.md"
    sample.write_text("## Canonical Sources\nROADMAP.yaml\n", encoding="utf-8")

    failures = require_markers(
        sample,
        [
            "## Canonical Sources",
            "ROADMAP.yaml",
            "LR-TASKS.yaml",
            "## Derived Views",
        ],
    )

    assert len(failures) == 2
    assert any("LR-TASKS.yaml" in failure for failure in failures)
    assert any("## Derived Views" in failure for failure in failures)
