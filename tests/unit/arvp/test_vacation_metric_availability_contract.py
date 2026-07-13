"""ARVP vacation replay metric availability contract tests (#4014)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from tests.unit.arvp import _arvp_vacation_metric_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

FIXTURES = helpers.FIXTURES_DIR
SCENARIO_FIXTURES = (
    FIXTURES / "donchian_monthly_baseline_metrics.v1.json",
    FIXTURES / "donchian_stress_v2_baseline_metrics.v1.json",
    FIXTURES / "primary_zero_trade_baseline_metrics.v1.json",
)


def _load(path: Path) -> dict:
    return helpers.load_json(path)


@pytest.fixture(scope="module")
def schema() -> dict:
    return _load(helpers.SCHEMA_PATH)


@pytest.fixture(scope="module")
def schema_validator(schema: dict) -> Draft7Validator:
    return Draft7Validator(schema)


@pytest.mark.parametrize("fixture_path", SCENARIO_FIXTURES, ids=lambda p: p.stem)
def test_scenario_metrics_fixtures_validate_against_schema(
    fixture_path: Path,
    schema_validator: Draft7Validator,
) -> None:
    payload = _load(fixture_path)
    errors = sorted(schema_validator.iter_errors(payload), key=lambda e: e.message)
    assert not errors, [e.message for e in errors]


def test_schema_declares_version_and_canonical_selection_documentation(
    schema: dict,
) -> None:
    assert schema["properties"]["schema_version"]["const"] == (
        "arvp_vacation_job_metrics.v1"
    )
    selection = schema["properties"]["canonical_job_selection"]["properties"]
    assert selection["selector"]["const"] == helpers.CANONICAL_SELECTOR
    assert selection["canonical_job_count"]["const"] == helpers.CANONICAL_JOB_COUNT
    assert selection["superseded_job_count"]["const"] == helpers.SUPERSEDED_JOB_COUNT


def test_matrix_documents_all_required_metrics() -> None:
    documented = {row["metric"] for row in helpers.METRIC_MATRIX}
    required = {
        "gross_pnl_quote",
        "net_pnl_quote",
        "fees_total_quote",
        "slippage",
        "max_drawdown_r",
        "fee_adjusted_max_drawdown_r",
        "profit_factor",
        "fee_adjusted_profit_factor",
        "expectancy_r",
        "fee_adjusted_expectancy_r",
        "closed_trades_total",
        "win_rate",
        "avg_win_r",
        "avg_loss_r",
        "exposure_or_time_in_market",
        "regime_behavior",
        "scenario_sensitivity",
        "window_stability",
    }
    assert documented == required


def test_matrix_markdown_exists_and_declares_ready_outcome() -> None:
    text = helpers.MATRIX_PATH.read_text(encoding="utf-8")
    assert helpers.OUTCOME_READY in text
    assert helpers.CANONICAL_SELECTOR in text
    assert "ranking_ready" in text
    assert "historical_cross_venue_research" in text
    for row in helpers.METRIC_MATRIX:
        assert row["metric"] in text


def test_canonical_selection_excludes_superseded_jobs() -> None:
    queue = _load(FIXTURES / "canonical_selection_queue_slice.v1.json")
    jobs = queue["jobs"]
    assert len(jobs) == 9
    canonical = helpers.select_canonical_jobs(jobs)
    assert len(canonical) == 3
    superseded = [j for j in jobs if j.get("superseded_by_stress_v2_rerun") is True]
    assert len(superseded) == helpers.SUPERSEDED_JOB_COUNT


def test_unknown_superseded_status_fails_closed() -> None:
    with pytest.raises(helpers.VacationMetricContractError, match="unknown"):
        helpers.is_canonical_queue_job(
            {"job_id": "bad", "superseded_by_stress_v2_rerun": "maybe"}
        )


def test_zero_trade_is_valid_not_missing() -> None:
    payload = _load(FIXTURES / "primary_zero_trade_baseline_metrics.v1.json")
    metrics = payload["metrics"]
    assert metrics["closed_trades_total"] == 0
    assert helpers.metric_is_missing(metrics, "closed_trades_total") is False
    assert helpers.is_rankable_job_metrics(metrics) is False


def test_missing_trade_dependent_fields_are_not_zero() -> None:
    payload = _load(FIXTURES / "primary_zero_trade_baseline_metrics.v1.json")
    metrics = payload["metrics"]
    for field in (
        "fee_adjusted_max_drawdown_r",
        "fee_adjusted_profit_factor",
        "fee_adjusted_expectancy_r",
        "avg_win_r",
        "avg_loss_r",
    ):
        assert helpers.metric_is_missing(metrics, field) is True


def test_traded_job_is_rankable() -> None:
    payload = _load(FIXTURES / "donchian_monthly_baseline_metrics.v1.json")
    assert helpers.is_rankable_job_metrics(payload["metrics"]) is True


def test_campaign_queue_state_canonical_counts_when_present() -> None:
    campaign_queue = (
        helpers.REPO_ROOT
        / "artifacts"
        / "arvp_vacation"
        / helpers.CAMPAIGN_ID
        / "queue_state.json"
    )
    if not campaign_queue.is_file():
        pytest.skip("local campaign queue_state.json not available")
    state = _load(campaign_queue)
    jobs = state.get("jobs") or []
    assert len(jobs) == helpers.QUEUE_RECORD_COUNT
    canonical = helpers.select_canonical_jobs(jobs)
    assert len(canonical) == helpers.CANONICAL_JOB_COUNT
    superseded = [j for j in jobs if j.get("superseded_by_stress_v2_rerun") is True]
    assert len(superseded) == helpers.SUPERSEDED_JOB_COUNT


def test_slippage_classified_not_available() -> None:
    row = next(r for r in helpers.METRIC_MATRIX if r["metric"] == "slippage")
    assert row["classification"] == "not_available"


@pytest.mark.parametrize(
    ("fixture_path", "expect_rankable"),
    [
        (FIXTURES / "donchian_monthly_baseline_metrics.v1.json", True),
        (FIXTURES / "donchian_stress_v2_baseline_metrics.v1.json", True),
        (FIXTURES / "primary_zero_trade_baseline_metrics.v1.json", False),
    ],
    ids=["donchian_monthly", "donchian_stress_v2", "primary_zero_trade"],
)
def test_fixture_rankable_semantics(fixture_path: Path, expect_rankable: bool) -> None:
    payload = _load(fixture_path)
    assert helpers.is_rankable_job_metrics(payload["metrics"]) is expect_rankable
