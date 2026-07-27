"""Deterministic ARVP strategy metric extraction tests (#4015)."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from core.replay.canonical_json import canonical_json_dumps
from tools.arvp_vacation.metric_contract import (
    CANONICAL_JOB_COUNT,
    QUEUE_RECORD_COUNT,
    SUPERSEDED_JOB_COUNT,
)
from tools.arvp_vacation.strategy_metric_extraction import (
    PROFIT_FACTOR_INFINITY_TOKEN,
    SCHEMA_VERSION,
    StrategyMetricExtractionError,
    build_extraction_bundle,
    extract_campaign_metrics,
    resolve_candles_total,
)
from tools.arvp_vacation.summary import _metrics_summary

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "arvp" / "strategy_metrics"
SCHEMA_PATH = REPO_ROOT / "docs" / "contracts" / "arvp_strategy_metrics.v1.schema.json"
CAMPAIGN_QUEUE = (
    REPO_ROOT
    / "artifacts"
    / "arvp_vacation"
    / "arvp_binance_historical_3990_2bb32b68_20260712T111944Z"
    / "queue_state.json"
)
GOLDEN_CONTENT_HASH = "8b253855277f04bfd6a16e6afc1ccf2eab1b3114d7cedf045797b83ab5a9c55a"


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def schema() -> dict:
    return _load(SCHEMA_PATH)


@pytest.fixture(scope="module")
def schema_validator(schema: dict) -> Draft7Validator:
    return Draft7Validator(schema)


def test_schema_declares_version_and_selector(schema: dict) -> None:
    assert schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION
    selection = schema["properties"]["canonical_job_selection"]["properties"]
    assert selection["selector"]["const"] == "superseded_by_stress_v2_rerun != true"


def test_slice_fixture_extracts_two_canonical_jobs_and_excludes_superseded() -> None:
    queue = _load(FIXTURES / "extraction_queue_slice.v1.json")
    bundle = build_extraction_bundle(queue, repo_root=REPO_ROOT)
    assert bundle["canonical_job_selection"]["canonical_job_count"] == 2
    assert bundle["canonical_job_selection"]["excluded_superseded_job_count"] == 1
    assert bundle["record_count"] == 6
    job_ids = {record["job_id"] for record in bundle["records"]}
    assert (
        "vac-donchian-breakout-v1-binance_1m_stress_max_drawdown-scenarios"
        not in job_ids
    )


def test_zero_trade_job_is_not_rankable() -> None:
    queue = _load(FIXTURES / "extraction_queue_slice.v1.json")
    records, _ = extract_campaign_metrics(queue, repo_root=REPO_ROOT)
    zero_trade = [
        record
        for record in records
        if record["job_id"]
        == "vac-primary-breakout-v1-binance_1m_month_2017_11-scenarios"
    ]
    assert len(zero_trade) == 3
    assert all(record["rankable"] is False for record in zero_trade)
    assert all(
        "zero_closed_trades_total" in record["not_rankable_reasons"]
        for record in zero_trade
    )


def test_missing_trade_field_is_missing_not_zero() -> None:
    queue = _load(FIXTURES / "extraction_queue_slice.v1.json")
    job = queue["jobs"][1]
    del job["scenario_metrics"]["baseline"]["metrics"]["closed_trades_total"]
    records, _ = extract_campaign_metrics(queue, repo_root=REPO_ROOT)
    baseline = next(
        record
        for record in records
        if record["job_id"] == job["job_id"] and record["scenario"] == "baseline"
    )
    assert baseline["closed_trades_total"] is None
    assert baseline["rankable"] is False
    assert "missing_closed_trades_total" in baseline["not_rankable_reasons"]


def test_nested_metrics_map_to_summary_fields() -> None:
    job = {
        "scenario_metrics": {
            "baseline": {
                "metrics": {
                    "closed_trades_total": 12,
                    "net_pnl_quote": -3.5,
                    "profit_factor": 0.8,
                    "expectancy_r": -0.01,
                    "max_drawdown_r": 1.2,
                    "win_rate": 0.4,
                }
            }
        }
    }
    summary = _metrics_summary(job)
    assert summary["baseline"]["trade_count"] == 12
    assert summary["baseline"]["net_pnl"] == -3.5
    assert summary["baseline"]["profit_factor"] == 0.8
    assert summary["baseline"]["expectancy"] == -0.01
    assert summary["baseline"]["max_drawdown"] == 1.2
    assert summary["baseline"]["win_rate"] == 0.4


def test_legacy_top_level_summary_fields_remain_supported() -> None:
    job = {
        "scenario_metrics": {
            "baseline": {
                "trade_count": 4,
                "net_pnl": 1.5,
                "win_rate": 0.5,
            }
        }
    }
    summary = _metrics_summary(job)
    assert summary["baseline"]["trade_count"] == 4
    assert summary["baseline"]["net_pnl"] == 1.5


def test_slippage_availability_is_not_available() -> None:
    queue = _load(FIXTURES / "extraction_queue_slice.v1.json")
    records, _ = extract_campaign_metrics(queue, repo_root=REPO_ROOT)
    assert all(record["slippage_availability"] == "not_available" for record in records)


def test_candles_total_preserves_producer_input_total() -> None:
    from tools.arvp_vacation.candle_rankability import resolve_candle_rankability

    result = resolve_candle_rankability(
        dataset_summary={
            "candles_total": 44640,
            "candles_live": 44606,
            "warmup_candles": 34,
        },
        strategy_id="breakout_volatility_filter_v1",
        campaign_id="batch_a_stage_a_d0a4e72d_20260713",
        parameter_fingerprint="abc",
        campaign_source_sha="d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a",
        repo_root=REPO_ROOT,
    )
    assert result.candles_total == 44640
    assert result.candles_evaluated == 44606
    assert result.rankability_blocking_flags == ()


def test_legacy_resolve_candles_total_still_flags_mismatch() -> None:
    candles, flags = resolve_candles_total({"candles_live": 100, "candles_total": 120})
    assert candles == 100
    assert "candles_live_candles_total_mismatch" in flags


def test_candles_total_falls_back_to_total() -> None:
    candles, flags = resolve_candles_total({"candles_total": 43200})
    assert candles == 43200
    assert flags == []


def test_warmup_trim_without_provenance_is_not_rankable() -> None:
    queue = _load(FIXTURES / "extraction_queue_slice.v1.json")
    records, _ = extract_campaign_metrics(queue, repo_root=REPO_ROOT)
    donchian = next(
        record
        for record in records
        if record["job_id"].startswith("vac-donchian-breakout-v1-binance_1m_month")
        and record["scenario"] == "baseline"
    )
    assert donchian["candles_total"] == 44640
    assert donchian["candles_input_total"] == 44640
    assert donchian["rankable"] is False
    assert "warmup_provenance_missing" in donchian["not_rankable_reasons"]


def test_profit_factor_infinity_is_canonical() -> None:
    queue = _load(FIXTURES / "extraction_queue_slice.v1.json")
    queue = copy.deepcopy(queue)
    queue["jobs"][0]["scenario_metrics"]["baseline"]["metrics"][
        "profit_factor"
    ] = math.inf
    records, _ = extract_campaign_metrics(queue, repo_root=REPO_ROOT)
    baseline = next(
        record
        for record in records
        if record["scenario"] == "baseline"
        and record["job_id"].startswith("vac-donchian-breakout-v1-binance_1m_month")
    )
    assert baseline["profit_factor"] == PROFIT_FACTOR_INFINITY_TOKEN


def test_nan_profit_factor_fails_closed() -> None:
    queue = copy.deepcopy(_load(FIXTURES / "extraction_queue_slice.v1.json"))
    queue["jobs"][0]["scenario_metrics"]["baseline"]["metrics"][
        "profit_factor"
    ] = math.nan
    with pytest.raises(StrategyMetricExtractionError, match="non-finite"):
        extract_campaign_metrics(queue, repo_root=REPO_ROOT)


def test_extraction_is_byte_identical_on_repeat() -> None:
    queue = _load(FIXTURES / "extraction_queue_slice.v1.json")
    first = canonical_json_dumps(build_extraction_bundle(queue, repo_root=REPO_ROOT))
    second = canonical_json_dumps(build_extraction_bundle(queue, repo_root=REPO_ROOT))
    assert first == second


def test_input_job_order_does_not_change_hash() -> None:
    queue = _load(FIXTURES / "extraction_queue_slice.v1.json")
    reversed_queue = copy.deepcopy(queue)
    reversed_queue["jobs"] = list(reversed(reversed_queue["jobs"]))
    first = build_extraction_bundle(queue, repo_root=REPO_ROOT)["content_hash"]
    second = build_extraction_bundle(reversed_queue, repo_root=REPO_ROOT)[
        "content_hash"
    ]
    assert first == second


def test_slice_bundle_validates_against_schema(
    schema_validator: Draft7Validator,
) -> None:
    queue = _load(FIXTURES / "extraction_queue_slice.v1.json")
    bundle = build_extraction_bundle(queue, repo_root=REPO_ROOT)
    errors = sorted(schema_validator.iter_errors(bundle), key=lambda err: err.message)
    assert not errors, [error.message for error in errors]


def test_campaign_queue_canonical_counts_when_present() -> None:
    if not CAMPAIGN_QUEUE.is_file():
        pytest.skip("local campaign queue_state.json not available")
    queue = _load(CAMPAIGN_QUEUE)
    bundle = build_extraction_bundle(queue, repo_root=REPO_ROOT)
    assert bundle["canonical_job_selection"]["queue_record_count"] == QUEUE_RECORD_COUNT
    assert (
        bundle["canonical_job_selection"]["canonical_job_count"] == CANONICAL_JOB_COUNT
    )
    assert (
        bundle["canonical_job_selection"]["excluded_superseded_job_count"]
        == SUPERSEDED_JOB_COUNT
    )
    assert bundle["record_count"] == CANONICAL_JOB_COUNT * 3


def test_campaign_content_hash_is_stable_when_present() -> None:
    if not CAMPAIGN_QUEUE.is_file():
        pytest.skip("local campaign queue_state.json not available")
    queue = _load(CAMPAIGN_QUEUE)
    first = build_extraction_bundle(queue, repo_root=REPO_ROOT)["content_hash"]
    second = build_extraction_bundle(queue, repo_root=REPO_ROOT)["content_hash"]
    assert first == second == GOLDEN_CONTENT_HASH


def test_record_schema_version_is_emitted() -> None:
    queue = _load(FIXTURES / "extraction_queue_slice.v1.json")
    records, _ = extract_campaign_metrics(queue, repo_root=REPO_ROOT)
    assert all(record["schema_version"] == SCHEMA_VERSION for record in records)


def test_purpose_and_window_class_are_separated() -> None:
    if not CAMPAIGN_QUEUE.is_file():
        pytest.skip("local campaign queue_state.json not available")
    queue = _load(CAMPAIGN_QUEUE)
    records, _ = extract_campaign_metrics(queue, repo_root=REPO_ROOT)
    purposes = {record["purpose"] for record in records if record["purpose"]}
    assert {"development", "validation", "out_of_sample", "stress"}.issuperset(purposes)
    window_classes = {record["window_class"] for record in records}
    assert "monthly" in window_classes
    assert "stress" in window_classes
