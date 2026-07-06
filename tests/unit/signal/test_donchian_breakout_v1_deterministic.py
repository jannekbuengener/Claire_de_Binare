"""Deterministic unit tests for donchian_breakout_v1 runtime signal path (#3789)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_services_signal = Path(__file__).parent.parent.parent.parent / "services" / "signal"
if str(_services_signal) not in sys.path:
    sys.path.insert(0, str(_services_signal))

from service import SignalEngine  # noqa: E402
from config import SignalConfig  # noqa: E402


def _make_config(**overrides) -> SignalConfig:
    defaults = dict(
        strategy_id="donchian_breakout_v1",
        symbol="BTCUSDT",
        min_volume=100.0,
        entry_channel_bars=3,
        exit_channel_bars=2,
        min_minutes_between_entries=0,
        trade_side_mode="long_only",
    )
    defaults.update(overrides)
    return SignalConfig(**defaults)


def _make_engine(config: SignalConfig) -> SignalEngine:
    with patch("service.config", config):
        return SignalEngine()


def _tick(
    engine: SignalEngine,
    *,
    ts: int,
    price: float,
    high: float | None = None,
    low: float | None = None,
    volume: float = 200_000.0,
    risk_blocked: bool = False,
):
    payload: dict = {
        "symbol": "BTCUSDT",
        "timestamp": ts,
        "price": price,
        "close": price,
        "high": high if high is not None else price,
        "low": low if low is not None else price,
        "volume": volume,
        "pct_change": 5.0,
    }
    if risk_blocked:
        payload["risk_blocked"] = True
    return engine.process_market_data(payload)


@pytest.mark.unit
def test_donchian_generates_buy_on_upper_channel_break():
    engine = _make_engine(_make_config())
    base_ts = 1_700_000_000
    seed = [
        {"price": 100.0, "high": 100.0, "low": 99.0},
        {"price": 101.0, "high": 101.0, "low": 100.0},
        {"price": 102.0, "high": 102.0, "low": 101.0},
    ]
    for idx, row in enumerate(seed):
        assert (
            _tick(
                engine,
                ts=base_ts + idx * 60,
                price=row["price"],
                high=row["high"],
                low=row["low"],
            )
            is None
        )

    breakout = _tick(engine, ts=base_ts + 180, price=103.0, high=103.0, low=102.0)

    assert breakout is not None
    assert breakout.side == "BUY"
    assert breakout.strategy_id == "donchian_breakout_v1"
    assert breakout.reason == "donchian_upper_break"
    assert breakout.metadata is not None
    assert breakout.metadata["strategy_id"] == "donchian_breakout_v1"
    assert breakout.metadata["donchian_upper"] == 102.0


@pytest.mark.unit
def test_donchian_current_bar_excluded_from_channel_calculation():
    """Upper channel must use prior closed bars only (exclusive of current tick)."""
    engine = _make_engine(_make_config(entry_channel_bars=2, exit_channel_bars=2))
    base_ts = 1_700_000_000
    _tick(engine, ts=base_ts, price=100.0, high=100.0, low=99.0)
    _tick(engine, ts=base_ts + 60, price=101.0, high=101.0, low=100.0)

    # close equals prior window high (101) — strict break requires >
    assert _tick(engine, ts=base_ts + 120, price=101.0, high=101.0, low=100.0) is None

    breakout = _tick(engine, ts=base_ts + 180, price=101.5, high=101.5, low=100.5)
    assert breakout is not None
    assert breakout.side == "BUY"


@pytest.mark.unit
def test_donchian_no_momentum_fallback_without_channel_break():
    engine = _make_engine(_make_config())
    base_ts = 1_700_000_000
    for idx in range(3):
        assert (
            _tick(
                engine,
                ts=base_ts + idx * 60,
                price=100.0 + idx,
                high=100.0 + idx,
                low=99.0 + idx,
            )
            is None
        )

    # Large pct_change but close does not break Donchian upper channel.
    assert (
        _tick(
            engine,
            ts=base_ts + 180,
            price=100.5,
            high=100.5,
            low=99.5,
            volume=500_000.0,
        )
        is None
    )


@pytest.mark.unit
def test_donchian_respects_entry_cooldown():
    engine = _make_engine(_make_config(min_minutes_between_entries=60))
    base_ts = 1_700_000_000
    for idx, high in enumerate([100.0, 101.0, 102.0]):
        _tick(engine, ts=base_ts + idx * 60, price=high, high=high, low=high - 1.0)

    first = _tick(
        engine,
        ts=base_ts + 180,
        price=103.0,
        high=103.0,
        low=102.0,
    )
    assert first is not None and first.side == "BUY"

    engine._position_open_by_symbol["BTCUSDT"] = False  # noqa: SLF001

    second = _tick(
        engine,
        ts=base_ts + 210,
        price=104.0,
        high=104.0,
        low=103.0,
    )
    assert second is None


@pytest.mark.unit
def test_donchian_emits_sell_on_lower_channel_break():
    engine = _make_engine(_make_config())
    base_ts = 1_700_000_000
    _tick(engine, ts=base_ts, price=100.0, high=100.0, low=99.0)
    _tick(engine, ts=base_ts + 60, price=101.0, high=101.0, low=100.0)
    _tick(engine, ts=base_ts + 120, price=102.0, high=102.0, low=101.0)
    entry = _tick(engine, ts=base_ts + 180, price=103.0, high=103.0, low=102.0)
    assert entry is not None and entry.side == "BUY"

    # Feed lows that establish a lower channel, then break below it.
    _tick(engine, ts=base_ts + 240, price=102.0, high=102.5, low=101.0)
    _tick(engine, ts=base_ts + 300, price=101.0, high=101.5, low=100.0)
    exit_signal = _tick(engine, ts=base_ts + 360, price=99.0, high=99.5, low=98.5)

    assert exit_signal is not None
    assert exit_signal.side == "SELL"
    assert exit_signal.reason == "donchian_lower_break"
    assert exit_signal.strategy_id == "donchian_breakout_v1"


@pytest.mark.unit
def test_donchian_entry_blocked_when_risk_blocked():
    engine = _make_engine(_make_config())
    base_ts = 1_700_000_000
    for idx, high in enumerate([100.0, 101.0, 102.0]):
        _tick(engine, ts=base_ts + idx * 60, price=high, high=high, low=high - 1.0)

    blocked = _tick(
        engine,
        ts=base_ts + 180,
        price=103.0,
        high=103.0,
        low=102.0,
        risk_blocked=True,
    )
    assert blocked is None


@pytest.mark.unit
def test_donchian_rejects_non_canonical_strategy_adapter(monkeypatch):
    test_config = _make_config()
    monkeypatch.setenv("SIGNAL_ADAPTER_ID", "does_not_exist")

    with patch("service.config", test_config):
        with pytest.raises(SystemExit) as excinfo:
            SignalEngine()
    assert excinfo.value.code == 1
