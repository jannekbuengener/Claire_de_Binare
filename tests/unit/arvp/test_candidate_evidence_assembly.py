"""ARVP candidate evidence packet assembly tests (#4016)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from services.validation.arvp_candidate_evidence_assembler import (
    RANKABILITY_NOT,
    assemble_arvp_candidate_evidence,
)
from tools.arvp_vacation.strategy_metric_extraction import build_extraction_bundle

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "arvp" / "strategy_metrics"
CANDIDATE_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "arvp" / "candidate_evidence"
PEP_SCHEMA_PATH = REPO_ROOT / "docs" / "contracts" / "profitability_evidence_packet.v1.schema.json"
CAMPAIGN_QUEUE = (
    REPO_ROOT
    / "artifacts"
    / "arvp_vacation"
    / "arvp_binance_historical_3990_2bb32b68_20260712T111944Z"
    / "queue_state.json"
)
GOLDEN_SOURCE_HASH = (
    "8b253855277f04bfd6a16e6afc1ccf2eab1b3114d7cedf045797b83ab5a9c55a"
)

def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def pep_validator() -> Draft7Validator:
    schema = _load(PEP_SCHEMA_PATH)
    return Draft7Validator(schema)


def _bundle_from_slice() -> dict:
    return _load(CANDIDATE_FIXTURES / "slice_metrics_bundle.v1.json")


def test_slice_bundle_yields_two_candidates_with_six_records_each_strategy() -> None:
    bundle = _bundle_from_slice()
    result = assemble_arvp_candidate_evidence(bundle)
    assert result.source_record_count == 6
    assert result.packet_count == 2
    assert set(result.candidates) == {"donchian_breakout_v1", "primary_breakout_v1"}


def test_packets_validate_against_pep_schema(pep_validator: Draft7Validator) -> None:
    result = assemble_arvp_candidate_evidence(_bundle_from_slice())
    for packet in result.packets:
        errors = sorted(pep_validator.iter_errors(packet), key=lambda err: str(err.message))
        assert not errors, errors[0].message if errors else ""


def test_ranking_ready_and_paper_same_venue_remain_false_or_not_run() -> None:
    result = assemble_arvp_candidate_evidence(_bundle_from_slice())
    for packet in result.packets:
        assert packet["ranking_ready"] is False
        assert packet["paper_reference_status"] == "not_run"
        assert packet["same_venue_status"] == "not_run"
        assert packet["replay_vs_paper_status"] == "not_run"


def test_zero_trade_candidate_is_not_rankable() -> None:
    result = assemble_arvp_candidate_evidence(_bundle_from_slice())
    primary = next(
        packet
        for packet in result.packets
        if packet["strategy_id"] == "primary_breakout_v1"
    )
    assert primary["rankability_status"] == RANKABILITY_NOT
    assert "no_rankable_baseline_windows" in primary["rankability_reasons"]


def test_fee_adjusted_max_drawdown_not_invented() -> None:
    result = assemble_arvp_candidate_evidence(_bundle_from_slice())
    primary = next(
        packet
        for packet in result.packets
        if packet["strategy_id"] == "primary_breakout_v1"
    )
    summaries = primary["arvp_evidence"]["economic_metric_summaries"]
    assert all(item["fee_adjusted_max_drawdown_r"] is None for item in summaries)


def test_scenario_sensitivity_deltas_handle_missing_and_zero_denominator() -> None:
    bundle = _bundle_from_slice()
    records = bundle["records"]
    pessimistic = next(
        record
        for record in records
        if record["job_id"].startswith("vac-primary")
        and record["scenario"] == "pessimistic_execution"
    )
    pessimistic["net_pnl_quote"] = None
    result = assemble_arvp_candidate_evidence(bundle)
    primary = next(
        packet
        for packet in result.packets
        if packet["strategy_id"] == "primary_breakout_v1"
    )
    sensitivity = primary["arvp_evidence"]["scenario_sensitivity"]
    assert sensitivity
    delta = sensitivity[0]["cost_sensitivity"]["pessimistic_execution"][
        "net_pnl_quote_delta"
    ]
    assert delta["absolute_delta"] is None
    assert delta["delta_reason"] == "missing_operand"


def test_reverse_input_order_produces_identical_hashes() -> None:
    bundle = _bundle_from_slice()
    reversed_bundle = copy.deepcopy(bundle)
    reversed_bundle["records"] = list(reversed(bundle["records"]))
    first = assemble_arvp_candidate_evidence(bundle)
    second = assemble_arvp_candidate_evidence(reversed_bundle)
    assert first.bundle_hash == second.bundle_hash
    assert [packet["content_hash"] for packet in first.packets] == [
        packet["content_hash"] for packet in second.packets
    ]


def test_full_campaign_assembly_when_artifacts_present() -> None:
    if not CAMPAIGN_QUEUE.is_file():
        pytest.skip("full campaign artifacts not present locally")

    bundle = build_extraction_bundle(_load(CAMPAIGN_QUEUE), repo_root=REPO_ROOT)
    assert bundle["record_count"] == 954
    assert bundle["content_hash"] == GOLDEN_SOURCE_HASH
    result = assemble_arvp_candidate_evidence(bundle)
    assert result.source_record_count == 954
    assert result.packet_count == 3
    assert set(result.candidates) == {
        "donchian_breakout_v1",
        "breakout_trend_filter_v1",
        "primary_breakout_v1",
    }

    second = assemble_arvp_candidate_evidence(bundle)
    assert second.bundle_hash == result.bundle_hash


def test_slice_fixture_manifest_matches_assembly_output() -> None:
    manifest = _load(CANDIDATE_FIXTURES / "slice_bundle_manifest.v1.json")
    result = assemble_arvp_candidate_evidence(_bundle_from_slice())
    assert result.bundle_hash == manifest["bundle_hash"]
    assert result.packet_count == manifest["packet_count"]
    assert result.source_record_count == manifest["source_record_count"]
