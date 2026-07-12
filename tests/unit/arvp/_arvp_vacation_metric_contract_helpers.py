"""Helpers for ARVP vacation replay metric availability contract (#4014)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "arvp" / "vacation_metrics"
SCHEMA_PATH = (
    REPO_ROOT / "docs" / "contracts" / "arvp_vacation_job_metrics.v1.schema.json"
)
MATRIX_PATH = REPO_ROOT / "docs" / "evidence" / "arvp_3990_metric_availability_matrix.md"
CAMPAIGN_ID = "arvp_binance_historical_3990_2bb32b68_20260712T111944Z"
from tools.arvp_vacation.metric_contract import (
    CANONICAL_JOB_COUNT,
    CANONICAL_SELECTOR,
    OUTCOME_READY,
    QUEUE_RECORD_COUNT,
    SUPERSEDED_JOB_COUNT,
    VacationMetricContractError,
    is_canonical_queue_job,
    is_rankable_job_metrics,
    metric_is_missing,
    select_canonical_jobs,
)


METRIC_MATRIX: tuple[dict[str, str], ...] = (
    {
        "metric": "gross_pnl_quote",
        "classification": "directly_available",
        "artifact_type": "scenario_metrics_json",
        "field_path": "metrics.gross_pnl_quote",
        "unit": "quote_currency",
        "sign_convention": "positive_profit_negative_loss",
        "aggregation_rule": "per_job_per_scenario; cross-job sums require explicit weighting policy in #4015",
        "missing_semantics": "field absent => missing; 0.0 with closed_trades_total=0 is valid zero",
        "limitations": "Binance historical replay only; not MEXC same-venue evidence",
    },
    {
        "metric": "net_pnl_quote",
        "classification": "directly_available",
        "artifact_type": "scenario_metrics_json",
        "field_path": "metrics.net_pnl_quote",
        "unit": "quote_currency",
        "sign_convention": "positive_profit_negative_loss",
        "aggregation_rule": "per_job_per_scenario; gross_pnl_quote - fees_total_quote when both present",
        "missing_semantics": "field absent => missing; 0.0 with closed_trades_total=0 is valid zero",
        "limitations": "Summary layer currently reads net_pnl alias; extractor must use metrics.net_pnl_quote (#4015)",
    },
    {
        "metric": "fees_total_quote",
        "classification": "directly_available",
        "artifact_type": "scenario_metrics_json",
        "field_path": "metrics.fees_total_quote",
        "unit": "quote_currency",
        "sign_convention": "non_negative_cost",
        "aggregation_rule": "per_job_per_scenario sum",
        "missing_semantics": "field absent => missing; 0 with zero trades is valid zero",
        "limitations": "Fees include simulated execution costs; slippage not itemized separately",
    },
    {
        "metric": "slippage",
        "classification": "not_available",
        "artifact_type": "scenario_metrics_json",
        "field_path": "metrics_availability.slippage_per_trade_available",
        "unit": "n/a",
        "sign_convention": "n/a",
        "aggregation_rule": "not_aggregable",
        "missing_semantics": "always missing as standalone metric; embedded in fill prices",
        "limitations": "metrics_availability.slippage_note documents embedded slippage only",
    },
    {
        "metric": "max_drawdown_r",
        "classification": "directly_available",
        "artifact_type": "scenario_metrics_json",
        "field_path": "metrics.max_drawdown_r",
        "unit": "r_multiple",
        "sign_convention": "non_negative_drawdown_depth",
        "aggregation_rule": "per_job_per_scenario; cross-window max requires explicit policy",
        "missing_semantics": "field absent => missing; 0.0 with zero trades is valid zero",
        "limitations": "Point-estimate drawdown from end-of-trade equity only",
    },
    {
        "metric": "fee_adjusted_max_drawdown_r",
        "classification": "directly_available",
        "artifact_type": "scenario_metrics_json",
        "field_path": "metrics.fee_adjusted_max_drawdown_r",
        "unit": "r_multiple",
        "sign_convention": "non_negative_drawdown_depth",
        "aggregation_rule": "per_job_per_scenario when present",
        "missing_semantics": "null or absent when closed_trades_total=0 or adapter omits field => missing",
        "limitations": "Emitted only by primary_breakout_v1 adapter with trades; absent for donchian/breakout_trend_filter",
    },
    {
        "metric": "profit_factor",
        "classification": "directly_available",
        "artifact_type": "scenario_metrics_json",
        "field_path": "metrics.profit_factor",
        "unit": "ratio",
        "sign_convention": "non_negative; 0.0 when no winning trades",
        "aggregation_rule": "per_job_per_scenario only",
        "missing_semantics": "field absent => missing; 0.0 with zero trades is valid zero not missing",
        "limitations": "Not a campaign-level profitability proof",
    },
    {
        "metric": "fee_adjusted_profit_factor",
        "classification": "directly_available",
        "artifact_type": "scenario_metrics_json",
        "field_path": "metrics.fee_adjusted_profit_factor",
        "unit": "ratio",
        "sign_convention": "non_negative",
        "aggregation_rule": "per_job_per_scenario when present",
        "missing_semantics": "null or absent when no trades on primary_breakout_v1 => missing; always present on donchian/btf",
        "limitations": "Adapter-dependent emission for zero-trade primary_breakout jobs",
    },
    {
        "metric": "expectancy_r",
        "classification": "directly_available",
        "artifact_type": "scenario_metrics_json",
        "field_path": "metrics.expectancy_r",
        "unit": "r_multiple",
        "sign_convention": "positive_expected_gain_negative_expected_loss",
        "aggregation_rule": "per_job_per_scenario only",
        "missing_semantics": "field absent => missing; 0.0 with zero trades is valid zero",
        "limitations": "Per-trade point estimate expectancy",
    },
    {
        "metric": "fee_adjusted_expectancy_r",
        "classification": "directly_available",
        "artifact_type": "scenario_metrics_json",
        "field_path": "metrics.fee_adjusted_expectancy_r",
        "unit": "r_multiple",
        "sign_convention": "positive_expected_gain_negative_expected_loss",
        "aggregation_rule": "per_job_per_scenario when present",
        "missing_semantics": "null or absent when no trades on primary_breakout_v1 => missing",
        "limitations": "Adapter-dependent for zero-trade primary_breakout jobs",
    },
    {
        "metric": "closed_trades_total",
        "classification": "directly_available",
        "artifact_type": "scenario_metrics_json",
        "field_path": "metrics.closed_trades_total",
        "unit": "count",
        "sign_convention": "non_negative_integer",
        "aggregation_rule": "per_job_per_scenario sum; zero is valid",
        "missing_semantics": "field absent => missing; 0 is valid zero-trade outcome not missing",
        "limitations": "Zero-trade jobs are rankable=false",
    },
    {
        "metric": "win_rate",
        "classification": "directly_available",
        "artifact_type": "scenario_metrics_json",
        "field_path": "metrics.win_rate",
        "unit": "ratio_0_1",
        "sign_convention": "non_negative",
        "aggregation_rule": "per_job_per_scenario only",
        "missing_semantics": "field absent => missing; 0.0 with zero trades is valid zero",
        "limitations": "Not recomputed across scenarios without weighting policy",
    },
    {
        "metric": "avg_win_r",
        "classification": "directly_available",
        "artifact_type": "scenario_metrics_json",
        "field_path": "metrics.avg_win_r",
        "unit": "r_multiple",
        "sign_convention": "typically_positive_when_present",
        "aggregation_rule": "per_job_per_scenario when winning trades exist",
        "missing_semantics": "null or absent when trades_win_count=0 => missing not zero",
        "limitations": "Requires at least one winning trade",
    },
    {
        "metric": "avg_loss_r",
        "classification": "directly_available",
        "artifact_type": "scenario_metrics_json",
        "field_path": "metrics.avg_loss_r",
        "unit": "r_multiple",
        "sign_convention": "typically_negative_when_present",
        "aggregation_rule": "per_job_per_scenario when losing trades exist",
        "missing_semantics": "null or absent when trades_loss_count=0 => missing not zero",
        "limitations": "Requires at least one losing trade",
    },
    {
        "metric": "exposure_or_time_in_market",
        "classification": "derivable_with_assumption",
        "artifact_type": "scenario_metrics_json+dataset_spec",
        "field_path": "metrics.signals_total / dataset_summary.candles_live",
        "unit": "ratio_proxy",
        "sign_convention": "non_negative",
        "aggregation_rule": "proxy only; true time-in-market needs per-bar position state",
        "missing_semantics": "requires both signals_total and candles_live; else missing",
        "limitations": "Proxy only; no per-bar position occupancy in artifacts",
    },
    {
        "metric": "regime_behavior",
        "classification": "directly_available",
        "artifact_type": "dataset_spec_json",
        "field_path": "regime_distribution",
        "unit": "candle_count_by_regime",
        "sign_convention": "non_negative_counts",
        "aggregation_rule": "per_dataset window; join by dataset_id",
        "missing_semantics": "dataset_spec missing => missing",
        "limitations": "Window-level regime mix; not per-trade regime attribution",
    },
    {
        "metric": "scenario_sensitivity",
        "classification": "deterministically_derivable",
        "artifact_type": "queue_state.scenario_metrics",
        "field_path": "scenario_metrics.{baseline,pessimistic_execution,feed_gap}.metrics.net_pnl_quote",
        "unit": "quote_currency_delta",
        "sign_convention": "delta_relative_to_baseline",
        "aggregation_rule": "per_job compare scenarios within same job fingerprint",
        "missing_semantics": "any scenario payload missing => partial missing for sensitivity pair",
        "limitations": "Sensitivity is intra-job only; windows are not independent samples",
    },
    {
        "metric": "window_stability",
        "classification": "derivable_with_assumption",
        "artifact_type": "campaign_aggregate",
        "field_path": "cross_job metric dispersion (out of #4014 single-job scope)",
        "unit": "policy_defined",
        "sign_convention": "n/a",
        "aggregation_rule": "requires cross-window aggregation policy in #4015/#4017",
        "missing_semantics": "not defined at single-job artifact level",
        "limitations": "Deferred to metric extraction and league table stages",
    },
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def scenario_metric_field_path(scenario_id: str, metric_field: str) -> str:
    return f"scenario_metrics.{scenario_id}.metrics.{metric_field}"


def artifact_metrics_field_path(metric_field: str) -> str:
    return f"metrics.{metric_field}"

