"""ARVP replay CLI entry point for primary_breakout_v1.

Thin operator-facing CLI that:
  - validates a minimal replay config fail-closed
  - loads historical candle input from file or db via the canonical dataset layer
  - delegates to the existing backtest surface (strategy_backtest_runner)
  - builds a ReplayReportInput and writes the artifact bundle via ReplayReporter
  - writes supplementary artifacts (config.resolved.json, env_redacted.txt)
  - emits a concise operator summary on stdout
  - returns stable exit codes (0/1/2)

Exit codes:
    0  Successful run, or valid dry-run (--dry-run).
    1  CLI / config validation error.
    2  Input / runtime error (malformed candles, bridge failure, execution
       failure, reporter failure, or determinism failure with --deterministic-verify).

 Usage:
     python -m services.validation.strategy_replay_runner \\
         --dataset-source file \\
         --input-candles candles.json \\
         [--output-dir artifacts/replay_reports] \\
         [--strategy-id primary_breakout_v1] \\
         [--symbol BTCUSDT] \\
         [--adapter-id primary_breakout_runner_v1] \\
         [--speedup-profile instant|1x|2x|5x|10x] \\
         [--dry-run] \\
         [--deterministic-verify]
     python -m services.validation.strategy_replay_runner \\
         --dataset-source db \\
         --db-dataset-window START_TS_MS:END_TS_MS \\
         [--output-dir artifacts/replay_reports] \\
         [--strategy-id primary_breakout_v1] \\
         [--symbol BTCUSDT] \\
         [--adapter-id primary_breakout_runner_v1] \\
         [--speedup-profile instant|1x|2x|5x|10x] \\
         [--dry-run] \\
         [--deterministic-verify]

Governance: Issue #1804 (LR-021 Replay CLI Slice)

relations:
  role: replay_cli_entry_point
  domain: validation
  upstream:
    - services.validation.strategy_backtest_runner (run_primary_breakout_backtest)
    - services.validation.replay_reporter         (ReplayReporter, write_bundle)
    - core.replay.replay_contracts                (ReplayReportInput and related)
    - core.replay.canonical_json                  (canonical_hash)
    - core.replay.historical_bridge               (constants, HistoricalBridgeError)
  downstream:
    - CLI operator / CI pipelines
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Any

from core.replay.canonical_json import canonical_hash, canonical_json_dumps
from core.replay.dataset_provider import (
    DBBackedDatasetProvider,
    DatasetLoadError,
    DatasetResult,
    FileBackedDatasetProvider,
)
from core.replay.dataset_spec import DatasetSpec, DatasetSpecError
from core.replay.historical_bridge import (
    HistoricalBridgeError,
    PrimaryBreakoutBridgeConfig,
    PRIMARY_BREAKOUT_STRATEGY_ID,
    PRIMARY_BREAKOUT_SYMBOL,
    build_primary_breakout_historical_bridge,
)
from core.replay.replay_contracts import (
    EnvelopeSummary,
    ReplayExecutionResult,
    ReplayIntegrity,
    ReplayReportArtifactManifest,
    ReplayReportInput,
    ReplayRunSpec,
)
from core.replay.scheduler import (
    ReplayScheduler,
    SchedulerConfig,
    SchedulerError,
)
from core.replay.run_registry import (
    ReplayRunRecord,
    ReplayRunRegistry,
    RunRegistryError,
    build_operator_summary,
    build_replay_provenance_fingerprint,
    build_replay_run_id,
)
from core.replay.scenario_packs import (
    list_builtin_scenario_ids,
    run_builtin_scenario_group,
    ScenarioPackError,
)
from core.replay.scenario_harness import (
    ScenarioHarnessError,
    ScenarioRunResult,
    ScenarioSpec,
)
from core.replay.replay_report_builder import (
    build_scenario_comparison_summary,
)
from core.utils.clock import utcnow
from core.utils.postgres_client import create_postgres_connection
from services.validation.replay_reporter import ReplayReporter, ReplayReporterError
from services.validation.strategy_backtest_runner import (
    PrimaryBreakoutBacktestError,
    PrimaryBreakoutBacktestRunConfig,
    _deterministic_run_id,
    run_primary_breakout_backtest,
)

# ---------------------------------------------------------------------------
# Supported constants (fail-closed validation anchors)
# ---------------------------------------------------------------------------
_SUPPORTED_STRATEGY_IDS: frozenset[str] = frozenset({PRIMARY_BREAKOUT_STRATEGY_ID})
_SUPPORTED_SYMBOLS: frozenset[str] = frozenset({PRIMARY_BREAKOUT_SYMBOL})
_SUPPORTED_ADAPTER_IDS: frozenset[str] = frozenset({"primary_breakout_runner_v1"})

_DEFAULT_OUTPUT_DIR = "artifacts/replay_reports"
_DEFAULT_STRATEGY_ID = PRIMARY_BREAKOUT_STRATEGY_ID
_DEFAULT_SYMBOL = PRIMARY_BREAKOUT_SYMBOL
_DEFAULT_ADAPTER_ID = "primary_breakout_runner_v1"
_DEFAULT_REPLAY_MODE = "baseline"

_CODE_COMMIT_RE = re.compile(r"^[a-f0-9]{7,40}$")
_FALLBACK_CODE_COMMIT = "0000000"

# ---------------------------------------------------------------------------
# Env vars that are safe to surface in env_redacted.txt
# ---------------------------------------------------------------------------
_SAFE_ENV_KEYS: frozenset[str] = frozenset(
    {
        "HOSTNAME",
        "OS",
        "PYTHON",
        "PYTHONPATH",
        "PWD",
        "HOME",
        "USER",
        "LOGNAME",
        "LANG",
        "LC_ALL",
        "TZ",
        "LOG_LEVEL",
        "MOCK_TRADING",
        "CDB_REPLAY_STRATEGY_ID",
        "CDB_REPLAY_SYMBOL",
    }
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class ReplayRunnerError(RuntimeError):
    """Raised when the replay runner cannot proceed (maps to exit code 2)."""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ARVPReplayConfig:
    """Minimal, fail-closed config for an ARVP replay run."""

    input_candles_file: str = ""
    """Path to candle input file (JSON array or JSONL)."""

    dataset_source: str = "file"
    """Dataset input source: 'file' or 'db'."""

    db_dataset_window: str | None = None
    """DB-backed dataset window: 'START_TS_MS:END_TS_MS' (epoch millis)."""

    strategy_id: str = _DEFAULT_STRATEGY_ID
    """Strategy identifier. Must be in _SUPPORTED_STRATEGY_IDS."""

    symbol: str = _DEFAULT_SYMBOL
    """Trading symbol. Must be in _SUPPORTED_SYMBOLS."""

    adapter_id: str = _DEFAULT_ADAPTER_ID
    """Adapter identifier. Must be in _SUPPORTED_ADAPTER_IDS."""

    speedup_profile: str = "instant"
    """Deterministic replay scheduler speed profile."""

    output_directory: str = _DEFAULT_OUTPUT_DIR
    """Root output directory for replay artifact bundles."""

    order_size: float = 1.0
    """Order size passed to the execution simulator."""

    order_book_depth_multiplier: float = 10_000.0
    """Order-book depth multiplier for slippage simulation."""

    entry_lookback_minutes: int = 240
    """Bridge entry lookback window in minutes."""

    exit_lookback_minutes: int = 120
    """Bridge exit lookback window in minutes."""

    breakout_buffer: float = 0.0005
    """Breakout confirmation buffer (fraction of price)."""

    min_minutes_between_entries: int = 60
    """Minimum cooldown between entry signals."""

    gate_trace_path: Path | None = None
    """Optional path for entry gate trace JSONL."""

    dry_run: bool = False
    """Validate config + input only; do not execute or write artifacts."""

    deterministic_verify: bool = False
    """Exit with code 2 if the replay determinism check fails."""

    scenario_ids: tuple[str, ...] | None = None
    """Tuple of built-in scenario IDs to run as a group."""

    scenario_group_id: str | None = None
    """Optional explicit scenario group ID."""

    def validate(self) -> None:
        """Fail-closed config validation. Raises ValueError on any violation."""
        dataset_source = (self.dataset_source or "").strip()
        if dataset_source not in {"file", "db"}:
            raise ValueError(
                f"dataset_source must be 'file' or 'db', got {self.dataset_source!r}"
            )

        if dataset_source == "file":
            if not self.input_candles_file:
                raise ValueError(
                    "dataset_source='file' requires input_candles_file "
                    "(use --input-candles)"
                )
            if self.db_dataset_window is not None:
                raise ValueError(
                    "dataset_source='file' and dataset_source='db' are mutually exclusive: "
                    "db_dataset_window must be None when dataset_source='file'."
                )
        else:
            if self.db_dataset_window is None or not str(self.db_dataset_window).strip():
                raise ValueError(
                    "dataset_source='db' requires db_dataset_window (use --db-dataset-window)"
                )
            if self.input_candles_file:
                raise ValueError(
                    "dataset_source='db' and dataset_source='file' are mutually exclusive: "
                    "input_candles_file must be empty when dataset_source='db'."
                )

            # Fail-closed: db_dataset_window must include an explicit window.
            _parse_db_dataset_window(self.db_dataset_window)
        if self.strategy_id not in _SUPPORTED_STRATEGY_IDS:
            raise ValueError(
                f"unsupported strategy_id {self.strategy_id!r}; "
                f"supported: {sorted(_SUPPORTED_STRATEGY_IDS)}"
            )
        if self.symbol not in _SUPPORTED_SYMBOLS:
            raise ValueError(
                f"unsupported symbol {self.symbol!r}; "
                f"supported: {sorted(_SUPPORTED_SYMBOLS)}"
            )
        if self.adapter_id not in _SUPPORTED_ADAPTER_IDS:
            raise ValueError(
                f"unsupported adapter_id {self.adapter_id!r}; "
                f"supported: {sorted(_SUPPORTED_ADAPTER_IDS)}"
            )
        try:
            SchedulerConfig(profile=self.speedup_profile).validate()
        except SchedulerError as exc:
            raise ValueError(str(exc)) from exc
        if self.order_size <= 0:
            raise ValueError("order_size must be > 0")
        if self.order_book_depth_multiplier <= 0:
            raise ValueError("order_book_depth_multiplier must be > 0")
        if self.entry_lookback_minutes <= 0:
            raise ValueError("entry_lookback_minutes must be > 0")
        if self.exit_lookback_minutes <= 0:
            raise ValueError("exit_lookback_minutes must be > 0")
        if self.breakout_buffer < 0:
            raise ValueError("breakout_buffer must be >= 0")
        if self.min_minutes_between_entries < 0:
            raise ValueError("min_minutes_between_entries must be >= 0")

        if self.scenario_ids and self.gate_trace_path:
            raise ValueError(
                "--gate-trace-path is not supported with --scenario-group (multiple scenarios "
                "would overwrite the same trace file). Run scenarios individually to use tracing."
            )

        # Scenario group validation
        if self.scenario_ids is not None:
            if not self.scenario_ids:
                raise ValueError("scenario_ids must be a non-empty tuple")
            known_scenarios = set(list_builtin_scenario_ids())
            for sid in self.scenario_ids:
                if sid not in known_scenarios:
                    raise ValueError(
                        f"unknown scenario_id {sid!r}; known: {sorted(known_scenarios)}"
                    )


_DB_DATASET_WINDOW_RE = re.compile(r"^(?P<start>\d+):(?P<end>\d+)$")


def _parse_db_dataset_window(db_dataset_window: str) -> tuple[int, int]:
    """Parse ``db_dataset_window`` into an explicit (start_ts_ms, end_ts_ms) window.

    Front-door contract: for DB-backed datasets, operators must provide the
    replay window explicitly as ``START_TS_MS:END_TS_MS`` (UTC epoch millis).
    """
    raw = str(db_dataset_window).strip()
    match = _DB_DATASET_WINDOW_RE.match(raw)
    if not match:
        raise ValueError(
            "db_dataset_window must be in the form 'START_TS_MS:END_TS_MS' (epoch millis), "
            f"got {db_dataset_window!r}"
        )
    try:
        start_ts_ms = int(match.group("start"))
        end_ts_ms = int(match.group("end"))
    except ValueError as exc:
        raise ValueError(
            "db_dataset_window must contain integer START_TS_MS and END_TS_MS, "
            f"got {db_dataset_window!r}"
        ) from exc
    if start_ts_ms <= 0 or end_ts_ms <= 0:
        raise ValueError(
            f"db_dataset_window timestamps must be > 0, got {db_dataset_window!r}"
        )
    if start_ts_ms >= end_ts_ms:
        raise ValueError(
            f"db_dataset_window start must be < end, got {db_dataset_window!r}"
        )
    return start_ts_ms, end_ts_ms


# ---------------------------------------------------------------------------
# Scenario override mapping (fail-closed)
# ---------------------------------------------------------------------------
_SCENARIO_GROUP_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

# Mapping: scenario override key -> ExecutionSimulator config field
_SCNARIO_OVERRIDE_KEY_TO_SIMULATOR: dict[str, str] = {
    "execution_slippage_bps": "BASE_SLIPPAGE_BPS",
    "fill_rate": "FILL_THRESHOLD",
    "fill_depth_factor": "DEPTH_IMPACT_FACTOR",
    "execution_delay_bars": "EXECUTION_DELAY_BARS",
}

_ALLOWED_SCENARIO_OVERRIDE_KEYS: frozenset[str] = frozenset(
    {
        "pack_id",
        "pack_version",
        "execution_slippage_bps",
        "fill_rate",
        "fill_depth_factor",
        "execution_delay_bars",
        "feed_gap_bars",
        "execution_posture",
    }
)

# Overrides die fail-closed rejected werden
_UNSUPPORTED_SCENARIO_OVERRIDES: frozenset[str] = frozenset(
    {
        "feed_gap_seconds",
        "drop_ticks_on_gap",
    }
)


@dataclass(frozen=True, slots=True)
class ScenarioResolvedOverrides:
    """Internal split between execution-simulator and replay-data overrides."""

    simulator_config: dict[str, Any]
    replay_data_overrides: dict[str, Any]


def _apply_scenario_overrides(
    base_config: ARVPReplayConfig,
    overrides: dict[str, Any],
) -> ScenarioResolvedOverrides:
    """Resolve scenario overrides into execution vs replay-data surfaces."""
    # Check for unsupported overrides first
    unsupported = set(overrides.keys()) & _UNSUPPORTED_SCENARIO_OVERRIDES
    if unsupported:
        raise ReplayRunnerError(
            f"Scenario override not currently supported: {sorted(unsupported)}. "
            f"Supported overrides: {sorted(_ALLOWED_SCENARIO_OVERRIDE_KEYS)}. "
            f"`feed_gap_seconds` is not representable on the strict 1m replay canvas; "
            f"use explicit bar-level semantics instead."
        )

    # Check for unknown keys
    unknown = set(overrides.keys()) - _ALLOWED_SCENARIO_OVERRIDE_KEYS
    if unknown:
        raise ReplayRunnerError(
            f"Scenario overrides contain unknown keys: {sorted(unknown)}. "
            f"Supported overrides: {sorted(_ALLOWED_SCENARIO_OVERRIDE_KEYS)}"
        )

    # Build simulator config
    sim_config: dict[str, Any] = {}
    replay_data_overrides: dict[str, Any] = {}
    for override_key, sim_field in _SCNARIO_OVERRIDE_KEY_TO_SIMULATOR.items():
        if override_key in overrides:
            value = overrides[override_key]
            sim_config[sim_field] = value

    if "feed_gap_bars" in overrides:
        replay_data_overrides["feed_gap_bars"] = overrides["feed_gap_bars"]

    # Pass execution_posture as simulator metadata (dokumentiert, keine numerische Wirkung)
    posture = overrides.get("execution_posture")
    if posture:
        sim_config["_execution_posture"] = posture

    return ScenarioResolvedOverrides(
        simulator_config=sim_config,
        replay_data_overrides=replay_data_overrides,
    )


def _apply_replay_data_overrides(
    candles: list[dict[str, Any]],
    overrides: dict[str, Any],
    *,
    warmup_count: int,
) -> list[dict[str, Any]]:
    """Apply deterministic replay-data perturbations without breaking 1m cadence.

    ``feed_gap_bars`` is modeled as a midpoint-aligned stale-feed window across the
    live 1m bars. Gap bars repeat the last visible bar, flip freshness to false,
    and carry a marker consumed by the historical bridge.
    """
    if not overrides:
        return candles

    perturbed = [dict(candle) for candle in candles]
    feed_gap_bars = overrides.get("feed_gap_bars")
    if feed_gap_bars is None:
        return perturbed
    if isinstance(feed_gap_bars, bool) or not isinstance(feed_gap_bars, int):
        raise ReplayRunnerError("feed_gap_bars must be an integer >= 1")
    if feed_gap_bars < 1:
        raise ReplayRunnerError("feed_gap_bars must be >= 1")

    live_count = len(perturbed) - warmup_count
    if live_count <= 0:
        raise ReplayRunnerError("feed_gap_bars requires at least one live candle")
    if feed_gap_bars >= live_count:
        raise ReplayRunnerError(
            "feed_gap_bars must leave at least one unaffected live candle"
        )

    gap_start = warmup_count + (live_count - feed_gap_bars) // 2
    source_index = max(0, gap_start - 1)
    stale_source = dict(perturbed[source_index])

    for idx in range(gap_start, gap_start + feed_gap_bars):
        gap_row = dict(stale_source)
        gap_row["ts_ms"] = perturbed[idx]["ts_ms"]
        gap_row["market_state_fresh"] = False
        gap_row["regime_fresh"] = False
        gap_row["data_gap_active"] = True
        gap_row["volume"] = 0.0
        perturbed[idx] = gap_row

    return perturbed


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _get_code_commit() -> str:
    """Derive the current git commit hash. Returns '0000000' if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            commit = result.stdout.strip()
            if _CODE_COMMIT_RE.match(commit):
                return commit
    except Exception:
        pass
    return _FALLBACK_CODE_COMMIT


