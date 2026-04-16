"""Tests for primary_breakout_v1 validation report contract and thresholds."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = PROJECT_ROOT / "docs" / "contracts" / "strategy_validation_report_v1.schema.json"
THRESHOLDS_PATH = (
    PROJECT_ROOT / "docs" / "evidence" / "primary_breakout_v1_validation_thresholds.json"
)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _valid_report_payload() -> dict:
    return {
        "schema_version": "strategy_validation_report.v1",
        "strategy_id": "primary_breakout_v1",
        "run_metadata": {
            "run_id": "bt-20260410-001",
            "generated_at": "2026-04-10T10:00:00Z",
            "source": "historical_backtest_v1",
            "code_commit": "a9a62be0a4bdf552acc7466eaa890f2ac36ddd58",
        },
        "config_snapshot": {
            "entry_lookback_minutes": 240,
            "exit_lookback_minutes": 120,
            "breakout_buffer": 0.0005,
            "min_minutes_between_entries": 60,
            "trade_side_mode": "long_only",
        },
        "dataset_summary": {
            "symbol": "BTCUSDT",
            "timeframe": "1m",
            "candles_total": 3000,
            "requested_period_start_ts_ms": 1_699_985_600_000,
            "requested_period_end_ts_ms": 1_700_179_940_000,
            "period_start_ts_ms": 1_700_000_000_000,
            "period_end_ts_ms": 1_700_179_940_000,
        },
        "metrics": {
            "signals_total": 120,
            "buy_signals_total": 60,
            "sell_signals_total": 60,
            "closed_trades_total": 40,
            "win_rate": 0.52,
            "profit_factor": 1.22,
            "expectancy_r": 0.08,
            "max_drawdown_r": 1.8,
            "market_state_fresh_ratio": 1.0,
            "regime_fresh_ratio": 0.995,
            "data_integrity_ok": True,
            "deterministic_replay_ok": True,
        },
        "thresholds_applied": {
            "threshold_profile_id": "primary_breakout_v1_validation_thresholds",
            "threshold_profile_version": "1",
            "pass_fail": {
                "min_closed_trades_total": 20,
                "min_profit_factor": 1.05,
                "min_expectancy_r": 0.0,
                "max_max_drawdown_r": 3.0,
                "min_market_state_fresh_ratio": 0.99,
                "min_regime_fresh_ratio": 0.99,
                "require_data_integrity_ok": True,
                "require_deterministic_replay_ok": True,
            },
        },
        "gate_result": {
            "status": "PASS",
            "failed_criteria": [],
            "review_flags": [],
        },
    }


@pytest.mark.unit
def test_schema_is_valid_and_strict() -> None:
    schema = _load_json(SCHEMA_PATH)
    Draft7Validator.check_schema(schema)
    assert schema["additionalProperties"] is False


@pytest.mark.unit
def test_valid_report_payload_passes_schema() -> None:
    schema = _load_json(SCHEMA_PATH)
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(_valid_report_payload()))
    assert errors == []


@pytest.mark.unit
def test_schema_rejects_additional_properties_fail_closed() -> None:
    schema = _load_json(SCHEMA_PATH)
    payload = _valid_report_payload()
    payload["metrics"]["unexpected_metric"] = 123

    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(payload))
    assert errors
    assert "additional properties are not allowed" in errors[0].message.lower()


@pytest.mark.unit
def test_schema_rejects_wrong_strategy_id_fail_closed() -> None:
    schema = _load_json(SCHEMA_PATH)
    payload = _valid_report_payload()
    payload["strategy_id"] = "other_strategy"

    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(payload))
    assert errors


@pytest.mark.unit
def test_threshold_profile_is_consistent_and_fail_closed() -> None:
    thresholds = _load_json(THRESHOLDS_PATH)

    assert thresholds["schema_version"] == "strategy_validation_thresholds.v1"
    assert thresholds["strategy_id"] == "primary_breakout_v1"
    assert thresholds["threshold_profile_id"] == "primary_breakout_v1_validation_thresholds"
    assert thresholds["threshold_profile_version"] == "1"

    pass_fail = thresholds["pass_fail"]
    review = thresholds["review_only"]

    assert pass_fail["require_data_integrity_ok"] is True
    assert pass_fail["require_deterministic_replay_ok"] is True

    # Review criteria must be stricter than pass/fail gates.
    assert review["min_closed_trades_recommended"] >= pass_fail["min_closed_trades_total"]
    assert review["min_profit_factor_recommended"] >= pass_fail["min_profit_factor"]
    assert review["max_max_drawdown_r_recommended"] <= pass_fail["max_max_drawdown_r"]
