"""Deterministic ARVP price-policy evaluation for replay signal semantics.

Evaluates each price policy (close, high, hlc3, ohlc4) against the existing
window bank and produces a comparison matrix.

Usage:
    python -m tools.replay.evaluate_price_policies

Output:
    - stdout: comparison matrix (markdown)
    - artifacts/price_policy_evaluation_3079/ — JSON + MD artifacts

Scope (#3079): deterministic, offline, no DB/Redis/MCP/runtime dependencies.
"""

from __future__ import annotations

import json
import logging
import pathlib
import sys
from typing import Any

from core.replay.historical_bridge import VALID_PRICE_POLICIES
from services.signal.config import SignalConfig
from services.signal.service import SignalEngine

logging.disable(logging.CRITICAL)

_ARTIFACT_DIR = pathlib.Path("artifacts/price_policy_evaluation_3079")
_PILOT_CANDLES_PATH = pathlib.Path("artifacts/calibration/2961/pilot_candles.json")
_PILOT_PAPER_PATH = pathlib.Path(
    "artifacts/recheck_2980/pilot_window_causal/paper_reference_window.json"
)
_W3028_CANDLES_PATH = pathlib.Path("artifacts/candles/3028_window/candles.json")
_W3028_PAPER_PATH = pathlib.Path(
    "artifacts/paper_reference_windows/paper_reference_window.json"
)


def _load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _create_signal_engine() -> SignalEngine:
    """Create a deterministic SignalEngine for policy evaluation."""
    from unittest.mock import patch

    config = SignalConfig(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        min_volume=0.0,
        entry_lookback_minutes=240,
        exit_lookback_minutes=120,
        breakout_buffer=0.0005,
        min_minutes_between_entries=60,
        trade_side_mode="long_only",
    )
    with patch("services.signal.service.config", config):
        return SignalEngine()


def _count_signals_by_policy(
    candles: list[dict[str, Any]], policy: str
) -> dict[str, int]:
    """Run the signal engine over candle data using a given price policy.

    Feeds each candle's OHLC values to the engine, using the policy price as
    ``price`` and ``close`` to simulate what the historical bridge would emit.
    Returns signal/order/fill counts.
    """
    engine = _create_signal_engine()

    signal_count = 0
    order_count = 0
    fill_count = 0

    for candle in candles:
        policy_price = None
        close = float(candle["close"])
        high = float(candle["high"])
        low = float(candle["low"])
        open_val = float(candle.get("open", close))
        if policy == "close":
            policy_price = close
        elif policy == "high":
            policy_price = high
        elif policy == "hlc3":
            policy_price = (high + low + close) / 3.0
        elif policy == "ohlc4":
            policy_price = (open_val + high + low + close) / 4.0

        signal = engine.process_market_data(
            {
                "symbol": candle["symbol"],
                "timestamp": candle["ts_ms"] // 1000,
                "price": policy_price,
                "close": policy_price,
                "high": high,
                "low": low,
                "volume": float(candle.get("volume", 0)),
                "regime_id": candle.get("regime_id", 0),
                "market_state_fresh": candle.get("market_state_fresh", True),
                "regime_fresh": candle.get("regime_fresh", True),
            }
        )
        if signal is not None:
            signal_count += 1
            if signal.side == "BUY":
                order_count += 1
                fill_count += 1
            elif signal.side == "SELL":
                pass

    return {
        "policy": policy,
        "signal_count": signal_count,
        "order_count": order_count,
        "fill_count": fill_count,
    }


def _paper_stats(paper_ref: dict[str, Any], window_label: str) -> dict[str, int]:
    """Extract paper reference signal/order/fill counts."""
    events = paper_ref.get("events", [])
    signal_count = 0
    order_count = 0
    fill_count = 0
    for ev in events:
        ev_type = ev.get("event_type")
        if ev_type == "SIGNAL":
            signal_count += 1
        elif ev_type == "ORDER":
            order_id = ev.get("order_id", "")
            if isinstance(order_id, str) and order_id.startswith("paper_"):
                order_count += 1
        elif ev_type == "FILL":
            order_id = ev.get("order_id", "")
            if isinstance(order_id, str) and order_id.startswith("paper_"):
                fill_count += 1
    causal = paper_ref.get("causal_context_events", [])
    causal_signal_count = sum(1 for cev in causal if cev.get("event_type") == "SIGNAL")
    return {
        "window": window_label,
        "paper_signal_count": signal_count,
        "paper_causal_signal_count": causal_signal_count,
        "paper_order_count": order_count,
        "paper_fill_count": fill_count,
    }


