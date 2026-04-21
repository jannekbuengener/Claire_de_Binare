"""Accelerated shadow replay CLI entry point for primary_breakout_v1.

Thin operator-facing CLI that:
  - validates a minimal replay config fail-closed
  - loads historical candle input from file (JSON array or JSONL)
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
        --input-candles candles.json \\
        [--output-dir artifacts/replay_reports] \\
        [--strategy-id primary_breakout_v1] \\
        [--symbol BTCUSDT] \\
        [--adapter-id primary_breakout_runner_v1] \\
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
from pathlib import Path
from typing import Any

from core.replay.canonical_json import canonical_hash
from core.replay.historical_bridge import (
    HistoricalBridgeError,
    PrimaryBreakoutBridgeConfig,
    PRIMARY_BREAKOUT_STRATEGY_ID,
    PRIMARY_BREAKOUT_SYMBOL,
)
from core.replay.replay_contracts import (
    EnvelopeSummary,
    ReplayExecutionResult,
    ReplayIntegrity,
    ReplayReportArtifactManifest,
    ReplayReportInput,
    ReplayRunSpec,
)
from services.validation.replay_reporter import ReplayReporter, ReplayReporterError
from services.validation.strategy_backtest_runner import (
    PrimaryBreakoutBacktestError,
    PrimaryBreakoutBacktestRunConfig,
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
class AcceleratedShadowReplayConfig:
    """Minimal, fail-closed config for an accelerated shadow replay run."""

    input_candles_file: str
    """Path to candle input file (JSON array or JSONL).  Required."""

    strategy_id: str = _DEFAULT_STRATEGY_ID
    """Strategy identifier. Must be in _SUPPORTED_STRATEGY_IDS."""

    symbol: str = _DEFAULT_SYMBOL
    """Trading symbol. Must be in _SUPPORTED_SYMBOLS."""

    adapter_id: str = _DEFAULT_ADAPTER_ID
    """Adapter identifier. Must be in _SUPPORTED_ADAPTER_IDS."""

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

    dry_run: bool = False
    """Validate config + input only; do not execute or write artifacts."""

    deterministic_verify: bool = False
    """Exit with code 2 if the replay determinism check fails."""

    def validate(self) -> None:
        """Fail-closed config validation. Raises ValueError on any violation."""
        if not self.input_candles_file:
            raise ValueError("input_candles_file is required")
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


def _load_candles(path: Path) -> list[dict[str, Any]]:
    """Load candles from a JSON array or JSONL file. Raises ReplayRunnerError on failure."""
    if not path.exists():
        raise ReplayRunnerError(f"input candles file not found: {path}")
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ReplayRunnerError(f"cannot read candles file: {exc}") from exc

    if not text:
        raise ReplayRunnerError("input candles file is empty")

    # JSON array
    if text.startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ReplayRunnerError(f"candles JSON parse error: {exc}") from exc
        if not isinstance(data, list):
            raise ReplayRunnerError("candles JSON root must be an array")
        if not data:
            raise ReplayRunnerError("candles array is empty")
        return data

    # JSONL (one JSON object per line)
    rows: list[dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReplayRunnerError(f"JSONL parse error at line {i}: {exc}") from exc
        if not isinstance(row, dict):
            raise ReplayRunnerError(f"JSONL line {i} must be a JSON object")
        rows.append(row)

    if not rows:
        raise ReplayRunnerError("candles file contains no valid rows")
    return rows


def _redact_env() -> dict[str, str]:
    """Return a small subset of environment variables safe to surface in logs."""
    return {k: v for k, v in os.environ.items() if k in _SAFE_ENV_KEYS}


def _build_replay_report_input(
    backtest_report: dict[str, Any],
    config: AcceleratedShadowReplayConfig,
    code_commit: str,
    output_dir: Path,
) -> ReplayReportInput:
    """Bridge a backtest runner report to a ReplayReportInput.

    This function is the only place that translates between the
    strategy_validation_report.v1 shape (from the backtest runner) and the
    replay_report.v1 contract (from #1806 / replay_contracts.py).

    No metrics are recalculated; all values are derived from the backtest report.
    """
    run_id: str = backtest_report["run_metadata"]["run_id"]
    dataset: dict[str, Any] = backtest_report["dataset_summary"]
    metrics: dict[str, Any] = backtest_report["metrics"]

    run_spec = ReplayRunSpec(
        replay_run_id=run_id,
        strategy_id=config.strategy_id,
        symbol=config.symbol,
        start_ts_ms=int(dataset["period_start_ts_ms"]),
        end_ts_ms=int(dataset["period_end_ts_ms"]),
        code_commit=code_commit,
        run_mode="shadow",
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
            ()
            if determinism_ok
            else ("deterministic_replay_check_failed",)
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
        dataset_summary=backtest_report.get("dataset_summary"),
        metrics=metrics,
        thresholds_applied=backtest_report.get("thresholds_applied"),
        # gate_result already computed by the backtest runner; reporter will skip evaluation.
        gate_result=backtest_report.get("gate_result"),
    )


def _write_supplementary_artifacts(
    bundle_dir: Path,
    config: AcceleratedShadowReplayConfig,
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
        "strategy_id": config.strategy_id,
        "symbol": config.symbol,
        "adapter_id": config.adapter_id,
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
def run_accelerated_shadow_replay(config: AcceleratedShadowReplayConfig) -> int:
    """Orchestrate a full accelerated shadow replay run.

    Args:
        config: Validated AcceleratedShadowReplayConfig instance.

    Returns:
        Exit code integer: 0 success, 1 config error, 2 runtime/input error.
    """
    input_path = Path(config.input_candles_file)

    # Load + validate candles (also covers dry-run path)
    try:
        candles = _load_candles(input_path)
    except ReplayRunnerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if config.dry_run:
        print(
            f"DRY-RUN: config valid, input file accessible. {len(candles)} candles found."
        )
        return 0

    output_dir = Path(config.output_directory)
    code_commit = _get_code_commit()

    # Delegate to the existing backtest surface (business logic lives here)
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
        backtest_report = run_primary_breakout_backtest(
            candles,
            run_config=run_cfg,
            code_commit=code_commit,
        )
    except (HistoricalBridgeError, PrimaryBreakoutBacktestError) as exc:
        print(f"ERROR: Replay execution failed: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: Unexpected runtime failure: {exc}", file=sys.stderr)
        return 2

    # Bridge backtest report → replay contract shape
    try:
        report_input = _build_replay_report_input(
            backtest_report, config, code_commit, output_dir
        )
    except Exception as exc:
        print(f"ERROR: Failed to build replay report input: {exc}", file=sys.stderr)
        return 2

    # Write artifact bundle via reporter (#1805 surface)
    reporter = ReplayReporter()
    try:
        bundle_dir = reporter.write_bundle(report_input, output_dir)
    except ReplayReporterError as exc:
        print(f"ERROR: Replay reporter failed: {exc}", file=sys.stderr)
        return 2

    # Write supplementary artifacts (CLI layer, not part of canonical hash)
    try:
        _write_supplementary_artifacts(bundle_dir, config, code_commit)
    except OSError as exc:
        print(f"ERROR: Failed to write supplementary artifacts: {exc}", file=sys.stderr)
        return 2

    # Determinism check
    metrics = backtest_report.get("metrics", {})
    deterministic_replay_ok = bool(metrics.get("deterministic_replay_ok", False))
    gate_status = (backtest_report.get("gate_result") or {}).get("status", "UNKNOWN")
    run_id = report_input.run_spec.replay_run_id

    if not deterministic_replay_ok:
        print(
            "WARNING: deterministic_replay_ok=False — two-pass check produced "
            "inconsistent outputs.",
            file=sys.stderr,
        )
        if config.deterministic_verify:
            print(
                "ERROR: --deterministic-verify is set; aborting with exit code 2.",
                file=sys.stderr,
            )
            return 2

    print(f"Shadow replay complete: run_id={run_id}")
    print(f"  gate_result={gate_status}")
    print(f"  deterministic_replay_ok={deterministic_replay_ok}")
    print(f"  bundle_dir={bundle_dir}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="strategy_replay_runner",
        description="Accelerated shadow replay CLI for primary_breakout_v1.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exit codes:\n"
            "  0  Success / valid dry-run\n"
            "  1  CLI / config validation error\n"
            "  2  Input / runtime error\n"
        ),
    )
    parser.add_argument(
        "--input-candles",
        required=True,
        metavar="FILE",
        help="Path to candle input file (JSON array or JSONL). Required.",
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
    return parser


def main() -> int:
    """Parse CLI args, build config, validate, and run. Returns exit code."""
    parser = _build_argument_parser()
    args = parser.parse_args()

    try:
        config = AcceleratedShadowReplayConfig(
            input_candles_file=args.input_candles,
            strategy_id=args.strategy_id,
            symbol=args.symbol,
            adapter_id=args.adapter_id,
            output_directory=args.output_dir,
            dry_run=args.dry_run,
            deterministic_verify=args.deterministic_verify,
        )
        config.validate()
    except ValueError as exc:
        print(f"ERROR: Config validation failed: {exc}", file=sys.stderr)
        return 1

    return run_accelerated_shadow_replay(config)


if __name__ == "__main__":
    raise SystemExit(main())
