"""Tests for check_window_timer_guardrail.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "governance"))

from check_window_timer_guardrail import (
    evaluate_window,
    load_max_window_minutes,
    load_observed_minutes,
)


def test_load_max_window_minutes_reads_policy() -> None:
    policy_path = Path("governance/p5_canary_readiness.yaml")
    assert load_max_window_minutes(policy_path) == 15


def test_load_observed_minutes_from_cli_value() -> None:
    assert load_observed_minutes(minutes=12, run_summary_path=None) == 12


def test_load_observed_minutes_from_run_summary(tmp_path: Path) -> None:
    run_summary_path = tmp_path / "run_summary.json"
    run_summary_path.write_text(
        json.dumps({"soak_minutes": 9}),
        encoding="utf-8",
    )
    assert load_observed_minutes(minutes=None, run_summary_path=run_summary_path) == 9


def test_load_observed_minutes_requires_input() -> None:
    with pytest.raises(ValueError):
        load_observed_minutes(minutes=None, run_summary_path=None)


def test_evaluate_window_passes_within_limit() -> None:
    result = evaluate_window(15, 15)
    assert result["verdict"] == "PASS"
    assert result["within_limit"] is True


def test_evaluate_window_fails_above_limit() -> None:
    result = evaluate_window(15, 16)
    assert result["verdict"] == "FAIL"
    assert result["within_limit"] is False