def evaluate_window(
    candles: list[dict[str, Any]],
    paper_ref: dict[str, Any],
    window_label: str,
) -> list[dict[str, Any]]:
    """Evaluate all price policies for one window, produce row per policy."""
    paper = _paper_stats(paper_ref, window_label)
    rows = []
    for policy in sorted(VALID_PRICE_POLICIES):
        result = _count_signals_by_policy(candles, policy)
        rows.append(
            {
                "window": window_label,
                "policy": policy,
                **result,
                "paper_signal_count": paper["paper_signal_count"],
                "paper_causal_signal_count": paper["paper_causal_signal_count"],
                "paper_order_count": paper["paper_order_count"],
                "paper_fill_count": paper["paper_fill_count"],
                "signal_count_delta": result["signal_count"]
                - paper["paper_signal_count"],
                "signal_context_delta": result["signal_count"]
                - (paper["paper_signal_count"] + paper["paper_causal_signal_count"]),
                "order_count_delta": result["order_count"] - paper["paper_order_count"],
                "fill_count_delta": result["fill_count"] - paper["paper_fill_count"],
            }
        )
    return rows


def build_matrix_md(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# ARVP Price Policy Evaluation Matrix",
        "",
        "**Scope:** #3079 — deterministic comparison of replay price policies",
        "**Generated:** offline, no DB/MCP/runtime dependencies",
        "",
        "## Per-Policy Comparison",
        "",
        "| Window | Policy | Signal | Order | Fill | Paper Sig | Paper Causal | Paper Ord | Paper Fill | Sig Δ | Ctx Δ | Ord Δ | Fill Δ |",
        "|--------|--------|-------:|------:|-----:|----------:|-------------:|----------:|-----------:|------:|------:|------:|-------:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['window']} | {r['policy']} "
            f"| {r['signal_count']} | {r['order_count']} | {r['fill_count']} "
            f"| {r['paper_signal_count']} | {r['paper_causal_signal_count']} "
            f"| {r['paper_order_count']} | {r['paper_fill_count']} "
            f"| {r['signal_count_delta']:+d} | {r['signal_context_delta']:+d} "
            f"| {r['order_count_delta']:+d} | {r['fill_count_delta']:+d} |"
        )
    return "\n".join(lines)


def main() -> None:
    pilot_candles = _load_json(_PILOT_CANDLES_PATH)
    pilot_paper = _load_json(_PILOT_PAPER_PATH)
    w3028_candles = _load_json(_W3028_CANDLES_PATH)
    w3028_paper = _load_json(_W3028_PAPER_PATH)

    results: list[dict[str, Any]] = []

    print("### Pilot Window (MEXC same-venue)")
    pilot_rows = evaluate_window(pilot_candles, pilot_paper, "pilot")
    results.extend(pilot_rows)
    for r in pilot_rows:
        print(
            f"  {r['policy']:8s} → signals={r['signal_count']}, "
            f"delta={r['signal_count_delta']:+d}, "
            f"ctx_delta={r['signal_context_delta']:+d}, "
            f"orders={r['order_count']}, fills={r['fill_count']}"
        )

    print()
    print("### #3028 Window (Binance venue_mismatch)")
    w3028_rows = evaluate_window(w3028_candles, w3028_paper, "3028")
    results.extend(w3028_rows)
    for r in w3028_rows:
        print(
            f"  {r['policy']:8s} → signals={r['signal_count']}, "
            f"delta={r['signal_count_delta']:+d}, "
            f"ctx_delta={r['signal_context_delta']:+d}, "
            f"orders={r['order_count']}, fills={r['fill_count']}"
        )

    matrix_md = build_matrix_md(results)
    print()
    print(matrix_md)

    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = _ARTIFACT_DIR / "policy_evaluation.json"
    json_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    md_path = _ARTIFACT_DIR / "policy_evaluation_matrix.md"
    md_path.write_text(matrix_md, encoding="utf-8")

    print(f"\nArtifacts written to {_ARTIFACT_DIR}/")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")


if __name__ == "__main__":
    main()
