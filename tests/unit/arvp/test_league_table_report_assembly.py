"""Governance-safe Strategy League table report assembly tests (#4017)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from services.validation.arvp_candidate_evidence_assembler import (
    RANKABILITY_NOT,
    RANKABILITY_PARTIAL,
    assemble_arvp_candidate_evidence,
)
from services.validation.profitability_league_table_report_assembler import (
    EXIT_STATUS_PARTIAL_NO_WINNER,
    build_governance_league_table_report,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "arvp" / "candidate_evidence"
REPORT_SCHEMA_PATH = (
    REPO_ROOT / "docs" / "contracts" / "profitability_league_table_report.v1.schema.json"
)
CAMPAIGN_QUEUE = (
    REPO_ROOT
    / "artifacts"
    / "arvp_vacation"
    / "arvp_binance_historical_3990_2bb32b68_20260712T111944Z"
    / "queue_state.json"
)
GOLDEN_SOURCE_HASH = (
    "ad3d4ccc449e81e4aa5ec81185d6b3229d12a9e05b2e4970dd352b7471e5b7ad"
)
GOLDEN_BUNDLE_HASH = (
    "4e7b4b88427d3fed84493721f97f82d0502c5a93ee96b81b8af8dab0671e26a4"
)
CAMPAIGN_ID = "arvp_binance_historical_3990_2bb32b68_20260712T111944Z"


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def report_validator() -> Draft7Validator:
    return Draft7Validator(_load(REPORT_SCHEMA_PATH))


def _assembly_from_slice() -> tuple[list[dict], str]:
    bundle = _load(FIXTURES / "slice_metrics_bundle.v1.json")
    result = assemble_arvp_candidate_evidence(bundle)
    return result.packets, result.bundle_hash


def _report_from_peps(peps: list[dict], *, bundle_hash: str) -> dict:
    result = build_governance_league_table_report(
        peps,
        campaign_id=CAMPAIGN_ID,
        evidence_class="historical_cross_venue_research",
        source_content_hash=GOLDEN_SOURCE_HASH,
        candidate_bundle_hash=bundle_hash,
        report_id="pltr-arvp-league-test-4017",
    )
    return result.report


def test_slice_bundle_report_is_partial_with_empty_official_ranking(
    report_validator: Draft7Validator,
) -> None:
    peps, bundle_hash = _assembly_from_slice()
    report = _report_from_peps(peps, bundle_hash=bundle_hash)

    assert report["table_status"] == "PARTIAL"
    assert report["ranking_ready"] is False
    assert report["winner"] is None
    assert report["official_ranking"] == []
    assert report["candidate_rankings"] == []
    assert report["officially_ranked_count"] == 0
    assert report["not_rankable_count"] == 2
    assert report["promotion_status"] == "NOT_AUTHORIZED"
    assert report["paper_reference_status"] == "not_run"
    assert report["same_venue_status"] == "not_run"
    assert report["source_content_hash"] == GOLDEN_SOURCE_HASH
    assert report["candidate_bundle_hash"] == bundle_hash

    errors = sorted(report_validator.iter_errors(report), key=lambda err: str(err.message))
    assert not errors, errors[0].message if errors else ""


def test_not_rankable_candidates_have_no_total_score() -> None:
    peps, bundle_hash = _assembly_from_slice()
    report = _report_from_peps(peps, bundle_hash=bundle_hash)

    for row in report["candidate_rows"]:
        assert row["rankability_status"] == RANKABILITY_NOT
        assert row["official_rank"] is None
        assert row["total_score"] is None
        assert row["sentinel_mode"] is True
        assert "rankability_status=NOT_RANKABLE" in row["exclusion_reasons"]


def test_partial_evidence_is_not_winner() -> None:
    peps, _ = _assembly_from_slice()
    partial_pep = copy.deepcopy(peps[0])
    partial_pep["rankability_status"] = RANKABILITY_PARTIAL
    partial_pep["rankability_reasons"] = ["partial_missing_required_metrics"]
    partial_pep["candidate_id"] = "cand-partial-test-v1"

    report = _report_from_peps([partial_pep], bundle_hash="a" * 64)
    assert report["winner"] is None
    assert report["official_ranking"] == []
    row = report["candidate_rows"][0]
    assert row["rankability_status"] == RANKABILITY_PARTIAL
    assert row["official_rank"] is None


def test_reverse_pep_order_yields_identical_report_hash() -> None:
    peps, bundle_hash = _assembly_from_slice()
    first = build_governance_league_table_report(
        peps,
        campaign_id=CAMPAIGN_ID,
        evidence_class="historical_cross_venue_research",
        source_content_hash=GOLDEN_SOURCE_HASH,
        candidate_bundle_hash=bundle_hash,
    )
    second = build_governance_league_table_report(
        list(reversed(peps)),
        campaign_id=CAMPAIGN_ID,
        evidence_class="historical_cross_venue_research",
        source_content_hash=GOLDEN_SOURCE_HASH,
        candidate_bundle_hash=bundle_hash,
    )
    assert first.report_content_hash == second.report_content_hash


def test_comparison_dimensions_and_formula_weights_visible() -> None:
    peps, bundle_hash = _assembly_from_slice()
    report = _report_from_peps(peps, bundle_hash=bundle_hash)

    assert report["weights"]["NET_ECONOMICS"] == 25.0
    assert sum(report["weights"].values()) == pytest.approx(100.0)
    assert len(report["dimension_definitions"]) == 17
    row = report["candidate_rows"][0]
    dims = row["comparison_dimensions"]
    assert "net_economic_result" in dims
    assert "sample_size" in dims
    assert "evidence_quality" in dims


def test_exit_status_documented_in_limitations() -> None:
    peps, bundle_hash = _assembly_from_slice()
    report = _report_from_peps(peps, bundle_hash=bundle_hash)
    joined = " ".join(report["limitations"])
    assert EXIT_STATUS_PARTIAL_NO_WINNER in joined


@pytest.mark.skipif(not CAMPAIGN_QUEUE.is_file(), reason="full campaign artifacts absent")
def test_full_campaign_league_report_when_artifacts_present(
    report_validator: Draft7Validator,
) -> None:
    from tools.arvp_vacation.strategy_metric_extraction import build_extraction_bundle

    bundle = build_extraction_bundle(_load(CAMPAIGN_QUEUE), repo_root=REPO_ROOT)
    assembly = assemble_arvp_candidate_evidence(bundle)
    assert assembly.bundle_hash == GOLDEN_BUNDLE_HASH

    report = _report_from_peps(assembly.packets, bundle_hash=assembly.bundle_hash)
    assert report["candidate_count"] == 3
    assert report["official_ranking"] == []
    assert report["winner"] is None

    statuses = {row["rankability_status"] for row in report["candidate_rows"]}
    assert RANKABILITY_NOT in statuses

    second = build_governance_league_table_report(
        list(reversed(assembly.packets)),
        campaign_id=CAMPAIGN_ID,
        evidence_class="historical_cross_venue_research",
        source_content_hash=GOLDEN_SOURCE_HASH,
        candidate_bundle_hash=assembly.bundle_hash,
        report_id="pltr-arvp-league-test-4017",
    )
    assert second.report_content_hash == report["report_content_hash"]

    errors = sorted(report_validator.iter_errors(report), key=lambda err: str(err.message))
    assert not errors, errors[0].message if errors else ""
