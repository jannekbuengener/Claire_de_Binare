"""Replay-vs-paper economics component diff tests (#4150)."""

from __future__ import annotations

import pytest

from core.replay.replay_vs_paper_compare import (
    compare_economics_from_reports,
    economics_payload_from_metrics,
)

pytestmark = [pytest.mark.unit]


def test_economics_payload_marks_missing_slippage_not_applicable() -> None:
    payload = economics_payload_from_metrics(
        {"gross_pnl_quote": 100.0, "fees_total_quote": 2.0}
    )
    assert payload["components"]["slippage_cost"]["status"] == "not_applicable"
    assert payload["components"]["total_fee_cost"]["amount"] == "2.00000000"
    assert payload["net_pnl"] == "98.00000000"


def test_compare_economics_component_diff() -> None:
    replay_report = {
        "metrics": {
            "gross_pnl_quote": 100.0,
            "fees_total_quote": 2.0,
            "slippage_cost_quote": 3.0,
        }
    }
    paper = {
        "gross_pnl_quote": 90.0,
        "fees_total_quote": 1.0,
        "slippage_cost_quote": 1.0,
    }
    diff = compare_economics_from_reports(replay_report, paper)
    assert diff["component_diffs"]["total_fee_cost"]["delta"] == "1.00000000"
    assert diff["component_diffs"]["slippage_cost"]["delta"] == "2.00000000"
    assert "fingerprint" in diff
