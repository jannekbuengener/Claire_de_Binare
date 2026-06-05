"""ARVP stimulus fixture contract: regime TREND + breakout signal path (#3015)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from services.regime.models import Candle, compute_adx, compute_atr
from services.validation.paper_runtime_stimulus_runner import (
    DEFAULT_FIXTURE_PATH,
    ONE_MINUTE_MS,
    align_to_minute,
    generate_fixture_candles,
    load_fixture_spec,
    resolve_runtime_base_ts_ms,
    resolve_runtime_warmup_base_price,
    to_market_data_payload,
)

_services_signal = Path(__file__).resolve().parents[3] / "services" / "signal"
if str(_services_signal) not in sys.path:
    sys.path.insert(0, str(_services_signal))

from config import SignalConfig  # noqa: E402
from service import SignalEngine  # noqa: E402


def _simulate_regime_state_machine(
    candles: list[dict],
    *,
    atr_high_vol_threshold: float = 2.0,
    adx_trend_threshold: float = 25.0,
    adx_range_threshold: float = 20.0,
    confirmation_bars: int = 3,
    period: int = 14,
) -> tuple[str, str, float]:
    """Mirror ``RegimeService._derive_regime`` confirmation semantics."""
    bucket: list[Candle] = []
    current = "UNKNOWN"
    candidate: str | None = None
    candidate_count = 0
    last_raw = "UNKNOWN"
    last_atr = 0.0
    for candle in candles:
        bucket.append(
            Candle(
                ts=int(candle["ts_ms"] // 1000),
                symbol=candle["symbol"],
                timeframe="60s",
                open=float(candle["open"]),
                high=float(candle["high"]),
                low=float(candle["low"]),
                close=float(candle["close"]),
                volume=float(candle["volume"]),
            )
        )
        adx = compute_adx(bucket, period)
        atr = compute_atr(bucket, period)
        if adx is None or atr is None:
            continue
        last_atr = atr
        if atr >= atr_high_vol_threshold:
            raw_regime = "HIGH_VOL_CHAOTIC"
        elif adx >= adx_trend_threshold:
            raw_regime = "TREND"
        elif adx <= adx_range_threshold:
            raw_regime = "RANGE"
        else:
            raw_regime = current
        last_raw = raw_regime
        if raw_regime == current:
            candidate = None
            candidate_count = 0
            continue
        if candidate != raw_regime:
            candidate = raw_regime
            candidate_count = 1
        else:
            candidate_count += 1
        if candidate_count >= confirmation_bars:
            current = raw_regime
            candidate = None
            candidate_count = 0
    return current, last_raw, last_atr


def _make_breakout_engine() -> SignalEngine:
    config = SignalConfig(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        entry_lookback_minutes=240,
        exit_lookback_minutes=120,
        breakout_buffer=0.0005,
        min_minutes_between_entries=60,
        trade_side_mode="long_only",
        market_state_staleness_s=300,
    )
    engine = SignalEngine.__new__(SignalEngine)
    engine.config = config
    engine.redis_client = None
    engine._high_history = __import__("collections").defaultdict(list)
    engine._low_history = __import__("collections").defaultdict(list)
    engine._last_entry_ts_ms = {}
    engine._position_open_by_symbol = __import__("collections").defaultdict(bool)
    engine.price_buffer = __import__(
        "services.signal.price_buffer", fromlist=["PriceBuffer"]
    ).PriceBuffer()
    from core.contracts.external_adapter_registry import build_strategy_adapter

    engine.strategy_adapter = build_strategy_adapter(
        None, evaluate_fn=engine._evaluate_builtin_strategy
    )
    return engine


@pytest.mark.unit
def test_runtime_relative_anchors_breakout_to_current_minute():
    spec = load_fixture_spec(DEFAULT_FIXTURE_PATH)
    now_ms = align_to_minute(int(time.time() * 1000))
    base_ts = resolve_runtime_base_ts_ms(spec, wall_clock_ms=now_ms)
    candles = generate_fixture_candles(spec, base_ts_ms_override=base_ts)
    assert candles[-1]["ts_ms"] == now_ms
    assert candles[0]["ts_ms"] == now_ms - spec.warmup_count * ONE_MINUTE_MS


@pytest.mark.unit
def test_runtime_warmup_base_price_anchors_to_market_close():
    spec = load_fixture_spec(DEFAULT_FIXTURE_PATH)
    market_close = 60_123.45
    start = resolve_runtime_warmup_base_price(spec, market_close=market_close)
    candles = generate_fixture_candles(spec, warmup_base_price_override=start)
    highest = candles[-2]["close"]
    assert highest == pytest.approx(market_close, rel=0, abs=spec.warmup_price_step)


@pytest.mark.unit
def test_fixture_breakout_keeps_regime_trend_not_high_vol():
    spec = load_fixture_spec(DEFAULT_FIXTURE_PATH)
    market_close = 60_000.0
    start = resolve_runtime_warmup_base_price(spec, market_close=market_close)
    now_ms = align_to_minute(int(time.time() * 1000))
    base_ts = resolve_runtime_base_ts_ms(spec, wall_clock_ms=now_ms)
    candles = generate_fixture_candles(
        spec,
        base_ts_ms_override=base_ts,
        warmup_base_price_override=start,
    )
    current, last_raw, atr = _simulate_regime_state_machine(candles)
    assert (
        current == "TREND"
    ), f"confirmed regime must stay TREND (current={current}, last_raw={last_raw}, atr={atr})"


@pytest.mark.unit
def test_legacy_premium_spike_would_classify_high_vol():
    """Documents the pre-#3015 failure mode: large breakout premium spikes ATR."""
    spec = load_fixture_spec(DEFAULT_FIXTURE_PATH)
    candles = generate_fixture_candles(spec)
    highest = candles[-2]["close"]
    threshold = highest * (1 + spec.breakout_buffer)
    spike_close = highest * (1 + spec.breakout_close_premium_pct / 100.0)
    for idx in range(-3, 0):
        candles[idx]["close"] = spike_close
        candles[idx]["high"] = spike_close
    current, last_raw, atr = _simulate_regime_state_machine(candles)
    assert last_raw == "HIGH_VOL_CHAOTIC"
    assert current == "HIGH_VOL_CHAOTIC"
    assert atr >= 2.0
    assert spike_close > threshold


@pytest.mark.unit
def test_stimulus_fixture_sequence_emits_breakout_buy_signal():
    spec = load_fixture_spec(DEFAULT_FIXTURE_PATH)
    market_close = 60_000.0
    start = resolve_runtime_warmup_base_price(spec, market_close=market_close)
    now_ms = align_to_minute(int(time.time() * 1000))
    base_ts = resolve_runtime_base_ts_ms(spec, wall_clock_ms=now_ms)
    candles = generate_fixture_candles(
        spec,
        base_ts_ms_override=base_ts,
        warmup_base_price_override=start,
        stimulus_run_id="contract-test",
    )
    engine = _make_breakout_engine()
    signal = None
    for candle in candles:
        payload = to_market_data_payload(candle)
        signal = engine.process_market_data(payload)
    assert signal is not None
    assert signal.side == "BUY"
    assert signal.reason == "breakout_entry"
