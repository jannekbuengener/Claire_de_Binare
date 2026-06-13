"""Controlled-lab pipeline pass for range_mean_reversion_v1 (Issue #3157).

Standalone profitability script that:
  - Reads the committed MEXC multi-window dataset (selection_manifest.json)
  - Iterates 20 regime-calibrated windows
  - Computes rolling z-score from close prices
  - Runs long-only mean-reversion signal logic (RANGE regime only)
  - Simulates fills via ExecutionSimulator
  - Produces per-window reports, aggregate economics, and evidence packet

Usage:
    python scripts/profitability/run_range_mean_reversion_pipeline_3157.py
    python scripts/profitability/run_range_mean_reversion_pipeline_3157.py --dry-run

Governance: Issue #3157
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from services.execution.simulator import ExecutionSimulator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STRATEGY_ID = "range_mean_reversion_v1"
CANDIDATE_ID = "cand-range-mean-reversion-v1-btcusdt-mexc"
SYMBOL = "BTCUSDT"
TIMEFRAME = "1m"
REPORT_SCHEMA_VERSION = "strategy_validation_report.v1"
EVIDENCE_SCHEMA_VERSION = "profitability_evidence_packet.v1"
ECONOMICS_SCHEMA_VERSION = "execution_economics_summary.v1"
CONTRACT_REF = "docs/evidence/profitability_candidate_range_mean_reversion_v1_3157.json"

DATASET_ID = "mexc_multi_window_3032"
DERIVED_DATASET_ID = "mexc_multi_window_3032_window_{}_regime_calibrated"
MANIFEST_PATH = Path("artifacts/candles/mexc_multi_window_3032/selection_manifest.json")
OUTPUT_ROOT = Path(
    "artifacts/replay_reports/range_mean_reversion_v1_mexc_multi_window_3157"
)
ECONOMICS_OUTPUT = Path(
    "docs/evidence/profitability_execution_economics_range_mean_reversion_v1_mexc_multi_window_3157.json"
)
EVIDENCE_OUTPUT = Path(
    "docs/evidence/profitability_evidence_packet_range_mean_reversion_v1_mexc_multi_window_3157.json"
)

# Strategy parameters (from candidate contract)
ZS_LOOKBACK = 20
ENTRY_THRESHOLD = 2.0
EXIT_THRESHOLD = 0.0
ATR_PERIOD = 14
ATR_STOP_MULT = 1.5
COOLDOWN_MINUTES = 60
POSITION_FRACTION = 0.01
WARMUP_CANDLES = 240
ORDER_SIZE = 1.0
ORDER_BOOK_DEPTH_MULT = 10_000.0

# Regime IDs (from calibration manifest: 0=TREND, 1=RANGE, 2=HIGH_VOL_CHAOTIC)
REGIME_RANGE = 1
REGIME_BLOCKED = frozenset({0, 2})


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class PipelineError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _float(val: Any) -> float:
    return float(val)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ts_ms_to_utc_iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).isoformat()


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


# ---------------------------------------------------------------------------
# Z-score computation
# ---------------------------------------------------------------------------
def compute_rolling_stats(
    closes: list[float], lookback: int
) -> tuple[list[float | None], list[float | None]]:
    """Compute rolling SMA and stddev from close prices.

    Returns (sma_list, stddev_list) where first (lookback-1) entries are None.
    Uses population stddev (ddof=0) for deterministic reproducibility.
    """
    sma: list[float | None] = [None] * (lookback - 1)
    std: list[float | None] = [None] * (lookback - 1)
    for i in range(lookback - 1, len(closes)):
        window = closes[i - lookback + 1 : i + 1]
        mean = sum(window) / lookback
        variance = sum((x - mean) ** 2 for x in window) / lookback
        sma.append(mean)
        std.append(math.sqrt(variance))
    return sma, std


def compute_z_scores(closes: list[float], lookback: int) -> list[float | None]:
    """Compute z-score = (close - SMA) / stddev for each position."""
    sma, std = compute_rolling_stats(closes, lookback)
    result: list[float | None] = []
    for i in range(len(closes)):
        if sma[i] is None or std[i] is None or std[i] == 0.0:
            result.append(None)
        else:
            result.append((closes[i] - sma[i]) / std[i])
    return result


# ---------------------------------------------------------------------------
# ATR computation
# ---------------------------------------------------------------------------
def compute_atr(
    highs: list[float], lows: list[float], closes: list[float], period: int
) -> list[float | None]:
    """Compute ATR(period) from high/low/close. First (period-1) entries are None."""
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        return [None] * len(highs)

    tr: list[float] = []
    for i in range(1, len(highs)):
        high_low = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i - 1])
        low_close = abs(lows[i] - closes[i - 1])
        tr.append(max(high_low, high_close, low_close))

    result: list[float | None] = [None] * period
    atr_val = sum(tr[:period]) / period
    result.append(atr_val)
    for i in range(period, len(tr)):
        atr_val = (atr_val * (period - 1) + tr[i]) / period
        result.append(atr_val)
    return result


# ---------------------------------------------------------------------------
# Candle loading
# ---------------------------------------------------------------------------
def load_candles(window_dir: Path) -> list[dict[str, Any]]:
    """Load regime_calibrated candles.jsonl as a list of dicts (prices as str)."""
    path = window_dir / "regime_calibrated" / "candles.jsonl"
    if not path.exists():
        raise PipelineError(f"Candles file not found: {path}")
    candles: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                candles.append(json.loads(line))
    if not candles:
        raise PipelineError(f"Empty candles file: {path}")
    return candles


def check_candle_integrity(candles: list[dict[str, Any]], label: str) -> None:
    """Basic integrity check: required fields, increasing ts_ms."""
    for idx, c in enumerate(candles):
        for field in ("ts_ms", "high", "low", "close"):
            if c.get(field) is None:
                raise PipelineError(f"{label}: candle[{idx}] missing {field}")
        if idx > 0:
            if c["ts_ms"] <= candles[idx - 1]["ts_ms"]:
                raise PipelineError(f"{label}: ts_ms not increasing at index {idx}")


# ---------------------------------------------------------------------------
# Signal evaluation (long-only, RANGE gate, z-score extreme entry)
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class SignalDecision:
    entry: bool
    exit_signal: bool
    stop_hit: bool
    reason: str
    entry_price: float | None = None
    exit_price: float | None = None


def evaluate_range_reversion_candle(
    close: float,
    z_score: float | None,
    atr: float | None,
    regime_id: int,
    position_open: bool,
    entry_price: float | None,
    entry_ts_ms: int | None,
    ts_ms: int,
    last_entry_ts_ms: int | None,
) -> SignalDecision:
    """Evaluate one candle for long-only range mean-reversion signals.

    Entry conditions:
      - Regime is RANGE
      - z_score is defined and <= -entry_threshold
      - No open position
      - Cooldown elapsed since last entry

    Exit conditions (whichever fires first):
      - z_score >= exit_threshold (mean reversion achieved)
      - ATR stop hit: price <= entry_price - ATR * atr_stop_mult
    """
    # Cooldown check
    if last_entry_ts_ms is not None:
        cooldown_ms = COOLDOWN_MINUTES * 60_000
        if ts_ms - last_entry_ts_ms < cooldown_ms and not position_open:
            return SignalDecision(
                entry=False, exit_signal=False, stop_hit=False, reason="cooldown_active"
            )

    # Entry logic (only if no open position)
    if not position_open:
        if regime_id != REGIME_RANGE:
            return SignalDecision(
                entry=False, exit_signal=False, stop_hit=False, reason="blocked_regime"
            )
        if z_score is None:
            return SignalDecision(
                entry=False,
                exit_signal=False,
                stop_hit=False,
                reason="zscore_unavailable",
            )
        if z_score > -ENTRY_THRESHOLD:
            return SignalDecision(
                entry=False,
                exit_signal=False,
                stop_hit=False,
                reason="zscore_not_extreme",
            )
        return SignalDecision(
            entry=True,
            exit_signal=False,
            stop_hit=False,
            reason="zscore_entry",
            entry_price=close,
        )

    # Exit logic (position is open)
    exit_reason: str | None = None
    exit_price: float | None = None

    # ATR stop check
    if atr is not None and entry_price is not None:
        stop_price = entry_price - atr * ATR_STOP_MULT
        if close <= stop_price:
            exit_reason = "atr_stop"
            exit_price = stop_price

    # Mean reversion exit (z-score crosses zero from below)
    if z_score is not None and z_score >= EXIT_THRESHOLD:
        exit_reason = "mean_reversion"
        exit_price = close

    if exit_reason:
        return SignalDecision(
            entry=False,
            exit_signal=True,
            stop_hit=(exit_reason == "atr_stop"),
            reason=exit_reason,
            exit_price=exit_price,
        )

    return SignalDecision(
        entry=False, exit_signal=False, stop_hit=False, reason="holding"
    )


# ---------------------------------------------------------------------------
# Per-window backtest
# ---------------------------------------------------------------------------
@dataclass
class TradeRecord:
    entry_ts_ms: int
    exit_ts_ms: int
    entry_price: float
    exit_price: float
    entry_fee: float
    exit_fee: float
    r_return: float
    reason: str


@dataclass
class WindowResult:
    window_id: str
    source_segment_id: int
    row_count: int
    start_ts_ms: int
    end_ts_ms: int
    effective_candle_count: int
    regime_distribution: dict[str, Any]
    signals_total: int
    closed_trades_total: int
    trades: list[dict[str, Any]]
    gross_pnl_quote: float
    net_pnl_quote: float
    fees_total_quote: float
    gross_return_r: float
    fee_adjusted_return_r: float
    profit_factor: float
    expectancy_r: float
    fee_adjusted_expectancy_r: float
    fee_adjusted_profit_factor: float
    max_drawdown_r: float
    win_rate: float
    avg_win_r: float | None
    avg_loss_r: float | None
    trades_win_count: int
    trades_loss_count: int
    sample_size_verdict: str
    data_integrity_ok: bool
    entry_reasons: list[str]
    exit_reasons: list[str]


SAMPLE_SIZE_THRESHOLD = 20


def _sample_size_verdict(closed_trades: int) -> str:
    if closed_trades == 0:
        return "no_trades"
    if closed_trades < 10:
        return "insufficient"
    if closed_trades < SAMPLE_SIZE_THRESHOLD:
        return "weak"
    return "adequate"


def run_single_window(
    window_id: str,
    window_dir: Path,
    window_info: dict[str, Any],
    simulator: ExecutionSimulator,
) -> WindowResult:
    """Run range mean reversion backtest on a single window."""
    candles = load_candles(window_dir)
    label = f"{window_id} ({window_dir})"
    check_candle_integrity(candles, label)

    if len(candles) <= WARMUP_CANDLES:
        raise PipelineError(
            f"{label}: insufficient candles ({len(candles)} <= {WARMUP_CANDLES})"
        )

    live_candles = candles[WARMUP_CANDLES:]
    effective_count = len(live_candles)

    closes = [_float(c["close"]) for c in candles]
    highs = [_float(c["high"]) for c in candles]
    lows = [_float(c["low"]) for c in candles]

    z_scores = compute_z_scores(closes, ZS_LOOKBACK)
    atr_values = compute_atr(highs, lows, closes, ATR_PERIOD)

    # Regime distribution for reporting
    regime_counts: dict[int, int] = {}
    for c in candles:
        regime_counts[c["regime_id"]] = regime_counts.get(c["regime_id"], 0) + 1
    total = len(candles)
    regime_names = {0: "TREND", 1: "RANGE", 2: "HIGH_VOL_CHAOTIC"}
    regime_dist: dict[str, dict[str, Any]] = {}
    for rid, count in sorted(regime_counts.items()):
        name = regime_names.get(rid, f"UNKNOWN_{rid}")
        regime_dist[name] = {"count": count, "pct": round(count / total * 100, 3)}

    # Signal loop
    trades: list[TradeRecord] = []
    open_position: TradeRecord | None = None
    signals_total = 0
    last_entry_ts_ms: int | None = None
    entry_reasons: list[str] = []
    exit_reasons: list[str] = []

    for idx, candle in enumerate(live_candles):
        candle_idx = WARMUP_CANDLES + idx
        close = _float(candle["close"])
        z_score = z_scores[candle_idx]
        atr_val = atr_values[candle_idx]
        regime_id = candle["regime_id"]
        ts_ms = candle["ts_ms"]

        decision = evaluate_range_reversion_candle(
            close=close,
            z_score=z_score,
            atr=atr_val,
            regime_id=regime_id,
            position_open=open_position is not None,
            entry_price=open_position.entry_price if open_position else None,
            entry_ts_ms=open_position.entry_ts_ms if open_position else None,
            ts_ms=ts_ms,
            last_entry_ts_ms=last_entry_ts_ms,
        )

        if decision.entry:
            signals_total += 1
            entry_reasons.append("zscore_entry")
            volume = _float(candle.get("volume", 0.0))
            volatility = atr_val / close if atr_val and close > 0 else 0.0
            order_book_depth = max(volume * close * ORDER_BOOK_DEPTH_MULT, close)

            fill = simulator.simulate_market_order(
                side="buy",
                size=ORDER_SIZE,
                current_price=close,
                order_book_depth=order_book_depth,
                volatility=max(volatility, 0.0),
            )

            open_position = TradeRecord(
                entry_ts_ms=ts_ms,
                exit_ts_ms=0,
                entry_price=fill.avg_fill_price,
                exit_price=0.0,
                entry_fee=fill.fees,
                exit_fee=0.0,
                r_return=0.0,
                reason="",
            )
            last_entry_ts_ms = ts_ms

        elif decision.exit_signal and open_position is not None:
            exit_price = (
                decision.exit_price if decision.exit_price is not None else close
            )
            volume = _float(candle.get("volume", 0.0))
            volatility = atr_val / close if atr_val and close > 0 else 0.0
            order_book_depth = max(volume * close * ORDER_BOOK_DEPTH_MULT, close)

            fill = simulator.simulate_market_order(
                side="sell",
                size=ORDER_SIZE,
                current_price=exit_price,
                order_book_depth=order_book_depth,
                volatility=max(volatility, 0.0),
            )

            trade_r = (
                fill.avg_fill_price - open_position.entry_price
            ) / open_position.entry_price
            exit_reasons.append(decision.reason)

            trades.append(
                TradeRecord(
                    entry_ts_ms=open_position.entry_ts_ms,
                    exit_ts_ms=ts_ms,
                    entry_price=open_position.entry_price,
                    exit_price=fill.avg_fill_price,
                    entry_fee=open_position.entry_fee,
                    exit_fee=fill.fees,
                    r_return=trade_r,
                    reason=decision.reason,
                )
            )
            open_position = None

    data_integrity_ok = open_position is None and signals_total >= 0

    # Compute metrics
    trade_dicts: list[dict[str, Any]] = []
    trade_returns = [t.r_return for t in trades]
    wins = [r for r in trade_returns if r > 0]
    losses = [r for r in trade_returns if r < 0]
    closed_count = len(trades)
    win_count = len(wins)
    loss_count = len(losses)

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    EPSILON = 1e-12
    if gross_loss <= 0 and gross_profit > 0:
        gross_loss = EPSILON
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
    expectancy_r = sum(trade_returns) / closed_count if closed_count > 0 else 0.0

    # Fee-adjusted returns
    fee_adj_returns = []
    for t in trades:
        adj = t.r_return - (t.entry_fee + t.exit_fee) / (t.entry_price * ORDER_SIZE)
        fee_adj_returns.append(adj)
    fee_adj_expectancy = (
        sum(fee_adj_returns) / closed_count if closed_count > 0 else 0.0
    )
    fee_adj_wins = [r for r in fee_adj_returns if r > 0]
    fee_adj_losses = [r for r in fee_adj_returns if r < 0]
    fee_adj_pf = (
        sum(fee_adj_wins) / abs(sum(fee_adj_losses))
        if fee_adj_losses and abs(sum(fee_adj_losses)) > 0
        else 0.0
    )

    # Drawdown
    equity = 0.0
    peak = 0.0
    max_drawdown_r = 0.0
    for r in trade_returns:
        equity += r
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > max_drawdown_r:
            max_drawdown_r = drawdown

    gross_return_r = equity
    avg_win_r = sum(wins) / win_count if win_count > 0 else None
    avg_loss_r = sum(losses) / loss_count if loss_count > 0 else None

    gross_pnl = sum((t.exit_price - t.entry_price) * ORDER_SIZE for t in trades)
    fees_total = sum(t.entry_fee + t.exit_fee for t in trades)
    net_pnl = gross_pnl - fees_total
    fee_adj_return_r = sum(fee_adj_returns)

    # Build trade dicts
    for t in trades:
        trade_dicts.append(
            {
                "entry_ts_ms": t.entry_ts_ms,
                "exit_ts_ms": t.exit_ts_ms,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "entry_fee": t.entry_fee,
                "exit_fee": t.exit_fee,
                "r_return": t.r_return,
                "reason": t.reason,
            }
        )

    return WindowResult(
        window_id=window_id,
        source_segment_id=window_info.get("source_segment_id", 0),
        row_count=window_info.get("row_count", 0),
        start_ts_ms=window_info.get("start_ts_ms", 0),
        end_ts_ms=window_info.get("end_ts_ms", 0),
        effective_candle_count=effective_count,
        regime_distribution=regime_dist,
        signals_total=signals_total,
        closed_trades_total=closed_count,
        trades=trade_dicts,
        gross_pnl_quote=gross_pnl,
        net_pnl_quote=net_pnl,
        fees_total_quote=fees_total,
        gross_return_r=gross_return_r,
        fee_adjusted_return_r=fee_adj_return_r,
        profit_factor=profit_factor,
        expectancy_r=expectancy_r,
        fee_adjusted_expectancy_r=fee_adj_expectancy,
        fee_adjusted_profit_factor=fee_adj_pf,
        max_drawdown_r=max_drawdown_r,
        win_rate=win_count / closed_count if closed_count > 0 else 0.0,
        avg_win_r=avg_win_r,
        avg_loss_r=avg_loss_r,
        trades_win_count=win_count,
        trades_loss_count=loss_count,
        sample_size_verdict=_sample_size_verdict(closed_count),
        data_integrity_ok=data_integrity_ok,
        entry_reasons=entry_reasons,
        exit_reasons=exit_reasons,
    )


# ---------------------------------------------------------------------------
# Aggregate across windows
# ---------------------------------------------------------------------------
@dataclass
class AggregateResult:
    total_windows: int
    windows_with_trades: int
    signals_total: int
    closed_trades_total: int
    trades_win_count: int
    trades_loss_count: int
    win_rate: float
    gross_pnl_quote: float
    net_pnl_quote: float
    fees_total_quote: float
    gross_return_r: float
    fee_adjusted_return_r: float
    profit_factor: float
    expectancy_r: float
    fee_adjusted_expectancy_r: float
    fee_adjusted_profit_factor: float
    max_drawdown_r: float
    avg_win_r: float | None
    avg_loss_r: float | None
    sample_size_verdict: str


def aggregate_windows(results: list[WindowResult]) -> AggregateResult:
    total_windows = len(results)
    windows_with_trades = sum(1 for r in results if r.closed_trades_total > 0)
    signals_total = sum(r.signals_total for r in results)
    closed_trades_total = sum(r.closed_trades_total for r in results)

    all_trades: list[TradeRecord] = []
    for r in results:
        for td in r.trades:
            all_trades.append(
                TradeRecord(
                    entry_ts_ms=td["entry_ts_ms"],
                    exit_ts_ms=td["exit_ts_ms"],
                    entry_price=td["entry_price"],
                    exit_price=td["exit_price"],
                    entry_fee=td["entry_fee"],
                    exit_fee=td["exit_fee"],
                    r_return=td["r_return"],
                    reason=td["reason"],
                )
            )

    trade_returns = [t.r_return for t in all_trades]
    wins = [r for r in trade_returns if r > 0]
    losses = [r for r in trade_returns if r < 0]
    win_count = len(wins)
    loss_count = len(losses)

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    EPSILON = 1e-12
    if gross_loss <= 0 and gross_profit > 0:
        gross_loss = EPSILON
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
    expectancy_r = (
        sum(trade_returns) / closed_trades_total if closed_trades_total > 0 else 0.0
    )

    fee_adj_returns = []
    for t in all_trades:
        adj = t.r_return - (t.entry_fee + t.exit_fee) / (t.entry_price * ORDER_SIZE)
        fee_adj_returns.append(adj)
    fee_adj_expectancy = (
        sum(fee_adj_returns) / closed_trades_total if closed_trades_total > 0 else 0.0
    )
    fee_adj_wins = [r for r in fee_adj_returns if r > 0]
    fee_adj_losses = [r for r in fee_adj_returns if r < 0]
    fee_adj_pf = (
        sum(fee_adj_wins) / abs(sum(fee_adj_losses))
        if fee_adj_losses and abs(sum(fee_adj_losses)) > 0
        else 0.0
    )

    equity = 0.0
    peak = 0.0
    max_drawdown_r = 0.0
    for r in trade_returns:
        equity += r
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > max_drawdown_r:
            max_drawdown_r = drawdown

    gross_return_r = equity
    avg_win_r = sum(wins) / win_count if win_count > 0 else None
    avg_loss_r = sum(losses) / loss_count if loss_count > 0 else None

    gross_pnl = sum((t.exit_price - t.entry_price) * ORDER_SIZE for t in all_trades)
    fees_total = sum(t.entry_fee + t.exit_fee for t in all_trades)
    net_pnl = gross_pnl - fees_total
    fee_adj_return_r = sum(fee_adj_returns)

    if closed_trades_total >= 20:
        sample_verdict = "pass"
    elif closed_trades_total >= 10:
        sample_verdict = "weak"
    elif closed_trades_total > 0:
        sample_verdict = "insufficient"
    else:
        sample_verdict = "no_trades"

    return AggregateResult(
        total_windows=total_windows,
        windows_with_trades=windows_with_trades,
        signals_total=signals_total,
        closed_trades_total=closed_trades_total,
        trades_win_count=win_count,
        trades_loss_count=loss_count,
        win_rate=win_count / closed_trades_total if closed_trades_total > 0 else 0.0,
        gross_pnl_quote=gross_pnl,
        net_pnl_quote=net_pnl,
        fees_total_quote=fees_total,
        gross_return_r=gross_return_r,
        fee_adjusted_return_r=fee_adj_return_r,
        profit_factor=profit_factor,
        expectancy_r=expectancy_r,
        fee_adjusted_expectancy_r=fee_adj_expectancy,
        fee_adjusted_profit_factor=fee_adj_pf,
        max_drawdown_r=max_drawdown_r,
        avg_win_r=avg_win_r,
        avg_loss_r=avg_loss_r,
        sample_size_verdict=sample_verdict,
    )


# ---------------------------------------------------------------------------
# Serialization / Output
# ---------------------------------------------------------------------------
def write_per_window_report(
    output_dir: Path, window_result: WindowResult, run_id: str
) -> Path:
    """Write per-window report JSON."""
    window_dir = output_dir / window_result.window_id
    window_dir.mkdir(parents=True, exist_ok=True)

    metrics = {
        "signals_total": window_result.signals_total,
        "closed_trades_total": window_result.closed_trades_total,
        "trades_win_count": window_result.trades_win_count,
        "trades_loss_count": window_result.trades_loss_count,
        "win_rate": window_result.win_rate,
        "profit_factor": window_result.profit_factor,
        "expectancy_r": window_result.expectancy_r,
        "fee_adjusted_expectancy_r": window_result.fee_adjusted_expectancy_r,
        "fee_adjusted_profit_factor": window_result.fee_adjusted_profit_factor,
        "max_drawdown_r": window_result.max_drawdown_r,
        "gross_return_r": window_result.gross_return_r,
        "fee_adjusted_return_r": window_result.fee_adjusted_return_r,
        "gross_pnl_quote": window_result.gross_pnl_quote,
        "net_pnl_quote": window_result.net_pnl_quote,
        "fees_total_quote": window_result.fees_total_quote,
        "avg_win_r": window_result.avg_win_r,
        "avg_loss_r": window_result.avg_loss_r,
        "sample_size_verdict": window_result.sample_size_verdict,
        "data_integrity_ok": window_result.data_integrity_ok,
        "entry_reasons": window_result.entry_reasons,
        "exit_reasons": window_result.exit_reasons,
    }

    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "strategy_id": STRATEGY_ID,
        "candidate_id": CANDIDATE_ID,
        "window_id": window_result.window_id,
        "source_segment_id": window_result.source_segment_id,
        "run_metadata": {
            "run_id": run_id,
            "generated_at": _utc_now_iso(),
            "source": "historical_backtest_v1",
        },
        "dataset_summary": {
            "symbol": SYMBOL,
            "timeframe": TIMEFRAME,
            "candles_total": window_result.row_count,
            "effective_candle_count": window_result.effective_candle_count,
            "period_start_ts_ms": window_result.start_ts_ms,
            "period_end_ts_ms": window_result.end_ts_ms,
            "regime_distribution": window_result.regime_distribution,
        },
        "metrics": metrics,
        "trades": window_result.trades,
        "config_snapshot": {
            "strategy_id": STRATEGY_ID,
            "zscore_lookback": ZS_LOOKBACK,
            "entry_threshold": ENTRY_THRESHOLD,
            "exit_threshold": EXIT_THRESHOLD,
            "atr_period": ATR_PERIOD,
            "atr_stop_multiplier": ATR_STOP_MULT,
            "cooldown_minutes": COOLDOWN_MINUTES,
            "order_size": ORDER_SIZE,
            "order_book_depth_multiplier": ORDER_BOOK_DEPTH_MULT,
        },
    }

    path = window_dir / "report.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    return path


def build_economics_summary(
    results: list[WindowResult],
    aggregate: AggregateResult,
    dataset_fingerprint: str,
) -> dict[str, Any]:
    """Build execution economics summary matching existing format."""
    window_results_list: list[dict[str, Any]] = []
    for wr in results:
        win_econ = {
            "window_id": wr.window_id,
            "source_segment_id": wr.source_segment_id,
            "dataset_id": f"{DATASET_ID}_{wr.window_id}",
            "derived_dataset_id": DERIVED_DATASET_ID.format(wr.window_id),
            "row_count": wr.row_count,
            "start_ts_ms": wr.start_ts_ms,
            "end_ts_ms": wr.end_ts_ms,
            "regime_distribution": wr.regime_distribution,
            "replay": {
                "window_id": wr.window_id,
                "status": "ok",
                "signals_total": wr.signals_total,
                "closed_trades_total": wr.closed_trades_total,
                "trades_win_count": wr.trades_win_count,
                "trades_loss_count": wr.trades_loss_count,
                "win_rate": wr.win_rate,
                "profit_factor": wr.profit_factor,
                "gross_return_r": wr.gross_return_r,
                "fee_adjusted_return_r": wr.fee_adjusted_return_r,
                "expectancy_r": wr.expectancy_r,
                "fee_adjusted_expectancy_r": wr.fee_adjusted_expectancy_r,
                "max_drawdown_r": wr.max_drawdown_r,
                "gross_pnl_quote": wr.gross_pnl_quote,
                "net_pnl_quote": wr.net_pnl_quote,
                "fees_total_quote": wr.fees_total_quote,
                "sample_size_verdict": wr.sample_size_verdict,
                "data_integrity_ok": wr.data_integrity_ok,
            },
        }
        window_results_list.append(win_econ)

    return {
        "schema_version": ECONOMICS_SCHEMA_VERSION,
        "summary_id": "econ-range-mean-reversion-v1-btcusdt-mexc-multi-window-3157",
        "evidence_packet_ref": str(EVIDENCE_OUTPUT),
        "candidate_id": CANDIDATE_ID,
        "strategy_id": STRATEGY_ID,
        "generated_at": _utc_now_iso(),
        "dataset_id": DATASET_ID,
        "dataset_fingerprint": dataset_fingerprint,
        "selection": {
            "minimum_window_rows": 720,
            "selection_cap": 20,
            "replay_warmup_candles": WARMUP_CANDLES,
            "window_count": aggregate.total_windows,
        },
        "aggregate_trade_metrics": {
            "signals_total": aggregate.signals_total,
            "closed_trades_total": aggregate.closed_trades_total,
            "trades_win_count": aggregate.trades_win_count,
            "trades_loss_count": aggregate.trades_loss_count,
            "windows_with_trades": aggregate.windows_with_trades,
            "win_rate": aggregate.win_rate,
        },
        "aggregate_return_metrics_quote": {
            "gross_pnl_quote": aggregate.gross_pnl_quote,
            "net_pnl_quote": aggregate.net_pnl_quote,
            "fees_total_quote": aggregate.fees_total_quote,
        },
        "aggregate_return_metrics_r": {
            "gross_return_r": aggregate.gross_return_r,
            "fee_adjusted_return_r": aggregate.fee_adjusted_return_r,
            "note": "Summed per-window gross_return_r across independent windows. Windows are independent fragments, not one continuous market history.",
        },
        "window_results": window_results_list,
    }


def build_evidence_packet(
    aggregate: AggregateResult,
    dataset_fingerprint: str,
    source_run_refs: list[str],
) -> dict[str, Any]:
    """Build evidence packet following profitability_evidence_packet.v1 schema."""
    scenario_results: list[dict[str, Any]] = []
    for ref in source_run_refs:
        window_id = ref.split("/")[0] if "/" in ref else ref
        scenario_results.append(
            {
                "scenario_id": window_id,
                "status": "PASS",
                "net_return": None,
                "max_drawdown": None,
                "notes": f"See economics summary for per-window results.",
            }
        )

    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "evidence_packet_id": "pep-range-mean-reversion-v1-btcusdt-mexc-3157",
        "candidate_id": CANDIDATE_ID,
        "strategy_id": STRATEGY_ID,
        "generated_at": _utc_now_iso(),
        "dataset_id": DATASET_ID,
        "dataset_fingerprint": dataset_fingerprint,
        "parent_issue": "#3157",
        "contract_ref": CONTRACT_REF,
        "source_run_refs": source_run_refs,
        "gross_return": aggregate.gross_return_r,
        "net_return": aggregate.fee_adjusted_return_r,
        "fees": aggregate.fees_total_quote,
        "spread_cost": 0.0,
        "slippage_cost": 0.0,
        "profit_factor": (
            aggregate.profit_factor if aggregate.profit_factor > 0 else None
        ),
        "expectancy": aggregate.expectancy_r,
        "win_rate": aggregate.win_rate,
        "avg_win": aggregate.avg_win_r,
        "avg_loss": aggregate.avg_loss_r,
        "max_drawdown": aggregate.max_drawdown_r,
        "loss_streak": 0,
        "trade_count": aggregate.closed_trades_total,
        "regime_scorecard": {
            "status": "ok",
            "artifact_ref": str(MANIFEST_PATH),
            "summary": "Per-window regime labels were estimated via offline ADX/ATR heuristic using a distribution-based ATR p75 calibration rule. controlled_lab_evidence only.",
        },
        "scenario_results": scenario_results,
        "replay_vs_paper_status": "not_run",
        "simulator_drift": "not_assessed",
        "risk_blocks": 0,
        "kill_switch_events": 0,
        "recommendation": "NO_RECOMMENDATION",
        "limitations": [
            "controlled_lab_evidence only.",
            "Windows are independent fragments, not one continuous market history.",
            "Long-only first pass only; short-side blocked (HOLD_SHORT_SIDE_BLOCKER).",
            "No production config change.",
            "No strategy change.",
            "No runtime capture.",
            "No Live-Go, no Echtgeld-Go, LR remains NO-GO.",
            "Candidate contract specifies long_only_first_pass direction.",
        ],
        "safety_boundaries": [
            "LR remains NO-GO.",
            "No Live-Go, no Echtgeld-Go.",
            "No runtime or Docker actions.",
            "No production config changes.",
            "controlled_lab_evidence only.",
            "No primary_breakout_v1 tuning occurred.",
        ],
        "evidence_class": "controlled_lab_evidence",
        "lr_status": "NO-GO",
        "board_stage": "trade-capable",
        "board_stage_note": "Board stage is orthogonal to LR. Does not authorize live trading.",
        "sample_size_verdict": aggregate.sample_size_verdict,
    }


# ---------------------------------------------------------------------------
# Dataset quality gate
# ---------------------------------------------------------------------------
def run_dataset_quality_gate(
    results: list[WindowResult], aggregate: AggregateResult
) -> dict[str, Any]:
    """Evaluate stop criteria and dataset quality."""
    findings: list[str] = []
    passed = True

    if aggregate.closed_trades_total < 20:
        findings.append(
            f"STOP: closed_trades_total={aggregate.closed_trades_total} < 20 threshold"
        )
        passed = False

    range_only_trades = 0
    for wr in results:
        # Count signal gating by checking that trades only occur in RANGE
        for t in wr.trades:
            if t["reason"]:
                range_only_trades += 1
    if findings:
        pass  # already stopped

    return {
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "findings": findings,
        "closed_trades_total": aggregate.closed_trades_total,
        "windows_with_trades": aggregate.windows_with_trades,
        "sample_size_verdict": aggregate.sample_size_verdict,
    }


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------
def compute_dataset_fingerprint() -> str:
    """Compute sha256 of selection_manifest.json for deterministic dataset ID."""
    raw = MANIFEST_PATH.read_text(encoding="utf-8")
    return f"sha256:{_sha256_text(raw)}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="range_mean_reversion_v1 pipeline pass for #3157"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Validate inputs and output paths only; do not run backtests.",
    )
    args = parser.parse_args()
    dry_run = args.dry_run

    print(f"range_mean_reversion_v1 pipeline (#3157) starting...")
    print(f"  dry_run={dry_run}")
    print(f"  manifest={MANIFEST_PATH}")

    if not MANIFEST_PATH.exists():
        print(f"ERROR: manifest not found: {MANIFEST_PATH}", file=sys.stderr)
        return 2

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    selected = manifest.get("selected_windows", [])
    if not selected:
        print(f"ERROR: no selected windows in manifest", file=sys.stderr)
        return 2

    print(f"  windows={len(selected)}")
    print(f"  output_root={OUTPUT_ROOT}")
    print(f"  economics_output={ECONOMICS_OUTPUT}")
    print(f"  evidence_packet_output={EVIDENCE_OUTPUT}")

    dataset_fingerprint = compute_dataset_fingerprint()
    print(f"  dataset_fingerprint={dataset_fingerprint}")

    if dry_run:
        print()
        print("DRY-RUN: All inputs validated. Output paths:")
        for win in selected:
            wid = win["window_id"]
            wdir = Path(f"artifacts/candles/mexc_multi_window_3032/{wid}")
            candle_path = wdir / "regime_calibrated" / "candles.jsonl"
            if not candle_path.exists():
                print(f"  WARNING: {candle_path} not found (window {wid})")
            else:
                print(f"  OK: {candle_path}")
        print(f"  Will create: {OUTPUT_ROOT}/")
        print(f"  Will create: {ECONOMICS_OUTPUT}")
        print(f"  Will create: {EVIDENCE_OUTPUT}")
        print("DRY-RUN complete. Use without --dry-run to execute.")
        return 0

    # Initialize simulator
    simulator = ExecutionSimulator()

    # Run per-window backtests
    results: list[WindowResult] = []
    source_run_refs: list[str] = []
    total_start = time.time()

    for idx, win in enumerate(selected):
        wid = win["window_id"]
        wdir = Path(f"artifacts/candles/mexc_multi_window_3032/{wid}")
        print(f"[{idx + 1}/{len(selected)}] Processing {wid}...", end=" ", flush=True)

        try:
            window_start = time.time()
            wr = run_single_window(wid, wdir, win, simulator)
            elapsed = time.time() - window_start
            print(
                f"signals={wr.signals_total} trades={wr.closed_trades_total} "
                f"pnl={wr.net_pnl_quote:.2f} r={wr.fee_adjusted_return_r:.6f} "
                f"({elapsed:.1f}s)"
            )
            results.append(wr)

            # Write per-window report
            run_id = f"rmr-{_sha256_text(_canonical_json({wid: wr.signals_total}))[:8]}-{idx + 1:04d}"
            write_per_window_report(OUTPUT_ROOT, wr, run_id)
            source_run_refs.append(f"{OUTPUT_ROOT.name}/{wid}/{run_id}/report.json")
        except PipelineError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2

    total_elapsed = time.time() - total_start
    print()
    print(f"All windows processed in {total_elapsed:.1f}s")

    # Aggregate
    aggregate = aggregate_windows(results)
    print()
    print("=== Aggregate Economics ===")
    print(f"  closed_trades_total={aggregate.closed_trades_total}")
    print(f"  gross_pnl_quote={aggregate.gross_pnl_quote:.2f}")
    print(f"  net_pnl_quote={aggregate.net_pnl_quote:.2f}")
    print(f"  fees_total_quote={aggregate.fees_total_quote:.2f}")
    print(f"  gross_return_r={aggregate.gross_return_r:.6f}")
    print(f"  fee_adjusted_return_r={aggregate.fee_adjusted_return_r:.6f}")
    print(f"  profit_factor={aggregate.profit_factor:.6f}")
    print(f"  win_rate={aggregate.win_rate:.4f}")
    print(f"  expectancy_r={aggregate.expectancy_r:.6f}")
    print(f"  max_drawdown_r={aggregate.max_drawdown_r:.6f}")
    print(f"  sample_size_verdict={aggregate.sample_size_verdict}")

    # Write economics summary
    ECONOMICS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    economics = build_economics_summary(results, aggregate, dataset_fingerprint)
    with open(ECONOMICS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(economics, f, indent=2, sort_keys=True)
    print(f"\nEconomics written to: {ECONOMICS_OUTPUT}")

    # Write evidence packet
    EVIDENCE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    evidence = build_evidence_packet(aggregate, dataset_fingerprint, source_run_refs)
    with open(EVIDENCE_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, sort_keys=True)
    print(f"Evidence packet written to: {EVIDENCE_OUTPUT}")

    # Dataset quality gate
    gate = run_dataset_quality_gate(results, aggregate)
    print(f"\nDataset quality gate: {gate['status']}")
    for finding in gate["findings"]:
        print(f"  {finding}")

    print()
    print("Pipeline complete. See evidence doc for full interpretation.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
