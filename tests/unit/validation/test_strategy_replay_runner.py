"""Unit tests for services/validation/strategy_replay_runner.py.

Tests cover:
  - ARVPReplayConfig defaults and fail-closed validation
  - _build_replay_report_input: correct field mapping, determinism toggle
  - run_arvp_replay: exit codes 0/1/2, dry-run, bundle written
  - main(): arg parsing, defaults, exit codes
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.replay.scenario_harness import ScenarioHarnessError
from core.replay.scenario_packs import ScenarioPackError
from core.replay.run_registry import ReplayRunRegistry, RunRegistryError
from core.replay.dataset_spec import DatasetSpec
from services.validation.replay_reporter import ReplayReporter
from services.validation.strategy_replay_runner import (
    _DEFAULT_ADAPTER_ID,
    _DEFAULT_OUTPUT_DIR,
    _DEFAULT_STRATEGY_ID,
    _DEFAULT_SYMBOL,
    ARVPReplayConfig,
    ReplayRunnerError,
    _apply_replay_data_overrides,
    _apply_scenario_overrides,
    _build_replay_report_input,
    run_arvp_replay,
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
    data_integrity_reason: str = "clean",
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
            "data_integrity_diagnostics": {
                "data_integrity_reason": data_integrity_reason,
                "open_position_at_end": None,
                "pending_signals_at_end": [],
            },
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


def _minimal_valid_config(**overrides) -> ARVPReplayConfig:
    defaults = {"input_candles_file": "candles.json"}
    defaults.update(overrides)
    return ARVPReplayConfig(**defaults)


# ---------------------------------------------------------------------------
# TestARVPReplayConfig
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestARVPReplayConfig:
    def test_defaults_are_set(self):
        cfg = ARVPReplayConfig(input_candles_file="input.json")
        assert cfg.dataset_source == "file"
        assert cfg.db_dataset_window is None
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
        cfg = ARVPReplayConfig(input_candles_file="candles.json")
        cfg.validate()  # Must not raise

    def test_validate_fails_missing_input_file(self):
        cfg = ARVPReplayConfig(input_candles_file="")
        with pytest.raises(ValueError, match="dataset_source='file' requires input_candles_file"):
            cfg.validate()

    def test_validate_passes_db_source_with_db_dataset_window(self):
        cfg = ARVPReplayConfig(
            dataset_source="db",
            db_dataset_window="1180000:1540000",
        )
        cfg.validate()  # Must not raise

    def test_validate_fails_db_source_missing_db_dataset_window(self):
        cfg = ARVPReplayConfig(dataset_source="db", db_dataset_window=None)
        with pytest.raises(
            ValueError, match="dataset_source='db' requires db_dataset_window"
        ):
            cfg.validate()

    def test_validate_fails_db_source_with_input_candles_file(self):
        cfg = ARVPReplayConfig(
            dataset_source="db",
            db_dataset_window="1180000:1540000",
            input_candles_file="candles.json",
        )
        with pytest.raises(ValueError, match="input_candles_file must be empty"):
            cfg.validate()

    def test_validate_fails_file_source_with_db_dataset_window(self):
        cfg = ARVPReplayConfig(
            dataset_source="file",
            input_candles_file="candles.json",
            db_dataset_window="1180000:1540000",
        )
        with pytest.raises(ValueError, match="db_dataset_window must be None"):
            cfg.validate()

    def test_validate_fails_unknown_dataset_source(self):
        cfg = ARVPReplayConfig(
            dataset_source="s3",
            input_candles_file="candles.json",
        )
        with pytest.raises(ValueError, match="dataset_source must be 'file' or 'db'"):
            cfg.validate()

    def test_db_dataset_id_field_is_not_supported(self):
        with pytest.raises(TypeError):
            ARVPReplayConfig(  # type: ignore[call-arg]
                dataset_source="db",
                db_dataset_id="1180000:1540000",
            )

    def test_validate_fails_db_dataset_window_without_explicit_window(self):
        cfg = ARVPReplayConfig(
            dataset_source="db",
            db_dataset_window="ds-001",
        )
        with pytest.raises(ValueError, match="START_TS_MS:END_TS_MS"):
            cfg.validate()

    def test_validate_fails_db_dataset_window_with_start_gte_end(self):
        cfg = ARVPReplayConfig(
            dataset_source="db",
            db_dataset_window="1540000:1540000",
        )
        with pytest.raises(ValueError, match="start must be < end"):
            cfg.validate()

    def test_validate_fails_unsupported_strategy_id(self):
        cfg = ARVPReplayConfig(
            input_candles_file="x.json", strategy_id="unsupported_strategy"
        )
        with pytest.raises(ValueError, match="unsupported strategy_id"):
            cfg.validate()

    def test_validate_fails_unsupported_symbol(self):
        cfg = ARVPReplayConfig(
            input_candles_file="x.json", symbol="ETHUSDT"
        )
        with pytest.raises(ValueError, match="unsupported symbol"):
            cfg.validate()

    def test_validate_fails_unsupported_adapter_id(self):
        cfg = ARVPReplayConfig(
            input_candles_file="x.json", adapter_id="unknown_adapter"
        )
        with pytest.raises(ValueError, match="unsupported adapter_id"):
            cfg.validate()

    def test_validate_fails_unsupported_speedup_profile(self):
        cfg = ARVPReplayConfig(
            input_candles_file="x.json",
            speedup_profile="100x",
        )
        with pytest.raises(ValueError, match="Unknown speedup profile"):
            cfg.validate()

    def test_validate_fails_zero_order_size(self):
        cfg = ARVPReplayConfig(
            input_candles_file="x.json", order_size=0.0
        )
        with pytest.raises(ValueError, match="order_size must be > 0"):
            cfg.validate()

    def test_validate_fails_negative_order_size(self):
        cfg = ARVPReplayConfig(
            input_candles_file="x.json", order_size=-1.0
        )
        with pytest.raises(ValueError, match="order_size must be > 0"):
            cfg.validate()

    def test_validate_fails_zero_depth_multiplier(self):
        cfg = ARVPReplayConfig(
            input_candles_file="x.json", order_book_depth_multiplier=0.0
        )
        with pytest.raises(ValueError, match="order_book_depth_multiplier must be > 0"):
            cfg.validate()

    def test_config_is_frozen(self):
        cfg = ARVPReplayConfig(input_candles_file="x.json")
        with pytest.raises((AttributeError, TypeError)):
            cfg.order_size = 99.0  # type: ignore[misc]


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

    def test_data_integrity_diagnostics_passed_through(self, tmp_path):
        report = _minimal_backtest_report(data_integrity_reason="open_position_at_end")
        cfg = _minimal_valid_config()
        result = _build_replay_report_input(report, cfg, "abc1234", tmp_path)

        assert result.metrics is not None
        assert result.metrics["data_integrity_diagnostics"] == {
            "data_integrity_reason": "open_position_at_end",
            "open_position_at_end": None,
            "pending_signals_at_end": [],
        }

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
# TestRunARVPReplay
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestRunARVPReplay:
    """Full-flow tests with run_primary_breakout_backtest and ReplayReporter mocked."""

    def _make_candles_file(self, tmp_path: Path, count: int = 300) -> Path:
        candles = [{"ts_ms": 1_000_000 + i * 60_000, "close": 50000.0,
                    "high": 51000.0, "low": 49000.0, "regime_id": 0,
                    "symbol": "BTCUSDT"} for i in range(count)]
        f = tmp_path / "candles.json"
        f.write_text(json.dumps(candles), encoding="utf-8")
        return f

    def _mock_bundle_dir(self, mock_write, tmp_path: Path):
        def _side_effect(report_input, output_dir):
            bundle_dir = Path(output_dir) / report_input.run_spec.replay_run_id
            bundle_dir.mkdir(parents=True, exist_ok=True)
            return bundle_dir

        mock_write.side_effect = _side_effect

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_successful_run_returns_0(self, mock_write, mock_backtest, tmp_path):
        mock_backtest.return_value = _minimal_backtest_report()
        self._mock_bundle_dir(mock_write, tmp_path)

        f = self._make_candles_file(tmp_path)
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
        )
        exit_code = run_arvp_replay(cfg)
        assert exit_code == 0

    @patch("services.validation.strategy_replay_runner.create_postgres_connection")
    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_successful_run_db_dataset_returns_0(
        self, mock_write, mock_backtest, mock_pg, tmp_path
    ):
        mock_backtest.return_value = _minimal_backtest_report()
        self._mock_bundle_dir(mock_write, tmp_path)

        warmup_count = 3
        warmup_start = 1_000_000
        start_ts_ms = warmup_start + warmup_count * 60_000
        rows = [
            (
                warmup_start + i * 60_000,
                100.0,
                101.0,
                99.0,
                100.5,
                10.0,
                100 + i,
                0,
            )
            for i in range(10)
        ]
        end_ts_ms = rows[-1][0]

        cursor = MagicMock()
        cursor.fetchall.return_value = rows
        conn = MagicMock()
        conn.cursor.return_value = cursor
        mock_pg.return_value = conn

        cfg = ARVPReplayConfig(
            dataset_source="db",
            db_dataset_window=f"{start_ts_ms}:{end_ts_ms}",
            output_directory=str(tmp_path),
            entry_lookback_minutes=warmup_count,
            exit_lookback_minutes=2,
        )
        exit_code = run_arvp_replay(cfg)
        assert exit_code == 0
        conn.close.assert_called()

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_supplementary_artifacts_written(self, mock_write, mock_backtest, tmp_path):
        mock_backtest.return_value = _minimal_backtest_report()
        self._mock_bundle_dir(mock_write, tmp_path)

        f = self._make_candles_file(tmp_path)
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
        )
        run_arvp_replay(cfg)

        report_input = mock_write.call_args.args[0]
        bundle_dir = Path(tmp_path) / report_input.run_spec.replay_run_id
        assert (bundle_dir / "config.resolved.json").exists()
        assert (bundle_dir / "env_redacted.txt").exists()

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_scheduler_metadata_embedded_in_report_input(
        self, mock_write, mock_backtest, tmp_path
    ):
        mock_backtest.return_value = _minimal_backtest_report()
        self._mock_bundle_dir(mock_write, tmp_path)

        f = self._make_candles_file(tmp_path)
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            speedup_profile="2x",
        )
        exit_code = run_arvp_replay(cfg)

        assert exit_code == 0
        report_input = mock_write.call_args.args[0]
        assert report_input.dataset_summary is not None
        assert report_input.dataset_summary["scheduler"]["profile"] == "2x"
        assert report_input.dataset_summary["scheduler"]["warmup_count"] == 240

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_successful_run_writes_running_completed_and_operator_summary(
        self, mock_write, mock_backtest, tmp_path
    ):
        mock_backtest.return_value = _minimal_backtest_report(deterministic_ok=True)
        self._mock_bundle_dir(mock_write, tmp_path)

        f = self._make_candles_file(tmp_path)
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            speedup_profile="5x",
        )

        exit_code = run_arvp_replay(cfg)

        assert exit_code == 0
        report_input = mock_write.call_args.args[0]
        run_id = report_input.run_spec.replay_run_id
        registry = ReplayRunRegistry(tmp_path / "run_registry.jsonl")
        records = registry.load_all()
        assert [record.status for record in records] == ["running", "completed"]
        assert all(record.run_id == run_id for record in records)
        summary_path = tmp_path / run_id / "operator_summary.json"
        assert summary_path.exists()
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary["run_id"] == run_id
        assert summary["status"] == "completed"
        assert summary["scheduler_profile"] == "5x"

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    def test_failed_run_writes_failed_state_with_reason(self, mock_backtest, tmp_path):
        from services.validation.strategy_backtest_runner import PrimaryBreakoutBacktestError

        mock_backtest.side_effect = PrimaryBreakoutBacktestError("boom")
        f = self._make_candles_file(tmp_path)
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
        )

        exit_code = run_arvp_replay(cfg)

        assert exit_code == 2
        records = ReplayRunRegistry(tmp_path / "run_registry.jsonl").load_all()
        assert [record.status for record in records] == ["running", "failed"]
        assert "boom" in records[-1].failure_reason

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_summary_and_registry_include_dataset_fingerprint_and_scheduler_profile(
        self, mock_write, mock_backtest, tmp_path
    ):
        mock_backtest.return_value = _minimal_backtest_report()
        self._mock_bundle_dir(mock_write, tmp_path)

        f = self._make_candles_file(tmp_path)
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            speedup_profile="10x",
        )

        exit_code = run_arvp_replay(cfg)

        assert exit_code == 0
        registry = ReplayRunRegistry(tmp_path / "run_registry.jsonl")
        completed = registry.load_all()[-1]
        expected_fingerprint = DatasetSpec(
            symbol="BTCUSDT",
            timeframe="1m",
            start_ts_ms=1_000_000 + 240 * 60_000,
            end_ts_ms=1_000_000 + 299 * 60_000,
            warmup_candles=240,
            source="file",
            file_path=str(f),
        ).fingerprint()
        assert completed.dataset_fingerprint == expected_fingerprint
        assert completed.scheduler_profile == "10x"

        summary_path = tmp_path / completed.run_id / "operator_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary["dataset_fingerprint"] == completed.dataset_fingerprint
        assert summary["scheduler_profile"] == "10x"

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_existing_bundle_behavior_stays_compatible(
        self, mock_write, mock_backtest, tmp_path
    ):
        mock_backtest.return_value = _minimal_backtest_report()
        self._mock_bundle_dir(mock_write, tmp_path)

        f = self._make_candles_file(tmp_path)
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
        )

        exit_code = run_arvp_replay(cfg)

        assert exit_code == 0
        report_input = mock_write.call_args.args[0]
        assert report_input.run_spec.replay_run_id.startswith("replay-")
        assert report_input.run_spec.metadata["execution_provenance_id"].startswith("bt-")
        assert Path(report_input.artifact_manifest.report_artifact_uri).name == "report.json"
        assert (
            Path(
                report_input.artifact_manifest.supplementary_artifacts[
                    "operator_summary_uri"
                ]
            ).name
            == "operator_summary.json"
        )

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    @patch("services.validation.strategy_replay_runner.ReplayRunRegistry.append")
    def test_registry_write_failure_returns_2(
        self, mock_append, mock_write, mock_backtest, tmp_path
    ):
        mock_backtest.return_value = _minimal_backtest_report()
        self._mock_bundle_dir(mock_write, tmp_path)
        mock_append.side_effect = [None, RunRegistryError("disk full")]

        f = self._make_candles_file(tmp_path)
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
        )

        exit_code = run_arvp_replay(cfg)

        assert exit_code == 2

    def test_missing_input_file_returns_2(self, tmp_path):
        cfg = ARVPReplayConfig(
            input_candles_file=str(tmp_path / "missing.json"),
            output_directory=str(tmp_path),
        )
        exit_code = run_arvp_replay(cfg)
        assert exit_code == 2

    def test_non_object_json_array_row_returns_2(self, tmp_path):
        f = tmp_path / "bad_row.json"
        f.write_text(json.dumps([{"ts_ms": 1_000_000}, 123]), encoding="utf-8")
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
        )
        exit_code = run_arvp_replay(cfg)
        assert exit_code == 2

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    def test_bridge_error_returns_2(self, mock_backtest, tmp_path):
        from core.replay.historical_bridge import HistoricalBridgeError
        mock_backtest.side_effect = HistoricalBridgeError("bad candles")

        f = self._make_candles_file(tmp_path)
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
        )
        exit_code = run_arvp_replay(cfg)
        assert exit_code == 2

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    def test_backtest_error_returns_2(self, mock_backtest, tmp_path):
        from services.validation.strategy_backtest_runner import PrimaryBreakoutBacktestError
        mock_backtest.side_effect = PrimaryBreakoutBacktestError("boom")

        f = self._make_candles_file(tmp_path)
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
        )
        exit_code = run_arvp_replay(cfg)
        assert exit_code == 2

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_reporter_error_returns_2(self, mock_write, mock_backtest, tmp_path):
        from services.validation.replay_reporter import ReplayReporterError
        mock_backtest.return_value = _minimal_backtest_report()
        mock_write.side_effect = ReplayReporterError("schema fail")

        f = self._make_candles_file(tmp_path)
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
        )
        exit_code = run_arvp_replay(cfg)
        assert exit_code == 2

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_determinism_warning_but_exit_0_without_flag(
        self, mock_write, mock_backtest, tmp_path, capsys
    ):
        mock_backtest.return_value = _minimal_backtest_report(deterministic_ok=False)
        self._mock_bundle_dir(mock_write, tmp_path)

        f = self._make_candles_file(tmp_path)
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            deterministic_verify=False,
        )
        exit_code = run_arvp_replay(cfg)
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "WARNING" in captured.err

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_deterministic_verify_flag_returns_2_on_failure(
        self, mock_write, mock_backtest, tmp_path
    ):
        mock_backtest.return_value = _minimal_backtest_report(deterministic_ok=False)
        self._mock_bundle_dir(mock_write, tmp_path)

        f = self._make_candles_file(tmp_path)
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            deterministic_verify=True,
        )
        exit_code = run_arvp_replay(cfg)
        assert exit_code == 2

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_deterministic_verify_failure_writes_failed_operator_summary(
        self, mock_write, mock_backtest, tmp_path
    ):
        mock_backtest.return_value = _minimal_backtest_report(deterministic_ok=False)
        self._mock_bundle_dir(mock_write, tmp_path)

        f = self._make_candles_file(tmp_path)
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            deterministic_verify=True,
        )
        exit_code = run_arvp_replay(cfg)

        assert exit_code == 2
        registry = ReplayRunRegistry(tmp_path / "run_registry.jsonl")
        records = registry.load_all()
        assert [r.status for r in records] == ["running", "failed"]
        failed = records[-1]
        summary_path = tmp_path / failed.run_id / "operator_summary.json"
        assert summary_path.exists()
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary["status"] == "failed"
        assert "deterministic" in summary["failure_reason"].lower()

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_deterministic_verify_flag_exit_0_on_ok(
        self, mock_write, mock_backtest, tmp_path
    ):
        mock_backtest.return_value = _minimal_backtest_report(deterministic_ok=True)
        self._mock_bundle_dir(mock_write, tmp_path)

        f = self._make_candles_file(tmp_path)
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            deterministic_verify=True,
        )
        exit_code = run_arvp_replay(cfg)
        assert exit_code == 0

    @patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest")
    @patch.object(ReplayReporter, "write_bundle")
    def test_backtest_called_with_correct_config(
        self, mock_write, mock_backtest, tmp_path
    ):
        mock_backtest.return_value = _minimal_backtest_report()
        self._mock_bundle_dir(mock_write, tmp_path)

        f = self._make_candles_file(tmp_path)
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            order_size=2.0,
            entry_lookback_minutes=180,
        )
        run_arvp_replay(cfg)

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
    def _make_valid_candles_file(self, tmp_path: Path, count: int = 10) -> Path:
        candles = [
            {
                "symbol": "BTCUSDT",
                "ts_ms": 1_000_000 + i * 60_000,
                "high": 51000.0,
                "low": 49000.0,
                "close": 50000.0,
                "regime_id": 0,
            }
            for i in range(count)
        ]
        f = tmp_path / "candles.json"
        f.write_text(json.dumps(candles), encoding="utf-8")
        return f

    def test_dry_run_returns_0_with_valid_input(self, tmp_path):
        f = self._make_valid_candles_file(tmp_path, count=5)

        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            dry_run=True,
            entry_lookback_minutes=1,
            exit_lookback_minutes=1,
        )
        exit_code = run_arvp_replay(cfg)
        assert exit_code == 0

    def test_dry_run_prints_candle_count(self, tmp_path, capsys):
        f = self._make_valid_candles_file(tmp_path, count=5)

        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            dry_run=True,
            entry_lookback_minutes=1,
            exit_lookback_minutes=1,
        )
        run_arvp_replay(cfg)
        captured = capsys.readouterr()
        assert "candles_total=5" in captured.out
        assert "DRY-RUN" in captured.out

    def test_dry_run_does_not_call_backtest(self, tmp_path):
        f = self._make_valid_candles_file(tmp_path, count=5)

        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            dry_run=True,
            entry_lookback_minutes=1,
            exit_lookback_minutes=1,
        )
        with patch(
            "services.validation.strategy_replay_runner.run_primary_breakout_backtest"
        ) as mock_bt:
            run_arvp_replay(cfg)
            mock_bt.assert_not_called()

    def test_dry_run_missing_file_returns_2(self, tmp_path):
        cfg = ARVPReplayConfig(
            input_candles_file=str(tmp_path / "missing.json"),
            dry_run=True,
        )
        exit_code = run_arvp_replay(cfg)
        assert exit_code == 2

    def test_dry_run_does_not_write_bundle(self, tmp_path):
        f = self._make_valid_candles_file(tmp_path, count=5)

        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path / "out"),
            dry_run=True,
            entry_lookback_minutes=1,
            exit_lookback_minutes=1,
        )
        run_arvp_replay(cfg)
        # output directory must NOT be created
        assert not (tmp_path / "out").exists()

    def test_scenario_group_dry_run_returns_0(self, tmp_path, capsys):
        f = self._make_valid_candles_file(tmp_path, count=5)

        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            dry_run=True,
            scenario_ids=("baseline", "delayed_execution"),
            entry_lookback_minutes=1,
            exit_lookback_minutes=1,
        )

        exit_code = run_arvp_replay(cfg)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "scenario group" in captured.out

    def test_scenario_group_dry_run_db_dataset_window_returns_0(self, tmp_path, capsys):
        warmup_count = 3
        warmup_start = 1_000_000
        start_ts_ms = warmup_start + warmup_count * 60_000
        rows = [
            (
                warmup_start + i * 60_000,
                100.0,
                101.0,
                99.0,
                100.5,
                10.0,
                100 + i,
                0,
            )
            for i in range(10)
        ]
        end_ts_ms = rows[-1][0]

        cursor = MagicMock()
        cursor.fetchall.return_value = rows
        conn = MagicMock()
        conn.cursor.return_value = cursor

        cfg = ARVPReplayConfig(
            dataset_source="db",
            db_dataset_window=f"{start_ts_ms}:{end_ts_ms}",
            output_directory=str(tmp_path),
            dry_run=True,
            scenario_ids=("baseline", "delayed_execution"),
            entry_lookback_minutes=warmup_count,
            exit_lookback_minutes=2,
        )

        with patch(
            "services.validation.strategy_replay_runner.create_postgres_connection",
            return_value=conn,
        ):
            exit_code = run_arvp_replay(cfg)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "scenario group" in captured.out
        assert "source='db'" in captured.out

    @pytest.mark.parametrize(
        ("error_cls", "message"),
        [
            (ScenarioHarnessError, "invalid scenario group"),
            (ScenarioPackError, "unknown scenario pack"),
        ],
    )
    def test_scenario_group_runtime_errors_return_2(
        self, tmp_path, capsys, error_cls, message
    ):
        f = self._make_valid_candles_file(tmp_path, count=5)

        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            scenario_ids=("baseline",),
            entry_lookback_minutes=1,
            exit_lookback_minutes=1,
        )

        with patch(
            "services.validation.strategy_replay_runner.run_builtin_scenario_group",
            side_effect=error_cls(message),
        ):
            exit_code = run_arvp_replay(cfg)

        assert exit_code == 2
        captured = capsys.readouterr()
        assert f"ERROR: {message}" in captured.err


# ---------------------------------------------------------------------------
# TestScenarioOverrides
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestScenarioOverrides:
    def test_apply_scenario_overrides_maps_explicit_bar_delay(self):
        cfg = ARVPReplayConfig(input_candles_file="candles.json")

        result = _apply_scenario_overrides(
            cfg,
            {
                "execution_delay_bars": 1,
                "execution_posture": "delayed",
            },
        )

        assert result.simulator_config["EXECUTION_DELAY_BARS"] == 1
        assert result.simulator_config["_execution_posture"] == "delayed"
        assert result.replay_data_overrides == {}

    def test_apply_scenario_overrides_rejects_execution_delay_ms(self):
        cfg = ARVPReplayConfig(input_candles_file="candles.json")

        with pytest.raises(ReplayRunnerError, match="unknown keys"):
            _apply_scenario_overrides(cfg, {"execution_delay_ms": 500})

    def test_apply_scenario_overrides_maps_feed_gap_to_replay_data_surface(self):
        cfg = ARVPReplayConfig(input_candles_file="candles.json")

        result = _apply_scenario_overrides(cfg, {"feed_gap_bars": 2})

        assert result.simulator_config == {}
        assert result.replay_data_overrides == {"feed_gap_bars": 2}

    def test_apply_scenario_overrides_rejects_seconds_gap_semantics(self):
        cfg = ARVPReplayConfig(input_candles_file="candles.json")

        with pytest.raises(ReplayRunnerError, match="not representable"):
            _apply_scenario_overrides(cfg, {"feed_gap_seconds": 30})


@pytest.mark.unit
class TestReplayDataOverrides:
    def test_apply_replay_data_overrides_injects_midpoint_gap(self):
        candles = [
            {
                "symbol": "BTCUSDT",
                "ts_ms": 1_000_000 + i * 60_000,
                "open": 100.0 + i,
                "high": 101.0 + i,
                "low": 99.0 + i,
                "close": 100.5 + i,
                "volume": 10.0 + i,
                "regime_id": 0,
                "market_state_fresh": True,
                "regime_fresh": True,
            }
            for i in range(10)
        ]

        perturbed = _apply_replay_data_overrides(
            candles,
            {"feed_gap_bars": 2},
            warmup_count=4,
        )

        assert perturbed[6]["data_gap_active"] is True
        assert perturbed[7]["data_gap_active"] is True
        assert perturbed[6]["market_state_fresh"] is False
        assert perturbed[7]["regime_fresh"] is False
        assert perturbed[6]["close"] == candles[5]["close"]
        assert perturbed[7]["high"] == candles[5]["high"]
        assert perturbed[6]["ts_ms"] == candles[6]["ts_ms"]
        assert perturbed[7]["ts_ms"] == candles[7]["ts_ms"]
        assert "data_gap_active" not in perturbed[5]

    def test_apply_replay_data_overrides_rejects_gap_covering_all_live_bars(self):
        candles = [
            {
                "symbol": "BTCUSDT",
                "ts_ms": 1_000_000 + i * 60_000,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 10.0,
                "regime_id": 0,
            }
            for i in range(6)
        ]

        with pytest.raises(ReplayRunnerError, match="unaffected live candle"):
            _apply_replay_data_overrides(
                candles,
                {"feed_gap_bars": 3},
                warmup_count=3,
            )


# ---------------------------------------------------------------------------
# TestMainArgParse
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestMainArgParse:
    def test_missing_input_candles_exits_1_or_2(self, tmp_path):
        with patch("sys.argv", ["prog"]):
            assert main() == 1

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
            "services.validation.strategy_replay_runner.run_arvp_replay",
            return_value=0,
        ) as mock_run:
            with patch("sys.argv", ["prog", "--input-candles", str(f)]):
                result = main()
        assert result == 0
        mock_run.assert_called_once()

    def test_db_invocation_calls_runner(self, tmp_path):
        with patch(
            "services.validation.strategy_replay_runner.run_arvp_replay",
            return_value=0,
        ) as mock_run:
            with patch(
                "sys.argv",
                [
                    "prog",
                    "--dataset-source",
                    "db",
                    "--db-dataset-window",
                    "1180000:1540000",
                ],
            ):
                result = main()
        assert result == 0
        mock_run.assert_called_once()

    def test_db_missing_db_dataset_window_exits_1(self, tmp_path):
        with patch(
            "sys.argv",
            [
                "prog",
                "--dataset-source",
                "db",
            ],
        ):
            assert main() == 1

    def test_db_with_input_candles_is_rejected(self, tmp_path):
        candles = [{"ts_ms": 1_000_000}]
        f = tmp_path / "c.json"
        f.write_text(json.dumps(candles))
        with patch(
            "sys.argv",
            [
                "prog",
                "--dataset-source",
                "db",
                "--db-dataset-window",
                "1180000:1540000",
                "--input-candles",
                str(f),
            ],
        ):
            assert main() == 1

    def test_db_dataset_id_flag_is_not_supported(self, tmp_path):
        with patch(
            "sys.argv",
            [
                "prog",
                "--dataset-source",
                "db",
                "--db-dataset-id",
                "1180000:1540000",
            ],
        ):
            with pytest.raises(SystemExit):
                main()

    def test_default_strategy_id_is_set(self, tmp_path):
        candles = [{"ts_ms": 1_000_000}]
        f = tmp_path / "c.json"
        f.write_text(json.dumps(candles))
        captured_config = []

        def capture(cfg):
            captured_config.append(cfg)
            return 0

        with patch(
            "services.validation.strategy_replay_runner.run_arvp_replay",
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
            "services.validation.strategy_replay_runner.run_arvp_replay",
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
            "services.validation.strategy_replay_runner.run_arvp_replay",
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
            "services.validation.strategy_replay_runner.run_arvp_replay",
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
            "services.validation.strategy_replay_runner.run_arvp_replay",
            side_effect=capture,
        ):
            with patch("sys.argv", ["prog", "--input-candles", str(f), "--speedup-profile", "5x"]):
                main()

        assert captured[0].speedup_profile == "5x"

    def test_gate_trace_path_flag_applied(self, tmp_path):
        candles = [{"ts_ms": 1_000_000}]
        f = tmp_path / "c.json"
        f.write_text(json.dumps(candles))
        captured = []
        trace_path = tmp_path / "gate.jsonl"

        def capture(cfg):
            captured.append(cfg)
            return 0

        with patch(
            "services.validation.strategy_replay_runner.run_arvp_replay",
            side_effect=capture,
        ):
            with patch("sys.argv", [
                "prog", "--input-candles", str(f), "--gate-trace-path", str(trace_path)
            ]):
                main()

        assert captured[0].gate_trace_path == trace_path

    def test_validate_fails_on_gate_trace_with_scenario_group(self):
        cfg = ARVPReplayConfig(
            input_candles_file="c.json",
            scenario_ids=("baseline",),
            gate_trace_path=Path("trace.jsonl"),
        )
        with pytest.raises(ValueError, match="not supported with --scenario-group"):
            cfg.validate()

    def test_run_arvp_replay_propagates_gate_trace_path(self, tmp_path):
        from services.validation.strategy_replay_runner import run_arvp_replay

        f = tmp_path / "c.json"
        candles = [{"ts_ms": 1_000_000 + i * 60_000, "close": 100.0, "high": 101.0,
                   "low": 99.0, "regime_id": 0, "symbol": "BTCUSDT"} for i in range(250)]
        f.write_text(json.dumps(candles))

        trace_path = tmp_path / "gate.jsonl"
        cfg = ARVPReplayConfig(
            input_candles_file=str(f),
            output_directory=str(tmp_path),
            gate_trace_path=trace_path,
        )

        with patch("services.validation.strategy_replay_runner.run_primary_breakout_backtest") as mock_bt:
            mock_bt.return_value = _minimal_backtest_report()
            with patch.object(ReplayReporter, "write_bundle") as mock_write:
                mock_write.return_value = tmp_path / "bundle"
                run_arvp_replay(cfg)

                assert mock_bt.call_args.kwargs["gate_trace_path"] == trace_path

    def test_exit_code_semantics_0(self, tmp_path):
        candles = [{"ts_ms": 1_000_000}]
        f = tmp_path / "c.json"
        f.write_text(json.dumps(candles))
        with patch(
            "services.validation.strategy_replay_runner.run_arvp_replay",
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
            "services.validation.strategy_replay_runner.run_arvp_replay",
            return_value=2,
        ):
            with patch("sys.argv", ["prog", "--input-candles", str(f)]):
                result = main()
        assert result == 2
