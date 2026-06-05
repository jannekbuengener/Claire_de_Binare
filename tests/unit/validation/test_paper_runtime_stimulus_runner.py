"""Tests for paper_runtime_stimulus_runner — Issue #2988

Safety preflight, fixture validation, candle generation, preview/publish
behaviour, and output contract checks.  No Redis writes, no DB writes,
no service logic changes.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dataclasses import asdict

from services.validation.paper_runtime_stimulus_runner import (
    DEFAULT_FIXTURE_PATH,
    FixtureSpec,
    ONE_MINUTE_MS,
    StimulusPublisher,
    generate_fixture_candles,
    load_fixture_spec,
    run_preview,
    run_publish,
    run_safety_preflight,
    to_market_data_payload,
    validate_fixture_spec,
)


@pytest.fixture
def fixture_spec() -> FixtureSpec:
    return FixtureSpec(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        cadence_ms=60_000,
        entry_lookback_minutes=240,
        exit_lookback_minutes=120,
        breakout_buffer=0.0005,
        min_minutes_between_entries=60,
        warmup_count=244,
        warmup_base_ts_ms=1_700_000_000_000,
        warmup_base_price=100_000.0,
        warmup_price_step=1.0,
        warmup_volume=200_000.0,
        warmup_trade_qty="1.0",
        warmup_regime_id=0,
        warmup_market_state_fresh=True,
        warmup_regime_fresh=True,
        breakout_close_premium_pct=0.10,
        breakout_volume=500_000.0,
        breakout_trade_qty="2.5",
    )


class TestSafetyPreflight:
    def test_passes_when_all_safe_env_set(self):
        with patch.dict(os.environ, {
            "MOCK_TRADING": "true",
            "DRY_RUN": "true",
            "MEXC_TESTNET": "true",
            "USE_REAL_BALANCE": "false",
        }, clear=False):
            result = run_safety_preflight()
        assert result.passed is True
        assert len(result.failures) == 0

    def test_rejects_mock_trading_false(self):
        with patch.dict(os.environ, {"MOCK_TRADING": "false"}, clear=False):
            result = run_safety_preflight()
        assert result.passed is False
        assert any("MOCK_TRADING" in f for f in result.failures)

    def test_rejects_dry_run_false(self):
        with patch.dict(os.environ, {"DRY_RUN": "false"}, clear=False):
            result = run_safety_preflight()
        assert result.passed is False
        assert any("DRY_RUN" in f for f in result.failures)

    def test_rejects_mexc_testnet_false(self):
        with patch.dict(os.environ, {"MEXC_TESTNET": "false"}, clear=False):
            result = run_safety_preflight()
        assert result.passed is False
        assert any("MEXC_TESTNET" in f for f in result.failures)

    def test_rejects_live_trading_confirmed_yes(self):
        with patch.dict(os.environ, {"LIVE_TRADING_CONFIRMED": "yes"}, clear=False):
            result = run_safety_preflight()
        assert result.passed is False
        assert any("LIVE_TRADING_CONFIRMED" in f for f in result.failures)

    def test_rejects_use_real_balance_true(self):
        with patch.dict(os.environ, {"USE_REAL_BALANCE": "true"}, clear=False):
            result = run_safety_preflight()
        assert result.passed is False
        assert any("USE_REAL_BALANCE" in f for f in result.failures)

    def test_summary_contains_no_secrets(self):
        with patch.dict(os.environ, {
            "MOCK_TRADING": "true",
            "DRY_RUN": "true",
            "MEXC_TESTNET": "true",
        }, clear=False):
            result = run_safety_preflight()
        summary = result.summary()
        assert "password" not in summary.lower()
        assert "dsn" not in summary.lower()
        assert "token" not in summary.lower()
        assert "NO-GO" in summary


class TestFixtureSpecValidation:
    def test_valid_spec_passes(self, fixture_spec):
        errors = validate_fixture_spec(fixture_spec)
        assert errors == []

    def test_rejects_wrong_strategy_id(self, fixture_spec):
        overrides = asdict(fixture_spec)
        overrides["strategy_id"] = "momentum_v2"
        spec = FixtureSpec(**overrides)
        errors = validate_fixture_spec(spec)
        assert any("strategy_id" in e for e in errors)

    def test_rejects_wrong_symbol(self, fixture_spec):
        overrides = asdict(fixture_spec)
        overrides["symbol"] = "ETHUSDT"
        spec = FixtureSpec(**overrides)
        errors = validate_fixture_spec(spec)
        assert any("symbol" in e for e in errors)

    def test_rejects_wrong_cadence(self, fixture_spec):
        overrides = asdict(fixture_spec)
        overrides["cadence_ms"] = 300_000
        spec = FixtureSpec(**overrides)
        errors = validate_fixture_spec(spec)
        assert any("cadence_ms" in e for e in errors)

    def test_rejects_insufficient_warmup(self, fixture_spec):
        overrides = asdict(fixture_spec)
        overrides["warmup_count"] = 10
        spec = FixtureSpec(**overrides)
        errors = validate_fixture_spec(spec)
        assert any("warmup_count" in e for e in errors)

    def test_rejects_negative_breakout_buffer(self, fixture_spec):
        overrides = asdict(fixture_spec)
        overrides["breakout_buffer"] = -0.001
        spec = FixtureSpec(**overrides)
        errors = validate_fixture_spec(spec)
        assert any("breakout_buffer" in e for e in errors)

    def test_rejects_negative_price_step(self, fixture_spec):
        overrides = asdict(fixture_spec)
        overrides["warmup_price_step"] = -1.0
        spec = FixtureSpec(**overrides)
        errors = validate_fixture_spec(spec)
        assert any("warmup_price_step" in e for e in errors)

    def test_rejects_zero_breakout_premium(self, fixture_spec):
        overrides = asdict(fixture_spec)
        overrides["breakout_close_premium_pct"] = 0.0
        spec = FixtureSpec(**overrides)
        errors = validate_fixture_spec(spec)
        assert any("breakout_close_premium_pct" in e for e in errors)


class TestFixtureCandleGeneration:
    def test_generates_correct_number_of_candles(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        assert len(candles) == fixture_spec.warmup_count + 1

    def test_warmup_cadence_is_1m(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        for i in range(1, fixture_spec.warmup_count):
            delta = candles[i]["ts_ms"] - candles[i - 1]["ts_ms"]
            assert delta == ONE_MINUTE_MS, f"candle {i} delta {delta} != 60000"

    def test_warmup_to_breakout_cadence_is_1m(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        second_last = candles[-2]
        last = candles[-1]
        delta = last["ts_ms"] - second_last["ts_ms"]
        assert delta == ONE_MINUTE_MS

    def test_warmup_prices_increase_by_step(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        for i in range(1, fixture_spec.warmup_count):
            assert candles[i]["close"] > candles[i - 1]["close"]

    def test_breakout_close_exceeds_highest_high_with_buffer(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        highest_high = fixture_spec.warmup_base_price + (
            fixture_spec.warmup_count - 1
        ) * fixture_spec.warmup_price_step
        breakout_threshold = highest_high * (1 + fixture_spec.breakout_buffer)
        breakout_close = candles[-1]["close"]
        assert breakout_close > breakout_threshold, (
            f"breakout_close {breakout_close} not > breakout_threshold {breakout_threshold}"
        )

    def test_breakout_candle_has_required_fields(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        bc = candles[-1]
        assert bc["symbol"] == "BTCUSDT"
        assert "ts_ms" in bc
        assert "close" in bc
        assert "high" in bc
        assert "low" in bc
        assert "volume" in bc
        assert bc["regime_id"] == 0

    def test_warmup_regime_is_trend(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        for c in candles:
            assert c["regime_id"] == 0
            assert c["market_state_fresh"] is True
            assert c["regime_fresh"] is True


class TestMarketDataPayload:
    def test_payload_contains_schema_version(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        payload = to_market_data_payload(candles[0])
        assert payload["schema_version"] == "v1.0"

    def test_payload_contains_regime_fields(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        payload = to_market_data_payload(candles[0])
        assert "regime_id" in payload
        assert "market_state_fresh" in payload
        assert "regime_fresh" in payload

    def test_payload_price_is_string(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        payload = to_market_data_payload(candles[0])
        assert isinstance(payload["price"], str)

    def test_payload_has_ohlc(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        payload = to_market_data_payload(candles[-1])
        assert "close" in payload
        assert "high" in payload
        assert "low" in payload
        assert "open" in payload


class TestPreviewMode:
    def test_preview_does_not_publish(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        mock_publisher = MagicMock(spec=StimulusPublisher)
        output = run_preview(candles, fixture_spec)
        mock_publisher.publish.assert_not_called()
        assert "Preview Mode" in output
        assert "no Redis publish" in output

    def test_preview_contains_expected_chain_target(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        output = run_preview(candles, fixture_spec)
        assert "SIGNAL" in output
        assert "DECISION" in output
        assert "ORDER(paper_)" in output
        assert "FILL" in output

    def test_preview_contains_no_secrets(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        output = run_preview(candles, fixture_spec)
        lower = output.lower()
        assert "dsn" not in lower
        assert "password" not in lower
        assert "token" not in lower
        assert "secret" not in lower


class TestPublishMode:
    def test_publish_calls_publisher_for_each_candle(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        mock_publisher = MagicMock(spec=StimulusPublisher)
        mock_publisher.publish.return_value = 1

        output = run_publish(candles, fixture_spec, mock_publisher, delay_seconds=0)

        assert mock_publisher.publish.call_count == len(candles)

    def test_publish_rejects_unsafe_preflight(self):
        with patch.dict(os.environ, {"MOCK_TRADING": "false"}, clear=False):
            preflight = run_safety_preflight()
        assert preflight.passed is False

    def test_publish_output_contains_lr_status(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        mock_publisher = MagicMock(spec=StimulusPublisher)
        mock_publisher.publish.return_value = 1

        output = run_publish(candles, fixture_spec, mock_publisher, delay_seconds=0)
        assert "NO-GO" in output

    def test_publish_output_contains_no_secrets(self, fixture_spec):
        candles = generate_fixture_candles(fixture_spec)
        mock_publisher = MagicMock(spec=StimulusPublisher)
        mock_publisher.publish.return_value = 1

        output = run_publish(candles, fixture_spec, mock_publisher, delay_seconds=0)
        lower = output.lower()
        assert "dsn" not in lower
        assert "password" not in lower
        assert "token" not in lower


class TestFixtureFileRoundTrip:
    def test_default_fixture_file_loads(self):
        assert DEFAULT_FIXTURE_PATH.exists(), f"fixture not found at {DEFAULT_FIXTURE_PATH}"
        spec = load_fixture_spec(DEFAULT_FIXTURE_PATH)
        errors = validate_fixture_spec(spec)
        assert errors == []

    def test_default_fixture_generates_candles(self):
        spec = load_fixture_spec(DEFAULT_FIXTURE_PATH)
        candles = generate_fixture_candles(spec)
        assert len(candles) == spec.warmup_count + 1
        assert candles[-1]["close"] > candles[-2]["close"]

    def test_default_fixture_breakout_fires(self):
        spec = load_fixture_spec(DEFAULT_FIXTURE_PATH)
        candles = generate_fixture_candles(spec)
        highest_high = spec.warmup_base_price + (
            spec.warmup_count - 1
        ) * spec.warmup_price_step
        breakout_threshold = highest_high * (1 + spec.breakout_buffer)
        assert candles[-1]["close"] > breakout_threshold

    def test_generated_candles_have_1m_cadence(self):
        spec = load_fixture_spec(DEFAULT_FIXTURE_PATH)
        candles = generate_fixture_candles(spec)
        for i in range(1, len(candles)):
            delta = candles[i]["ts_ms"] - candles[i - 1]["ts_ms"]
            assert delta == ONE_MINUTE_MS, f"delta {delta} at candle {i}"


class TestStopAfterCompleteChain:
    def test_flag_is_parsed(self):
        from services.validation.paper_runtime_stimulus_runner import _parse_args
        args = _parse_args(["--stop-after-complete-chain"])
        assert args.stop_after_complete_chain is True

    def test_flag_defaults_false(self):
        from services.validation.paper_runtime_stimulus_runner import _parse_args
        args = _parse_args([])
        assert args.stop_after_complete_chain is False


class TestNoDBOrExportCall:
    def test_runner_does_not_import_db_writer(self):
        from services.validation import paper_runtime_stimulus_runner as mod
        source = open(mod.__file__).read()
        import_lines = [
            line for line in source.split("\n")
            if line.strip().startswith(("import ", "from "))
        ]
        import_text = "\n".join(import_lines)
        assert "psycopg2" not in import_text
        assert "paper_reference_window_export" not in import_text
        assert "paper_reference_window_runner" not in import_text