def _redact_env() -> dict[str, str]:
    """Return a small subset of environment variables safe to surface in logs."""
    return {k: v for k, v in os.environ.items() if k in _SAFE_ENV_KEYS}


def _utc_now_iso() -> str:
    return utcnow().replace(tzinfo=timezone.utc).isoformat()


def _build_provenance_config_snapshot(
    config: ARVPReplayConfig,
) -> dict[str, Any]:
    return {
        "order_size": config.order_size,
        "order_book_depth_multiplier": config.order_book_depth_multiplier,
        "entry_lookback_minutes": config.entry_lookback_minutes,
        "exit_lookback_minutes": config.exit_lookback_minutes,
        "breakout_buffer": config.breakout_buffer,
        "min_minutes_between_entries": config.min_minutes_between_entries,
    }


def _load_dataset_result(
    config: ARVPReplayConfig,
    *,
    warmup_count: int,
) -> DatasetResult:
    """Load + validate dataset via the canonical dataset provider layer."""
    dataset_source = (config.dataset_source or "").strip()
    if dataset_source == "file":
        input_path = Path(config.input_candles_file)
        temp_spec = DatasetSpec(
            symbol=config.symbol,
            timeframe="1m",
            start_ts_ms=0,
            end_ts_ms=0,
            warmup_candles=warmup_count,
            source="file",
            file_path=str(input_path),
        )
        try:
            temp_result = FileBackedDatasetProvider().load(temp_spec)
        except (DatasetLoadError, DatasetSpecError) as exc:
            raise ReplayRunnerError(str(exc)) from exc

        candles = list(temp_result.candles)
        try:
            start_ts_ms = int(candles[warmup_count]["ts_ms"])
            end_ts_ms = int(candles[-1]["ts_ms"])
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise ReplayRunnerError(
                "dataset requires numeric ts_ms on the first live candle and last candle"
            ) from exc

        spec = DatasetSpec(
            symbol=config.symbol,
            timeframe="1m",
            start_ts_ms=start_ts_ms,
            end_ts_ms=end_ts_ms,
            warmup_candles=warmup_count,
            source="file",
            file_path=str(input_path),
        )
        try:
            spec.validate()
        except DatasetSpecError as exc:
            raise ReplayRunnerError(f"dataset spec validation failed: {exc}") from exc

        return DatasetResult(
            spec=spec,
            candles=temp_result.candles,
            fingerprint=spec.fingerprint(),
            warmup_count=warmup_count,
            effective_candle_count=len(candles) - warmup_count,
        )

    if dataset_source == "db":
        start_ts_ms, end_ts_ms = _parse_db_dataset_window(
            str(config.db_dataset_window)
        )
        spec = DatasetSpec(
            symbol=config.symbol,
            timeframe="1m",
            start_ts_ms=start_ts_ms,
            end_ts_ms=end_ts_ms,
            warmup_candles=warmup_count,
            source="db",
            file_path=None,
            db_dataset_window=str(config.db_dataset_window),
        )
        try:
            conn = create_postgres_connection()
        except Exception as exc:
            raise ReplayRunnerError(f"failed to connect to Postgres: {exc}") from exc
        try:
            return DBBackedDatasetProvider(conn).load(spec)
        except (DatasetLoadError, DatasetSpecError) as exc:
            raise ReplayRunnerError(str(exc)) from exc
        finally:
            try:
                conn.close()
            except Exception:
                pass

    raise ReplayRunnerError(f"unsupported dataset_source: {config.dataset_source!r}")


