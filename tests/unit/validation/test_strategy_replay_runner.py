"""Unit tests for services/validation/strategy_replay_runner.py.

Tests cover:
  - AcceleratedShadowReplayConfig defaults and fail-closed validation
  - _load_candles: JSON array, JSONL, missing file, empty file, malformed JSON
  - _build_replay_report_input: correct field mapping, determinism toggle
  - run_accelerated_shadow_replay: exit codes 0/1/2, dry-run, bundle written
  - main(): arg parsing, defaults, exit codes
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from services.validation.replay_reporter import ReplayReporter
from services.validation.strategy_replay_runner import (
    _DEFAULT_ADAPTER_ID,
    _DEFAULT_OUTPUT_DIR,
    _DEFAULT_STRATEGY_ID,
    _DEFAULT_SYMBOL,
    AcceleratedShadowReplayConfig,
    ReplayRunnerError,
    _build_replay_report_input,
    _load_candles,
    run_accelerated_shadow_replay,
    main,
)
from core.replay.canonical_json import canonical_hash


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _minimal_backtest_report(
    *,
    run_id: str = "bt-abc1234567890123",
    deterministic_ok: bool = True,
    signals_total: int = 6,
    buy_signals_total: int = 3,
    closed_trades_total: int = 3,
    candles_total: int = 400,
    period_start_ts_ms: int = 1_700_000_000_000,
    period_end_ts_ms: int = 1_700_100_000_000,
    gate_status: str = "PASS",
) -> dict:
    return {
        "schema_version": "strategy_validation_report.v1",
        "strategy_id": "primary_breakout_v1",
        "run_metadata": {
            "run_id": run_id,
            "generated_at": "2023-11-14T00:00:00+00:00",
            "source": "historical_backtest_v1",
            "code_commit": "abc1234",
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
            "candles_total": candles_total,
            "requested_period_start_ts_ms": period_start_ts_ms,
            "requested_period_end_ts_ms": period_end_ts_ms,
            "period_start_ts_ms": period_start_ts_ms,
            "period_end_ts_ms": period_end_ts_ms,
        },
        "metrics": {
            "signals_total": signals_total,
            "buy_signals_total": buy_signals_total,
            "sell_signals_total": 3,
            "closed_trades_total": closed_trades_total,
            "win_rate": 0.67,
            "profit_factor": 1.3,
            "expectancy_r": 0.1,
            "max_drawdown_r": 1.5,
            "market_state_fresh_ratio": 0.99,
            "regime_fresh_ratio": 0.99,
            "data_integrity_ok": True,
            "deterministic_replay_ok": deterministic_ok,
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
        "gate_result": {"status": gate_status, "failed_criteria": [], "review_flags": []},
    }


def _minimal_valid_config(**overrides) -> AcceleratedShadowReplayConfig:
    defaults = {"input_candles_file": "candles.json"}
    defaults.update(overrides)
    return AcceleratedShadowReplayConfig(**defaults)


# ---------------------------------------------------------------------------
# TestAcceleratedShadowReplayConfig
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestAcceleratedShadowReplayConfig:
    def test_defaults_are_set(self):
        cfg = AcceleratedShadowReplayConfig(input_candles_file="input.json")
        assert cfg.strategy_id == _DEFAULT_STRATEGY_ID
        assert cfg.symbol == _DEFAULT_SYMBOL
        assert cfg.adapter_id == _DEFAULT_ADAPTER_ID
        assert cfg.speedup_profile == "instant"
        assert cfg.output_directory == _DEFAULT_OUTPUT_DIR
        assert cfg.order_size == 1.0
        assert cfg.order_book_depth_multiplier == 10_000.0
        assert cfg.entry_lookback_minutes == 240
        assert cfg.exit_lookback_minutes == 120
        assert cfg.breakout_buffer == 0.0005
        assert cfg.min_minutes_between_entries == 60
        assert cfg.dry_run is False
        assert cfg.deterministic_verify is False

    def test_validate_passes_valid_config(self):
        cfg = AcceleratedShadowReplayConfig(input_candles_file="candles.json")
        cfg.validate()  # Must not raise

    def test_validate_fails_missing_input_file(self):
        cfg = AcceleratedShadowReplayConfig(input_candles_file="")
        with pytest.raises(ValueError, match="input_candles_file is required"):
            cfg.validate()

    def test_validate_fails_unsupported_strategy_id(self):
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file="x.json", strategy_id="unsupported_strategy"
        )
        with pytest.raises(ValueError, match="unsupported strategy_id"):
            cfg.validate()

    def test_validate_fails_unsupported_symbol(self):
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file="x.json", symbol="ETHUSDT"
        )
        with pytest.raises(ValueError, match="unsupported symbol"):
            cfg.validate()

    def test_validate_fails_unsupported_adapter_id(self):
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file="x.json", adapter_id="unknown_adapter"
        )
        with pytest.raises(ValueError, match="unsupported adapter_id"):
            cfg.validate()

    def test_validate_fails_unsupported_speedup_profile(self):
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file="x.json",
            speedup_profile="100x",
        )
        with pytest.raises(ValueError, match="Unknown speedup profile"):
            cfg.validate()

    def test_validate_fails_zero_order_size(self):
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file="x.json", order_size=0.0
        )
        with pytest.raises(ValueError, match="order_size must be > 0"):
            cfg.validate()

    def test_validate_fails_negative_order_size(self):
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file="x.json", order_size=-1.0
        )
        with pytest.raises(ValueError, match="order_size must be > 0"):
            cfg.validate()

    def test_validate_fails_zero_depth_multiplier(self):
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file="x.json", order_book_depth_multiplier=0.0
        )
        with pytest.raises(ValueError, match="order_book_depth_multiplier must be > 0"):
            cfg.validate()

    def test_config_is_frozen(self):
        cfg = AcceleratedShadowReplayConfig(input_candles_file="x.json")
        with pytest.raises((AttributeError, TypeError)):
            cfg.order_size = 99.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestLoadCandles
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestLoadCandles:
    def test_load_json_array(self, tmp_path):
        data = [{"ts_ms": 1_000_000, "close": 50000.0, "high": 51000.0, "low": 49000.0,
                 "regime_id": 0, "symbol": "BTCUSDT"}]
        f = tmp_path / "candles.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        result = _load_candles(f)
        assert len(result) == 1
        assert result[0]["ts_ms"] == 1_000_000

    def test_load_jsonl(self, tmp_path):
        rows = [
            {"ts_ms": 1_000_000, "close": 50000.0},
            {"ts_ms": 1_060_000, "close": 50100.0},
        ]
        f = tmp_path / "candles.jsonl"
        f.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        result = _load_candles(f)
        assert len(result) == 2
        assert result[1]["ts_ms"] == 1_060_000

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ReplayRunnerError, match="not found"):
            _load_candles(tmp_path / "nonexistent.json")

    def test_empty_file_raises(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("", encoding="utf-8")
        with pytest.raises(ReplayRunnerError, match="empty"):
            _load_candles(f)

    def test_malformed_json_array_raises(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("[{bad json", encoding="utf-8")
        with pytest.raises(ReplayRunnerError, match="parse error"):
            _load_candles(f)

    def test_json_array_non_object_row_raises(self, tmp_path):
        f = tmp_path / "bad_row.json"
        f.write_text(json.dumps([{"ts_ms": 1_000_000}, 123]), encoding="utf-8")
        with pytest.raises(ReplayRunnerError, match="must be a JSON object"):
            _load_candles(f)

    def test_malformed_jsonl_raises(self, tmp_path):
        f = tmp_path / "bad.jsonl"
        f.write_text('{"ts_ms": 1}\nbad line\n', encoding="utf-8")
        with pytest.raises(ReplayRunnerError, match="JSONL parse error"):
            _load_candles(f)

    def test_json_non_array_raises(self, tmp_path):
        f = tmp_path / "obj.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        # Does not start with "[" → treated as JSONL; single line is valid dict
        result = _load_candles(f)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_empty_array_raises(self, tmp_path):
        f = tmp_path / "empty_arr.json"
        f.write_text("[]", encoding="utf-8")
        with pytest.raises(ReplayRunnerError, match="empty"):
            _load_candles(f)


# ---------------------------------------------------------------------------
# TestBuildReplayReportInput
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestBuildReplayReportInput:
    def test_builds_valid_input_determinism_ok(self, tmp_path):
        report = _minimal_backtest_report(deterministic_ok=True)
        cfg = _minimal_valid_config()
        result = _build_replay_report_input(report, cfg, "abc1234", tmp_path)

        assert result.schema_version == "replay_report.v1"
        assert result.report_type == "shadow_replay"
        assert result.strategy_id == "primary_breakout_v1"
        assert result.run_spec.replay_run_id == report["run_metadata"]["run_id"]
        assert result.run_spec.code_commit == "abc1234"
        assert result.run_spec.run_mode == "shadow"
        assert result.run_spec.symbol == "BTCUSDT"
        assert result.run_spec.start_ts_ms == report["dataset_summary"]["period_start_ts_ms"]
        assert result.run_spec.end_ts_ms == report["dataset_summary"]["period_end_ts_ms"]

    def test_execution_result_fields(self, tmp_path):
        report = _minimal_backtest_report(
            signals_total=6,
            buy_signals_total=3,
            closed_trades_total=3,
            candles_total=400,
        )
        cfg = _minimal_valid_config()
        result = _build_replay_report_input(report, cfg, "abc1234", tmp_path)

        er = result.execution_result
        assert er.events_processed == 400
        assert er.decisions_made == 6
        # orders_placed counts BUY + SELL signals: 3 + 3 = 6
        assert er.orders_placed == 6
        assert er.fills_recorded == 3
        assert er.envelope_hashes == []

    def test_integrity_ok_when_deterministic(self, tmp_path):
        report = _minimal_backtest_report(deterministic_ok=True)
        cfg = _minimal_valid_config()
        result = _build_replay_report_input(report, cfg, "abc1234", tmp_path)

        assert result.replay_integrity.integrity_ok is True
        assert not result.replay_integrity.failed_checks
        assert result.replay_integrity.envelope_count == 0
        assert len(result.replay_integrity.envelope_chain_hash) == 64
        assert len(result.replay_integrity.event_loop_states_hash) == 64

    def test_integrity_fails_when_not_deterministic(self, tmp_path):
        report = _minimal_backtest_report(deterministic_ok=False)
        cfg = _minimal_valid_config()
        result = _build_replay_report_input(report, cfg, "abc1234", tmp_path)

        assert result.replay_integrity.integrity_ok is False
        assert len(result.replay_integrity.failed_checks) > 0
        assert "deterministic_replay_check_failed" in result.replay_integrity.failed_checks

    def test_gate_result_passed_through(self, tmp_path):
        report = _minimal_backtest_report(gate_status="FAIL")
        cfg = _minimal_valid_config()
        result = _build_replay_report_input(report, cfg, "abc1234", tmp_path)

        assert result.gate_result is not None
        assert result.gate_result["status"] == "FAIL"

    def test_metrics_passed_through(self, tmp_path):
        report = _minimal_backtest_report()
        cfg = _minimal_valid_config()
        result = _build_replay_report_input(report, cfg, "abc1234", tmp_path)

        assert result.metrics is not None
        assert result.metrics["profit_factor"] == 1.3

    def test_config_snapshot_passed_through(self, tmp_path):
        report = _minimal_backtest_report()
        cfg = _minimal_valid_config()
        result = _build_replay_report_input(report, cfg, "abc1234", tmp_path)

        assert result.config_snapshot is not None
        assert "entry_lookback_minutes" in result.config_snapshot

    def test_empty_chain_hash_is_stable(self, tmp_path):
        report = _minimal_backtest_report()
        cfg = _minimal_valid_config()
        r1 = _build_replay_report_input(report, cfg, "abc1234", tmp_path)
        r2 = _build_replay_report_input(report, cfg, "abc1234", tmp_path)

        assert r1.replay_integrity.envelope_chain_hash == r2.replay_integrity.envelope_chain_hash
        assert r1.replay_integrity.envelope_chain_hash == canonical_hash([])

    def test_embeds_scheduler_metadata_in_dataset_summary(self, tmp_path):
        report = _minimal_backtest_report()
        cfg = _minimal_valid_config(speedup_profile="2x")
        scheduler_metadata = {
            "profile": "2x",
            "warmup_count": 240,
            "live_candle_count": 60,
            "event_time_span_ms": 3_540_000,
            "simulated_elapsed_ms": 1_770_000,
        }

        result = _build_replay_report_input(
            report,
            cfg,
            "abc1234",
            tmp_path,
            scheduler_metadata=scheduler_metadata,
        )

        assert result.dataset_summary is not None
        assert result.dataset_summary["scheduler"] == scheduler_metadata


# ---------------------------------------------------------------------------
# TestRunAcceleratedShadowReplay
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRunAcceleratedShadowReplay:
    """Full-flow tests with run_primary_breakout_backtest and ReplayReporter mocked."""

    def _make_candles_file(self, tmp_path: Path, count: int = 300) -> Path:
        candles = [{"ts_ms": 1_000_000 + i * 60_000, "close": 50000.0,
                    "high": 51000.0, "low": 49000.0, "regime_id": 0,
                    "symbol": "BTCUSDT"} for i in range(count)]
        f = tmp_path / "candles.json"
        f.write_text(json.dumps(candles), encoding="utf-8")
        return f

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_successful_run_returns_0(self, mock_write, mock_backtest, tmp_path):
        mock_backtest.return_value = _minimal_backtest_report()
        mock_write.return_value = tmp_path / "bt-abc1234567890123"
        (tmp_path / "bt-abc1234567890123").mkdir()

        f = self._make_candles_file(tmp_path)
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
        )
        exit_code = run_accelerated_shadow_replay(cfg)
        assert exit_code == 0

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_supplementary_artifacts_written(self, mock_write, mock_backtest, tmp_path):
        bundle_dir = tmp_path / "bt-abc1234567890123"
        bundle_dir.mkdir()
        mock_backtest.return_value = _minimal_backtest_report()
        mock_write.return_value = bundle_dir

        f = self._make_candles_file(tmp_path)
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
        )
        run_accelerated_shadow_replay(cfg)

        assert (bundle_dir / "config.resolved.json").exists()
        assert (bundle_dir / "env_redacted.txt").exists()

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_scheduler_metadata_embedded_in_report_input(
        self, mock_write, mock_backtest, tmp_path
    ):
        bundle_dir = tmp_path / "bt-abc1234567890123"
        bundle_dir.mkdir()
        mock_backtest.return_value = _minimal_backtest_report()
        mock_write.return_value = bundle_dir

        f = self._make_candles_file(tmp_path)
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            speedup_profile="2x",
        )
        exit_code = run_accelerated_shadow_replay(cfg)

        assert exit_code == 0
        report_input = mock_write.call_args.args[0]
        assert report_input.dataset_summary is not None
        assert report_input.dataset_summary["scheduler"]["profile"] == "2x"
        assert report_input.dataset_summary["scheduler"]["warmup_count"] == 240

    def test_missing_input_file_returns_2(self, tmp_path):
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(tmp_path / "missing.json"),
            output_directory=str(tmp_path),
        )
        exit_code = run_accelerated_shadow_replay(cfg)
        assert exit_code == 2

    def test_non_object_json_array_row_returns_2(self, tmp_path):
        f = tmp_path / "bad_row.json"
        f.write_text(json.dumps([{"ts_ms": 1_000_000}, 123]), encoding="utf-8")
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
        )
        exit_code = run_accelerated_shadow_replay(cfg)
        assert exit_code == 2

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    def test_bridge_error_returns_2(self, mock_backtest, tmp_path):
        from core.replay.historical_bridge import HistoricalBridgeError
        mock_backtest.side_effect = HistoricalBridgeError("bad candles")

        f = self._make_candles_file(tmp_path)
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
        )
        exit_code = run_accelerated_shadow_replay(cfg)
        assert exit_code == 2

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    def test_backtest_error_returns_2(self, mock_backtest, tmp_path):
        from services.validation.strategy_backtest_runner import PrimaryBreakoutBacktestError
        mock_backtest.side_effect = PrimaryBreakoutBacktestError("boom")

        f = self._make_candles_file(tmp_path)
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
        )
        exit_code = run_accelerated_shadow_replay(cfg)
        assert exit_code == 2

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_reporter_error_returns_2(self, mock_write, mock_backtest, tmp_path):
        from services.validation.replay_reporter import ReplayReporterError
        mock_backtest.return_value = _minimal_backtest_report()
        mock_write.side_effect = ReplayReporterError("schema fail")

        f = self._make_candles_file(tmp_path)
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
        )
        exit_code = run_accelerated_shadow_replay(cfg)
        assert exit_code == 2

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_determinism_warning_but_exit_0_without_flag(
        self, mock_write, mock_backtest, tmp_path, capsys
    ):
        bundle_dir = tmp_path / "bt-abc1234567890123"
        bundle_dir.mkdir()
        mock_backtest.return_value = _minimal_backtest_report(deterministic_ok=False)
        mock_write.return_value = bundle_dir

        f = self._make_candles_file(tmp_path)
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            deterministic_verify=False,
        )
        exit_code = run_accelerated_shadow_replay(cfg)
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "WARNING" in captured.err

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_deterministic_verify_flag_returns_2_on_failure(
        self, mock_write, mock_backtest, tmp_path
    ):
        bundle_dir = tmp_path / "bt-abc1234567890123"
        bundle_dir.mkdir()
        mock_backtest.return_value = _minimal_backtest_report(deterministic_ok=False)
        mock_write.return_value = bundle_dir

        f = self._make_candles_file(tmp_path)
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            deterministic_verify=True,
        )
        exit_code = run_accelerated_shadow_replay(cfg)
        assert exit_code == 2

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_deterministic_verify_flag_exit_0_on_ok(
        self, mock_write, mock_backtest, tmp_path
    ):
        bundle_dir = tmp_path / "bt-abc1234567890123"
        bundle_dir.mkdir()
        mock_backtest.return_value = _minimal_backtest_report(deterministic_ok=True)
        mock_write.return_value = bundle_dir

        f = self._make_candles_file(tmp_path)
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            deterministic_verify=True,
        )
        exit_code = run_accelerated_shadow_replay(cfg)
        assert exit_code == 0

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_backtest_called_with_correct_config(
        self, mock_write, mock_backtest, tmp_path
    ):
        bundle_dir = tmp_path / "bt-abc1234567890123"
        bundle_dir.mkdir()
        mock_backtest.return_value = _minimal_backtest_report()
        mock_write.return_value = bundle_dir

        f = self._make_candles_file(tmp_path)
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            order_size=2.0,
            entry_lookback_minutes=180,
        )
        run_accelerated_shadow_replay(cfg)

        mock_backtest.assert_called_once()
        call_kwargs = mock_backtest.call_args
        run_config = call_kwargs[1]["run_config"]
        assert run_config.order_size == 2.0
        assert run_config.bridge.entry_lookback_minutes == 180


# ---------------------------------------------------------------------------
# TestDryRun
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestDryRun:
    def test_dry_run_returns_0_with_valid_input(self, tmp_path):
        candles = [{"ts_ms": 1_000_000}]
        f = tmp_path / "candles.json"
        f.write_text(json.dumps(candles), encoding="utf-8")

        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            dry_run=True,
        )
        exit_code = run_accelerated_shadow_replay(cfg)
        assert exit_code == 0

    def test_dry_run_prints_candle_count(self, tmp_path, capsys):
        candles = [{"ts_ms": 1_000_000 + i * 60_000} for i in range(5)]
        f = tmp_path / "candles.json"
        f.write_text(json.dumps(candles), encoding="utf-8")

        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            dry_run=True,
        )
        run_accelerated_shadow_replay(cfg)
        captured = capsys.readouterr()
        assert "5" in captured.out
        assert "DRY-RUN" in captured.out

    def test_dry_run_does_not_call_backtest(self, tmp_path):
        candles = [{"ts_ms": 1_000_000}]
        f = tmp_path / "candles.json"
        f.write_text(json.dumps(candles), encoding="utf-8")

        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(f),
            dry_run=True,
        )
        with patch(
            "services.validation.strategy_replay_runner.run_primary_breakout_backtest"
        ) as mock_bt:
            run_accelerated_shadow_replay(cfg)
            mock_bt.assert_not_called()

    def test_dry_run_missing_file_returns_2(self, tmp_path):
        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(tmp_path / "missing.json"),
            dry_run=True,
        )
        exit_code = run_accelerated_shadow_replay(cfg)
        assert exit_code == 2

    def test_dry_run_does_not_write_bundle(self, tmp_path):
        candles = [{"ts_ms": 1_000_000}]
        f = tmp_path / "candles.json"
        f.write_text(json.dumps(candles), encoding="utf-8")

        cfg = AcceleratedShadowReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path / "out"),
            dry_run=True,
        )
        run_accelerated_shadow_replay(cfg)
        # output directory must NOT be created
        assert not (tmp_path / "out").exists()


# ---------------------------------------------------------------------------
# TestMainArgParse
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestMainArgParse:
    def test_missing_input_candles_exits_1_or_2(self, tmp_path):
        with patch("sys.argv", ["prog"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # argparse exits with 2 on missing required arg
            assert exc_info.value.code != 0

    def test_unsupported_strategy_exits_1(self, tmp_path, capsys):
        candles = [{"ts_ms": 1_000_000}]
        f = tmp_path / "c.json"
        f.write_text(json.dumps(candles))
        with patch("sys.argv", ["prog", "--input-candles", str(f),
                                "--strategy-id", "bad_strategy"]):
            result = main()
        assert result == 1

    def test_valid_invocation_calls_runner(self, tmp_path):
        candles = [{"ts_ms": 1_000_000}]
        f = tmp_path / "c.json"
        f.write_text(json.dumps(candles))
        with patch(
            "services.validation.strategy_replay_runner.run_accelerated_shadow_replay",
            return_value=0,
        ) as mock_run:
            with patch("sys.argv", ["prog", "--input-candles", str(f)]):
                result = main()
        assert result == 0
        mock_run.assert_called_once()

    def test_default_strategy_id_is_set(self, tmp_path):
        candles = [{"ts_ms": 1_000_000}]
        f = tmp_path / "c.json"
        f.write_text(json.dumps(candles))
        captured_config = []

        def capture(cfg):
            captured_config.append(cfg)
            return 0

        with patch(
            "services.validation.strategy_replay_runner.run_accelerated_shadow_replay",
            side_effect=capture,
        ):
            with patch("sys.argv", ["prog", "--input-candles", str(f)]):
                main()

        assert captured_config[0].strategy_id == _DEFAULT_STRATEGY_ID

    def test_output_dir_override_applied(self, tmp_path):
        candles = [{"ts_ms": 1_000_000}]
        f = tmp_path / "c.json"
        f.write_text(json.dumps(candles))
        captured = []

        def capture(cfg):
            captured.append(cfg)
            return 0

        custom_dir = str(tmp_path / "custom_out")
        with patch(
            "services.validation.strategy_replay_runner.run_accelerated_shadow_replay",
            side_effect=capture,
        ):
            with patch("sys.argv", [
                "prog", "--input-candles", str(f), "--output-dir", custom_dir
            ]):
                main()

        assert captured[0].output_directory == custom_dir

    def test_dry_run_flag_applied(self, tmp_path):
        candles = [{"ts_ms": 1_000_000}]
        f = tmp_path / "c.json"
        f.write_text(json.dumps(candles))
        captured = []

        def capture(cfg):
            captured.append(cfg)
            return 0

        with patch(
            "services.validation.strategy_replay_runner.run_accelerated_shadow_replay",
            side_effect=capture,
        ):
            with patch("sys.argv", ["prog", "--input-candles", str(f), "--dry-run"]):
                main()

        assert captured[0].dry_run is True

    def test_deterministic_verify_flag_applied(self, tmp_path):
        candles = [{"ts_ms": 1_000_000}]
        f = tmp_path / "c.json"
        f.write_text(json.dumps(candles))
        captured = []

        def capture(cfg):
            captured.append(cfg)
            return 0

        with patch(
            "services.validation.strategy_replay_runner.run_accelerated_shadow_replay",
            side_effect=capture,
        ):
            with patch("sys.argv", [
                "prog", "--input-candles", str(f), "--deterministic-verify"
            ]):
                main()

        assert captured[0].deterministic_verify is True

    def test_speedup_profile_flag_applied(self, tmp_path):
        candles = [{"ts_ms": 1_000_000}]
        f = tmp_path / "c.json"
        f.write_text(json.dumps(candles))
        captured = []

        def capture(cfg):
            captured.append(cfg)
            return 0

        with patch(
            "services.validation.strategy_replay_runner.run_accelerated_shadow_replay",
            side_effect=capture,
        ):
            with patch("sys.argv", ["prog", "--input-candles", str(f), "--speedup-profile", "5x"]):
                main()

        assert captured[0].speedup_profile == "5x"

    def test_exit_code_semantics_0(self, tmp_path):
        candles = [{"ts_ms": 1_000_000}]
        f = tmp_path / "c.json"
        f.write_text(json.dumps(candles))
        with patch(
            "services.validation.strategy_replay_runner.run_accelerated_shadow_replay",
            return_value=0,
        ):
            with patch("sys.argv", ["prog", "--input-candles", str(f)]):
                result = main()
        assert result == 0

    def test_exit_code_semantics_2(self, tmp_path):
        candles = [{"ts_ms": 1_000_000}]
        f = tmp_path / "c.json"
        f.write_text(json.dumps(candles))
        with patch(
            "services.validation.strategy_replay_runner.run_accelerated_shadow_replay",
            return_value=2,
        ):
            with patch("sys.argv", ["prog", "--input-candles", str(f)]):
                result = main()
        assert result == 2
