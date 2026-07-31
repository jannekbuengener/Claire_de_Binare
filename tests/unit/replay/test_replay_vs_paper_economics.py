"""Replay-vs-paper economics component diff tests (#4150)."""

from __future__ import annotations

import pytest

from core.replay.execution_economics_v1 import (
    CONTRACT_VERSION,
    FUNDING_INPUT_AVAILABILITY,
    LIMIT_ORDER_MODEL_STATUS,
)
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


def test_replay_and_paper_share_contract_semantics() -> None:
    """Replay and paper must describe funding/limit identically (#4190)."""
    metrics = {"gross_pnl_quote": 100.0, "fees_total_quote": 2.0}
    replay = economics_payload_from_metrics(metrics)
    paper = economics_payload_from_metrics(dict(metrics, gross_pnl_quote=90.0))

    for payload in (replay, paper):
        assert payload["contract_version"] == CONTRACT_VERSION
        assert payload["execution_semantics"]["order_type"] == "market"
        assert payload["execution_semantics"]["fill_status"] == "filled"
        assert payload["execution_semantics"]["maker_fill_evidence"] is False
        assert payload["execution_semantics"]["funding_basis"] is None
        funding = payload["components"]["funding_cost_when_active"]
        assert funding["status"] == "inactive_not_wired"
        assert funding["amount"] is None
        snapshot = payload["assumptions_snapshot"]
        assert snapshot["funding_model"]["input_availability"] == (
            FUNDING_INPUT_AVAILABILITY
        )
        assert snapshot["limit_order_model"]["status"] == LIMIT_ORDER_MODEL_STATUS

    assert (
        replay["assumptions_snapshot"]["fingerprint"]
        == paper["assumptions_snapshot"]["fingerprint"]
    )


def test_inactive_funding_is_incomparable_not_a_zero_delta() -> None:
    diff = compare_economics_from_reports(
        {"metrics": {"gross_pnl_quote": 100.0, "fees_total_quote": 2.0}},
        {"gross_pnl_quote": 90.0, "fees_total_quote": 1.0},
    )
    funding = diff["component_diffs"]["funding_cost_when_active"]
    assert funding["delta"] is None
    assert funding["status"] == "both_not_applicable_or_missing"