def _build_scheduler_metadata(
    dataset_result: DatasetResult,
    *,
    speedup_profile: str,
) -> dict[str, Any]:
    """Derive deterministic scheduler metadata from a validated dataset result."""
    try:
        return (
            ReplayScheduler()
            .schedule(
                dataset_result,
                SchedulerConfig(profile=speedup_profile),
            )
            .to_dict()
        )
    except (TypeError, ValueError) as exc:
        raise ReplayRunnerError(f"scheduler validation failed: {exc}") from exc


def _build_execution_provenance_id(
    candles: list[dict[str, Any]],
    *,
    run_config: PrimaryBreakoutBacktestRunConfig,
    code_commit: str,
) -> str:
    """Precompute the deterministic backtest provenance id for the runner record."""
    try:
        bridge_requests = build_primary_breakout_historical_bridge(
            candles, config=run_config.bridge
        )
        return _deterministic_run_id(bridge_requests, run_config, code_commit)
    except Exception as exc:
        raise ReplayRunnerError(
            f"failed to derive execution provenance id: {exc}"
        ) from exc


def _write_operator_summary_artifact(
    bundle_dir: Path,
    record: ReplayRunRecord,
) -> None:
    summary_path = bundle_dir / "operator_summary.json"
    summary_path.write_text(
        canonical_json_dumps(build_operator_summary(record)),
        encoding="utf-8",
    )


