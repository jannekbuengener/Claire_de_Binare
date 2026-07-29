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


def test_limitations_document_placeholder_zeros() -> None:
    result = assemble_arvp_candidate_evidence(_bundle())
    for packet in result.packets:
        joined = " ".join(packet["limitations"])
        assert "not_applicable" in joined or "schema placeholder" in joined
        assert "execution_economics_gross_to_net" in joined
