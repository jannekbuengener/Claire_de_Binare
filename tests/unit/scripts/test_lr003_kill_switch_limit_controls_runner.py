"""Tests for the deterministic LR-003 kill-switch/limit-controls drill runner."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "drills"))

from lr003_kill_switch_limit_controls_runner import (
    DRILL_ID,
    build_summary,
    render_markdown,
    run_lr003_drill,
)


def test_lr003_drill_runner_produces_passing_summary(tmp_path: Path) -> None:
    summary = run_lr003_drill(tmp_path)

    assert summary["drill_id"] == DRILL_ID
    assert summary["verdict"] == "PASS"
    assert summary["scenario_count"] == 7
    assert summary["passed_count"] == 7
    assert summary["failed_count"] == 0

    scenario_names = {scenario["name"] for scenario in summary["scenarios"]}
    assert scenario_names == {
        "risk_kill_switch_active_blocks",
        "risk_kill_switch_eval_error_fails_closed",
        "execution_kill_switch_active_blocks",
        "deny_max_notional",
        "deny_max_exposure",
        "deny_max_drawdown",
        "allow_reduce_only_sell",
    }


def test_build_summary_and_render_markdown_fail_closed() -> None:
    summary = build_summary(
        [
            {
                "name": "ok",
                "passed": True,
                "expected": "expected",
                "actual": "actual",
                "details": {},
            },
            {
                "name": "broken",
                "passed": False,
                "expected": "expected",
                "actual": "actual",
                "details": {},
            },
        ]
    )

    assert summary["verdict"] == "FAIL"
    assert summary["failed_count"] == 1

    markdown = render_markdown(summary)
    assert "- verdict: `FAIL`" in markdown
    assert "| `broken` | `FAIL` | expected | actual |" in markdown


def test_lr003_drill_runner_writes_summary_and_report_files(tmp_path: Path) -> None:
    run_lr003_drill(tmp_path)

    summary_path = tmp_path / "lr003_summary.json"
    report_path = tmp_path / "lr003_report.md"

    assert summary_path.is_file()
    assert report_path.is_file()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert summary["verdict"] == "PASS"
    assert "# LR-003 Kill-Switch + Limit Controls Drill" in report
    assert "`risk_kill_switch_active_blocks`" in report
    assert "`deny_max_drawdown`" in report