def _append_failed_record(
    registry: ReplayRunRegistry,
    *,
    run_id: str,
    strategy_id: str,
    symbol: str,
    dataset_fingerprint: str,
    scheduler_profile: str,
    execution_provenance_id: str,
    artifact_root: str,
    deterministic_replay_ok: bool,
    started_at_utc: str,
    failure_reason: str,
    gate_status: str | None = None,
) -> ReplayRunRecord:
    record = ReplayRunRecord(
        run_id=run_id,
        status="failed",
        mode=_DEFAULT_REPLAY_MODE,
        strategy_id=strategy_id,
        symbol=symbol,
        dataset_fingerprint=dataset_fingerprint,
        scheduler_profile=scheduler_profile,
        execution_provenance_id=execution_provenance_id,
        artifact_root=artifact_root,
        gate_status=gate_status,
        deterministic_replay_ok=deterministic_replay_ok,
        failure_reason=failure_reason,
        started_at_utc=started_at_utc,
        finished_at_utc=_utc_now_iso(),
    )
    registry.append(record)
    return record


def _build_replay_report_input(
    backtest_report: dict[str, Any],
    config: ARVPReplayConfig,
    code_commit: str,
    output_dir: Path,
    scheduler_metadata: dict[str, Any] | None = None,
    *,
    runner_run_id: str | None = None,
    execution_provenance_id: str | None = None,
    dataset_fingerprint: str | None = None,
) -> ReplayReportInput:
    """Bridge a backtest runner report to a ReplayReportInput.

    This function is the only place that translates between the
    strategy_validation_report.v1 shape (from the backtest runner) and the
    replay_report.v1 contract (from #1806 / replay_contracts.py).

    No metrics are recalculated; all values are derived from the backtest report.
    """
    execution_run_id: str = (
        execution_provenance_id or backtest_report["run_metadata"]["run_id"]
    )
    run_id: str = runner_run_id or execution_run_id
    dataset: dict[str, Any] = dict(backtest_report["dataset_summary"])
    if dataset_fingerprint is not None:
        dataset["dataset_fingerprint"] = dataset_fingerprint
    if scheduler_metadata is not None:
        dataset["scheduler"] = dict(scheduler_metadata)
    metrics: dict[str, Any] = backtest_report["metrics"]
    run_spec_metadata: dict[str, Any] = {
        "mode": _DEFAULT_REPLAY_MODE,
        "execution_provenance_id": execution_run_id,
        "scheduler_profile": config.speedup_profile,
    }
    if dataset_fingerprint is not None:
        run_spec_metadata["dataset_fingerprint"] = dataset_fingerprint

    run_spec = ReplayRunSpec(
        replay_run_id=run_id,
        strategy_id=config.strategy_id,
        symbol=config.symbol,
        start_ts_ms=int(dataset["period_start_ts_ms"]),
        end_ts_ms=int(dataset["period_end_ts_ms"]),
        code_commit=code_commit,
        run_mode="shadow",
        metadata=run_spec_metadata,
    )

    exec_result = ReplayExecutionResult(
        run_id=run_id,
        events_processed=int(dataset.get("candles_total", 0)),
        decisions_made=int(metrics.get("signals_total", 0)),
        orders_placed=int(metrics.get("buy_signals_total", 0))
        + int(metrics.get("sell_signals_total", 0)),
        fills_recorded=int(metrics.get("closed_trades_total", 0)),
        # Shadow replay does not emit an envelope chain — empty list is correct.
        envelope_hashes=[],
    )

    determinism_ok = bool(metrics.get("deterministic_replay_ok", False))
    # Deterministic empty-chain hash: canonical_hash([]) is stable across runs.
    empty_chain_hash = canonical_hash([])

    integrity = ReplayIntegrity(
        run_id=run_id,
        envelope_count=0,
        envelope_chain_hash=empty_chain_hash,
        event_loop_states_hash=empty_chain_hash,
        integrity_ok=determinism_ok,
        failed_checks=(
            () if determinism_ok else ("deterministic_replay_check_failed",)
        ),
    )

    envelope_summary = EnvelopeSummary(
        decision_envelopes_total=0,
        order_envelopes_total=0,
        fill_envelopes_total=0,
    )

    bundle_dir = output_dir / run_id
    artifact_manifest = ReplayReportArtifactManifest(
        envelope_log_uri="none",
        event_loop_states_uri="none",
        report_artifact_uri=str(bundle_dir / "report.json"),
        supplementary_artifacts={
            "config_resolved_uri": str(bundle_dir / "config.resolved.json"),
            "env_redacted_uri": str(bundle_dir / "env_redacted.txt"),
            "operator_summary_uri": str(bundle_dir / "operator_summary.json"),
        },
    )

    return ReplayReportInput(
        schema_version="replay_report.v1",
        report_type="shadow_replay",
        strategy_id=config.strategy_id,
        run_spec=run_spec,
        execution_result=exec_result,
        replay_integrity=integrity,
        envelope_summary=envelope_summary,
        artifact_manifest=artifact_manifest,
        config_snapshot=backtest_report.get("config_snapshot"),
        dataset_summary=dataset,
        metrics=metrics,
        thresholds_applied=backtest_report.get("thresholds_applied"),
        # gate_result already computed by the backtest runner; reporter will skip evaluation.
        gate_result=backtest_report.get("gate_result"),
    )


