"""ARVP candidate evidence gross-to-net wiring (#4150)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.validation.arvp_candidate_evidence_assembler import (
    assemble_arvp_candidate_evidence,
)

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[3]
CANDIDATE_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "arvp" / "candidate_evidence"


def _bundle() -> dict:
    with (CANDIDATE_FIXTURES / "slice_metrics_bundle.v1.json").open(
        encoding="utf-8"
    ) as handle:
        return json.load(handle)


def test_cost_evidence_includes_gross_to_net_block() -> None:
    result = assemble_arvp_candidate_evidence(_bundle())
    for packet in result.packets:
        cost = packet["arvp_evidence"]["cost_evidence"]
        g2n = cost["execution_economics_gross_to_net"]
        assert g2n["contract_version"] == "execution_economics_gross_to_net.v1"
        assert g2n["reconciled"] is True
        assert g2n["components"]["spread_cost"]["status"] == "not_applicable"
        assert g2n["components"]["spread_cost"]["amount"] is None
        assert cost["spread_availability"] == "not_applicable"
        # Without slippage_cost_quote on metrics, slippage is not a measured zero.
        assert g2n["components"]["slippage_cost"]["status"] == "not_applicable"
        assert cost["slippage_availability"] == "not_available"
        assert "assumptions_snapshot" in g2n
        assert g2n["assumptions_snapshot"]["order_size"]["value"] == "1.0"
        assert "fingerprint" in g2n["assumptions_snapshot"]


def test_funding_and_limit_orders_are_not_billed() -> None:
    """#4190: both surfaces stay retired and never become a measured zero."""
    result = assemble_arvp_candidate_evidence(_bundle())
    for packet in result.packets:
        g2n = packet["arvp_evidence"]["cost_evidence"][
            "execution_economics_gross_to_net"
        ]
        funding = g2n["components"]["funding_cost_when_active"]
        assert funding["status"] == "inactive_not_wired"
        assert funding["amount"] is None
        snapshot = g2n["assumptions_snapshot"]
        assert snapshot["funding_model"]["wired_into_replay_pnl"] is False
        assert snapshot["funding_model"]["input_availability"] == (
            "unavailable_no_funding_rate_series"
        )
        assert snapshot["limit_order_model"]["status"] == (
            "parked_not_economics_billable"
        )
        assert snapshot["limit_order_model"]["wired_into_arvp_runners"] is False


def test_market_only_path_reports_taker_semantics() -> None:
    result = assemble_arvp_candidate_evidence(_bundle())
    for packet in result.packets:
        g2n = packet["arvp_evidence"]["cost_evidence"][
            "execution_economics_gross_to_net"
        ]
        semantics = g2n["execution_semantics"]
        assert semantics["order_type"] == "market"
        assert semantics["maker_fill_evidence"] is False
        assert semantics["funding_basis"] is None
        assert g2n["components"]["maker_fee_cost"]["status"] == "zero"


def test_limitations_document_placeholder_zeros() -> None:
    result = assemble_arvp_candidate_evidence(_bundle())
    for packet in result.packets:
        joined = " ".join(packet["limitations"])
        assert "not_applicable" in joined or "schema placeholder" in joined
        assert "execution_economics_gross_to_net" in joined