def _write_supplementary_artifacts(
    bundle_dir: Path,
    config: ARVPReplayConfig,
    code_commit: str,
) -> None:
    """Write config.resolved.json and env_redacted.txt into the bundle directory.

    These are supplementary artifacts beyond the core reporter bundle
    (report.json, manifest.json, audit.log). They are written by the CLI layer
    and are not part of the deterministic report hash.

    Raises:
        OSError if either file cannot be written.
    """
    resolved_config: dict[str, Any] = {
        "dataset_source": config.dataset_source,
        "input_candles_file": config.input_candles_file,
        "db_dataset_window": config.db_dataset_window,
        "strategy_id": config.strategy_id,
        "symbol": config.symbol,
        "adapter_id": config.adapter_id,
        "speedup_profile": config.speedup_profile,
        "output_directory": config.output_directory,
        "order_size": config.order_size,
        "order_book_depth_multiplier": config.order_book_depth_multiplier,
        "entry_lookback_minutes": config.entry_lookback_minutes,
        "exit_lookback_minutes": config.exit_lookback_minutes,
        "breakout_buffer": config.breakout_buffer,
        "min_minutes_between_entries": config.min_minutes_between_entries,
        "code_commit": code_commit,
        "dry_run": config.dry_run,
        "deterministic_verify": config.deterministic_verify,
    }
    config_path = bundle_dir / "config.resolved.json"
    config_path.write_text(
        json.dumps(resolved_config, indent=2, sort_keys=True), encoding="utf-8"
    )

    env_lines = [f"{k}={v}" for k, v in sorted(_redact_env().items())]
    env_path = bundle_dir / "env_redacted.txt"
    env_path.write_text("\n".join(env_lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def run_arvp_replay(config: ARVPReplayConfig) -> int:
    """Orchestrate a full ARVP replay run (baseline or scenario group).

    Args:
        config: Validated ARVPReplayConfig instance.

    Returns:
        Exit code integer: 0 success, 1 config error, 2 runtime/input error.
    """
    run_cfg = PrimaryBreakoutBacktestRunConfig(
        bridge=PrimaryBreakoutBridgeConfig(
            entry_lookback_minutes=config.entry_lookback_minutes,
            exit_lookback_minutes=config.exit_lookback_minutes,
            breakout_buffer=config.breakout_buffer,
            min_minutes_between_entries=config.min_minutes_between_entries,
        ),
        order_size=config.order_size,
        order_book_depth_multiplier=config.order_book_depth_multiplier,
    )
    warmup_count = max(
        run_cfg.bridge.entry_lookback_minutes,
        run_cfg.bridge.exit_lookback_minutes,
    )

    # Scenario group path
    if config.scenario_ids:
        return _run_scenario_group_path_with_candles(config, warmup_count=warmup_count)

    try:
        dataset_result = _load_dataset_result(config, warmup_count=warmup_count)
    except ReplayRunnerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    candles: list[dict[str, Any]] = [dict(candle) for candle in dataset_result.candles]

    if config.dry_run:
        print(
            "DRY-RUN: config valid, dataset loaded. "
            f"source={config.dataset_source!r}, candles_total={len(candles)}."
        )
        return 0

    output_dir = Path(config.output_directory)
    code_commit = _get_code_commit()
    try:
        scheduler_metadata = _build_scheduler_metadata(
            dataset_result,
            speedup_profile=config.speedup_profile,
        )
        execution_provenance_id = _build_execution_provenance_id(
            candles,
            run_config=run_cfg,
            code_commit=code_commit,
        )
        provenance_fingerprint = build_replay_provenance_fingerprint(
            strategy_id=config.strategy_id,
            symbol=config.symbol,
            adapter_id=config.adapter_id,
            dataset_fingerprint=dataset_result.fingerprint,
            scheduler_profile=config.speedup_profile,
            execution_provenance_id=execution_provenance_id,
            code_commit=code_commit,
            mode=_DEFAULT_REPLAY_MODE,
            config_snapshot=_build_provenance_config_snapshot(config),
        )
        registry = ReplayRunRegistry(output_dir / "run_registry.jsonl")
        run_id = build_replay_run_id(
            provenance_fingerprint,
            registry.next_attempt(provenance_fingerprint),
        )
    except (ReplayRunnerError, RunRegistryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    started_at_utc = _utc_now_iso()
    artifact_root = str(output_dir / run_id)
    try:
        registry.append(
            ReplayRunRecord(
                run_id=run_id,
                status="running",
                mode=_DEFAULT_REPLAY_MODE,
                strategy_id=config.strategy_id,
                symbol=config.symbol,
                dataset_fingerprint=dataset_result.fingerprint,
                scheduler_profile=config.speedup_profile,
                execution_provenance_id=execution_provenance_id,
                artifact_root=artifact_root,
                deterministic_replay_ok=False,
                started_at_utc=started_at_utc,
            )
        )
    except RunRegistryError as exc:
        print(f"ERROR: Failed to write running run record: {exc}", file=sys.stderr)
        return 2

    # Delegate to the existing backtest surface (business logic lives here)
    try:
        backtest_report = run_primary_breakout_backtest(
            candles,
            run_config=run_cfg,
            code_commit=code_commit,
            gate_trace_path=config.gate_trace_path,
        )
    except (HistoricalBridgeError, PrimaryBreakoutBacktestError) as exc:
        try:
            _append_failed_record(
                registry,
                run_id=run_id,
                strategy_id=config.strategy_id,
                symbol=config.symbol,
                dataset_fingerprint=dataset_result.fingerprint,
                scheduler_profile=config.speedup_profile,
                execution_provenance_id=execution_provenance_id,
                artifact_root=artifact_root,
                deterministic_replay_ok=False,
                started_at_utc=started_at_utc,
                failure_reason=f"Replay execution failed: {exc}",
            )
        except RunRegistryError as registry_exc:
            print(
                f"ERROR: Failed to write failed run record: {registry_exc}",
                file=sys.stderr,
            )
        print(f"ERROR: Replay execution failed: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        try:
            _append_failed_record(
                registry,
                run_id=run_id,
                strategy_id=config.strategy_id,
                symbol=config.symbol,
                dataset_fingerprint=dataset_result.fingerprint,
                scheduler_profile=config.speedup_profile,
                execution_provenance_id=execution_provenance_id,
                artifact_root=artifact_root,
                deterministic_replay_ok=False,
                started_at_utc=started_at_utc,
                failure_reason=f"Unexpected runtime failure: {exc}",
            )
        except RunRegistryError as registry_exc:
            print(
                f"ERROR: Failed to write failed run record: {registry_exc}",
                file=sys.stderr,
            )
        print(f"ERROR: Unexpected runtime failure: {exc}", file=sys.stderr)
        return 2

    # Bridge backtest report → replay contract shape
    try:
        report_input = _build_replay_report_input(
            backtest_report,
            config,
            code_commit,
            output_dir,
            scheduler_metadata=scheduler_metadata,
            runner_run_id=run_id,
            execution_provenance_id=execution_provenance_id,
            dataset_fingerprint=dataset_result.fingerprint,
        )
    except Exception as exc:
        try:
            _append_failed_record(
                registry,
                run_id=run_id,
                strategy_id=config.strategy_id,
                symbol=config.symbol,
                dataset_fingerprint=dataset_result.fingerprint,
                scheduler_profile=config.speedup_profile,
                execution_provenance_id=execution_provenance_id,
                artifact_root=artifact_root,
                deterministic_replay_ok=False,
                started_at_utc=started_at_utc,
                failure_reason=f"Failed to build replay report input: {exc}",
            )
        except RunRegistryError as registry_exc:
            print(
                f"ERROR: Failed to write failed run record: {registry_exc}",
                file=sys.stderr,
            )
        print(f"ERROR: Failed to build replay report input: {exc}", file=sys.stderr)
        return 2

    # Write artifact bundle via reporter (#1805 surface)
    reporter = ReplayReporter()
    try:
        bundle_dir = reporter.write_bundle(report_input, output_dir)
    except ReplayReporterError as exc:
        try:
            _append_failed_record(
                registry,
                run_id=run_id,
                strategy_id=config.strategy_id,
                symbol=config.symbol,
                dataset_fingerprint=dataset_result.fingerprint,
                scheduler_profile=config.speedup_profile,
                execution_provenance_id=execution_provenance_id,
                artifact_root=artifact_root,
                deterministic_replay_ok=False,
                started_at_utc=started_at_utc,
                failure_reason=f"Replay reporter failed: {exc}",
            )
        except RunRegistryError as registry_exc:
            print(
                f"ERROR: Failed to write failed run record: {registry_exc}",
                file=sys.stderr,
            )
        print(f"ERROR: Replay reporter failed: {exc}", file=sys.stderr)
        return 2

    # Write supplementary artifacts (CLI layer, not part of canonical hash)
    artifact_root = str(bundle_dir)
    try:
        _write_supplementary_artifacts(bundle_dir, config, code_commit)
    except OSError as exc:
        try:
            _append_failed_record(
                registry,
                run_id=run_id,
                strategy_id=config.strategy_id,
                symbol=config.symbol,
                dataset_fingerprint=dataset_result.fingerprint,
                scheduler_profile=config.speedup_profile,
                execution_provenance_id=execution_provenance_id,
                artifact_root=artifact_root,
                deterministic_replay_ok=False,
                started_at_utc=started_at_utc,
                failure_reason=f"Failed to write supplementary artifacts: {exc}",
            )
        except RunRegistryError as registry_exc:
            print(
                f"ERROR: Failed to write failed run record: {registry_exc}",
                file=sys.stderr,
            )
        print(f"ERROR: Failed to write supplementary artifacts: {exc}", file=sys.stderr)
        return 2

    # Determinism check
    metrics = backtest_report.get("metrics", {})
    deterministic_replay_ok = bool(metrics.get("deterministic_replay_ok", False))
    gate_status = (backtest_report.get("gate_result") or {}).get("status")

    if not deterministic_replay_ok:
        print(
            "WARNING: deterministic_replay_ok=False — two-pass check produced "
            "inconsistent outputs.",
            file=sys.stderr,
        )
        if config.deterministic_verify:
            failed_record: ReplayRunRecord | None = None
            try:
                failed_record = _append_failed_record(
                    registry,
                    run_id=run_id,
                    strategy_id=config.strategy_id,
                    symbol=config.symbol,
                    dataset_fingerprint=dataset_result.fingerprint,
                    scheduler_profile=config.speedup_profile,
                    execution_provenance_id=execution_provenance_id,
                    artifact_root=artifact_root,
                    gate_status=gate_status,
                    deterministic_replay_ok=False,
                    started_at_utc=started_at_utc,
                    failure_reason=(
                        "--deterministic-verify set and deterministic_replay_ok=False"
                    ),
                )
            except RunRegistryError as registry_exc:
                print(
                    f"ERROR: Failed to write failed run record: {registry_exc}",
                    file=sys.stderr,
                )
            if failed_record is not None:
                try:
                    _write_operator_summary_artifact(bundle_dir, failed_record)
                except OSError as exc:
                    print(
                        f"ERROR: Failed to write operator summary: {exc}",
                        file=sys.stderr,
                    )
            print(
                "ERROR: --deterministic-verify is set; aborting with exit code 2.",
                file=sys.stderr,
            )
            return 2

    completed_record = ReplayRunRecord(
        run_id=run_id,
        status="completed",
        mode=_DEFAULT_REPLAY_MODE,
        strategy_id=config.strategy_id,
        symbol=config.symbol,
        dataset_fingerprint=dataset_result.fingerprint,
        scheduler_profile=config.speedup_profile,
        execution_provenance_id=execution_provenance_id,
        artifact_root=artifact_root,
        gate_status=gate_status,
        deterministic_replay_ok=deterministic_replay_ok,
        started_at_utc=started_at_utc,
        finished_at_utc=_utc_now_iso(),
    )
    try:
        registry.append(completed_record)
    except RunRegistryError as exc:
        print(f"ERROR: Failed to write completed run record: {exc}", file=sys.stderr)
        return 2

    try:
        _write_operator_summary_artifact(bundle_dir, completed_record)
    except OSError as exc:
        try:
            _append_failed_record(
                registry,
                run_id=run_id,
                strategy_id=config.strategy_id,
                symbol=config.symbol,
                dataset_fingerprint=dataset_result.fingerprint,
                scheduler_profile=config.speedup_profile,
                execution_provenance_id=execution_provenance_id,
                artifact_root=artifact_root,
                gate_status=gate_status,
                deterministic_replay_ok=deterministic_replay_ok,
                started_at_utc=started_at_utc,
                failure_reason=f"Failed to write operator summary: {exc}",
            )
        except RunRegistryError as registry_exc:
            print(
                f"ERROR: Failed to write failed run record: {registry_exc}",
                file=sys.stderr,
            )
        print(f"ERROR: Failed to write operator summary: {exc}", file=sys.stderr)
        return 2

    print(f"Shadow replay complete: run_id={run_id}")
    print("  status=completed")
    print(f"  mode={_DEFAULT_REPLAY_MODE}")
    print(f"  execution_provenance_id={execution_provenance_id}")
    print(f"  dataset_fingerprint={dataset_result.fingerprint}")
    print(f"  scheduler_profile={config.speedup_profile}")
    print(f"  gate_result={gate_status or 'UNKNOWN'}")
    print(f"  deterministic_replay_ok={deterministic_replay_ok}")
    print(f"  bundle_dir={bundle_dir}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="strategy_replay_runner",
        description="ARVP replay CLI for primary_breakout_v1.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exit codes:\n"
            "  0  Success / valid dry-run\n"
            "  1  CLI / config validation error\n"
            "  2  Input / runtime error\n"
        ),
    )
    parser.add_argument(
        "--dataset-source",
        default="file",
        choices=("file", "db"),
        metavar="SOURCE",
        help="Dataset input source. Default: 'file'.",
    )
    parser.add_argument(
        "--input-candles",
        default="",
        metavar="FILE",
        help="Path to candle input file (JSON array or JSONL). Required when --dataset-source=file.",
    )
    parser.add_argument(
        "--db-dataset-window",
        default=None,
        metavar="START_TS_MS:END_TS_MS",
        help="DB-backed dataset window (epoch millis). Required when --dataset-source=db.",
    )
    parser.add_argument(
        "--output-dir",
        default=_DEFAULT_OUTPUT_DIR,
        metavar="DIR",
        help=f"Root output directory for replay artifact bundles. Default: {_DEFAULT_OUTPUT_DIR!r}",
    )
    parser.add_argument(
        "--strategy-id",
        default=_DEFAULT_STRATEGY_ID,
        metavar="ID",
        help=f"Strategy identifier. Default: {_DEFAULT_STRATEGY_ID!r}",
    )
    parser.add_argument(
        "--symbol",
        default=_DEFAULT_SYMBOL,
        metavar="SYMBOL",
        help=f"Trading symbol. Default: {_DEFAULT_SYMBOL!r}",
    )
    parser.add_argument(
        "--adapter-id",
        default=_DEFAULT_ADAPTER_ID,
        metavar="ID",
        help=f"Adapter identifier. Default: {_DEFAULT_ADAPTER_ID!r}",
    )
    parser.add_argument(
        "--gate-trace-path",
        default=None,
        metavar="PATH",
        type=Path,
        help="Optional path for entry gate trace JSONL.",
    )
    parser.add_argument(
        "--speedup-profile",
        default="instant",
        metavar="PROFILE",
        help="Deterministic scheduler speed profile. Default: 'instant'.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Validate config and input file only; do not execute or write artifacts.",
    )
    parser.add_argument(
        "--deterministic-verify",
        action="store_true",
        default=False,
        help="Exit with code 2 if the replay determinism check fails.",
    )
    parser.add_argument(
        "--scenario-group",
        default=None,
        metavar="ID,ID,...",
        help="Comma-separated built-in scenario IDs (baseline,pessimistic_execution,...)",
    )
    parser.add_argument(
        "--scenario-group-id",
        default=None,
        metavar="ID",
        help="Optional explicit scenario group ID",
    )
    return parser


def _run_scenario_group_path_with_candles(
    config: ARVPReplayConfig,
    *,
    warmup_count: int,
) -> int:
    try:
        dataset_result = _load_dataset_result(config, warmup_count=warmup_count)
    except ReplayRunnerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    candles: list[dict[str, Any]] = [dict(candle) for candle in dataset_result.candles]

    if config.dry_run:
        print(
            "DRY-RUN: scenario group valid, dataset loaded. "
            f"source={config.dataset_source!r}, candles_total={len(candles)}."
        )
        return 0

    return _run_scenario_group_path(config, candles)


def _run_scenario_group_path(
    config: ARVPReplayConfig,
    candles: list[dict[str, Any]],
) -> int:
    """Run scenario group via harness."""
    output_dir = Path(config.output_directory)
    code_commit = _get_code_commit()

    def run_single(spec: ScenarioSpec) -> ScenarioRunResult:
        try:
            run_cfg = PrimaryBreakoutBacktestRunConfig(
                bridge=PrimaryBreakoutBridgeConfig(
                    entry_lookback_minutes=config.entry_lookback_minutes,
                    exit_lookback_minutes=config.exit_lookback_minutes,
                    breakout_buffer=config.breakout_buffer,
                    min_minutes_between_entries=config.min_minutes_between_entries,
                ),
                order_size=config.order_size,
                order_book_depth_multiplier=config.order_book_depth_multiplier,
            )
            warmup_count = max(
                run_cfg.bridge.entry_lookback_minutes,
                run_cfg.bridge.exit_lookback_minutes,
            )
            resolved_overrides = _apply_scenario_overrides(config, spec.config_overrides)
            scenario_candles = _apply_replay_data_overrides(
                candles,
                resolved_overrides.replay_data_overrides,
                warmup_count=warmup_count,
            )

            backtest_report = run_primary_breakout_backtest(
                scenario_candles,
                run_config=run_cfg,
                simulator_config=resolved_overrides.simulator_config,
                code_commit=code_commit,
            )

            run_id = backtest_report["run_metadata"]["run_id"]
            return ScenarioRunResult(
                scenario_id=spec.scenario_id,
                exit_code=0,
                run_id=run_id,
            )
        except ReplayRunnerError as exc:
            return ScenarioRunResult(
                scenario_id=spec.scenario_id,
                exit_code=2,
                failure_reason=str(exc),
            )
        except Exception as exc:
            return ScenarioRunResult(
                scenario_id=spec.scenario_id,
                exit_code=2,
                failure_reason=str(exc),
            )

    try:
        manifest = run_builtin_scenario_group(
            config.scenario_ids,
            run_fn=run_single,
            output_dir=output_dir,
            group_id=config.scenario_group_id,
        )
    except (ScenarioHarnessError, ScenarioPackError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    summary = build_scenario_comparison_summary(manifest)
    summary_path = Path(manifest.artifact_root) / "scenario_comparison_summary.md"
    summary_path.write_text(summary, encoding="utf-8")

    return 0 if manifest.failed_count == 0 else 2


def main() -> int:
    """Parse CLI args, build config, validate, and run. Returns exit code."""
    parser = _build_argument_parser()
    args = parser.parse_args()

    scenario_ids = None
    if args.scenario_group:
        scenario_ids = tuple(
            part.strip() for part in args.scenario_group.split(",") if part.strip()
        )

    try:
        config = ARVPReplayConfig(
            input_candles_file=args.input_candles,
            dataset_source=args.dataset_source,
            db_dataset_window=args.db_dataset_window,
            strategy_id=args.strategy_id,
            symbol=args.symbol,
            adapter_id=args.adapter_id,
            speedup_profile=args.speedup_profile,
            output_directory=args.output_dir,
            gate_trace_path=args.gate_trace_path,
            dry_run=args.dry_run,
            deterministic_verify=args.deterministic_verify,
            scenario_ids=scenario_ids,
            scenario_group_id=args.scenario_group_id,
        )
        config.validate()
    except ValueError as exc:
        print(f"ERROR: Config validation failed: {exc}", file=sys.stderr)
        return 1

    return run_arvp_replay(config)


if __name__ == "__main__":
    raise SystemExit(main())
