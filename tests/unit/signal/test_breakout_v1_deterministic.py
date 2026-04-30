"""
Deterministic unit tests for _process_primary_breakout_v1.

Option C – Paper Evidence Signal Test (Issue context: probe blocked_no_new_high_final_timeout).

Goal: Prove the breakout pipeline logic is correct in isolation, without
live market conditions, Redis, Docker, or DB.

Design constraints:
- No Redis / no DB writes.  redis_client=None → _load_market_state returns {}.
  market_state_fresh / regime_fresh are injected via the raw payload dict
  (service.py lines 587-590 explicit fallback path).
- No PAPER_EVIDENCE_PROBE_MODE – we pass regime_id="TREND" + regime_fresh=True
  directly, which is the production path for a fresh TREND regime.
- Synthetic timestamps (seconds, converted to ms internally via normalize_ts_ms).
- entry_lookback_minutes=3, exit_lookback_minutes=2 for fast warmup.
- breakout_buffer=0.0 (geometric minimum – tested threshold in probe).
- min_minutes_between_entries=0 (no cooldown interference in most tests).

Governance: CDB_AGENT_POLICY.md, CDB_CONSTITUTION.md
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Path setup: avoid collision with built-in `signal` stdlib module
# ---------------------------------------------------------------------------
_services_signal = Path(__file__).parent.parent.parent.parent / "services" / "signal"
if str(_services_signal) not in sys.path:
    sys.path.insert(0, str(_services_signal))

from service import SignalEngine  # noqa: E402
from config import SignalConfig  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> SignalConfig:
    """Return a minimal primary_breakout_v1 config with optional overrides."""
    defaults = dict(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        min_volume=100.0,
        entry_lookback_minutes=3,
        exit_lookback_minutes=2,
        breakout_buffer=0.0,
        min_minutes_between_entries=0,
        trade_side_mode="long_only",
    )
    defaults.update(overrides)
    return SignalConfig(**defaults)


def _make_engine(config: SignalConfig) -> SignalEngine:
    """Instantiate SignalEngine with the given config patched in."""
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
    regime_id: str = "TREND",
    market_state_fresh: bool = True,
    regime_fresh: bool = True,
    risk_blocked: bool = False,
):
    """Send one market-data tick through the engine and return the Signal or None."""
    payload: dict = {
        "symbol": "BTCUSDT",
        "timestamp": ts,
        "price": price,
        "close": price,
        "high": high if high is not None else price,
        "low": low if low is not None else price,
        "volume": volume,
        "regime_id": regime_id,
        "market_state_fresh": market_state_fresh,
        "regime_fresh": regime_fresh,
    }
    if risk_blocked:
        payload["risk_blocked"] = True
    return engine.process_market_data(payload)


def _warmup(engine: SignalEngine, base_ts: int, base_price: float, minutes: int = 4):
    """
    Feed `minutes` ticks spaced 60 s apart to satisfy the entry warmup window.
    Returns (last_ts, last_price).

    Prices ascend by +1.0 per minute so each tick is a new high – the breakout
    condition depends on a SUBSEQUENT tick exceeding the window maximum, which
    this helper does NOT send.
    """
    ts = base_ts
    price = base_price
    for _ in range(minutes):
        _tick(engine, ts=ts, price=price, high=price, low=price - 1.0)
        ts += 60
        price += 1.0
    return ts, price


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_breakout_buy_fires_after_warmup():
    """
    Golden path: BUY fires exactly when:
      - warmup window is satisfied (>= entry_lookback_minutes of history)
      - close_now > highest_high in window  (breakout_buffer=0.0)
      - regime fresh + TREND
      - no risk block, no cooldown
    """
    config = _make_config()
    engine = _make_engine(config)
    base_ts = 1_700_000_000

    # Warmup: 4 ticks at 60s spacing, prices 100..103
    last_ts, last_price = _warmup(engine, base_ts, 100.0, minutes=4)

    # After warmup the window's highest_high = max(100,101,102,103) = 103.0
    # (last tick was appended AFTER decision, so the breakout tick's prior max = 103.0).
    # Actually: _update_breakout_history appends AFTER decision, so at the time of
    # the breakout tick the history contains the first 4 ticks (100-103).
    # We need close_now > 103.0.
    signal = _tick(engine, ts=last_ts, price=104.0, high=104.0, low=103.0)

    assert signal is not None, "Expected BUY signal after warmup + breakout"
    assert signal.side == "BUY"
    assert signal.symbol == "BTCUSDT"
    assert signal.reason == "breakout_entry"
    assert signal.price == 104.0
    assert signal.strategy_id == "primary_breakout_v1"


@pytest.mark.unit
def test_no_signal_before_warmup():
    """
    No BUY when entry_warmup_ok is False (history span < entry_lookback_minutes).
    Trades spaced 1 second apart do NOT satisfy the 3-minute window.
    """
    config = _make_config()
    engine = _make_engine(config)
    base_ts = 1_700_000_000

    for i in range(10):
        signal = _tick(
            engine,
            ts=base_ts + i,  # 1s spacing – never spans 3 minutes
            price=100.0 + i,
            high=100.0 + i,
            low=99.0 + i,
        )
        assert signal is None, f"Unexpected BUY at tick {i} before warmup"


@pytest.mark.unit
def test_runtime_lookback_is_elapsed_time_not_sample_count_regression():
    """
    Regression for #1941: dense observations must not satisfy the warmup span
    unless the elapsed wall-clock time covers the configured lookback window.
    """
    config = _make_config()
    engine = _make_engine(config)
    base_ts = 1_700_000_000

    # 180 one-second ticks produce far more observations than the 3-minute
    # lookback value, but they still span only 179 seconds of wall-clock time.
    for second_offset in range(180):
        signal = _tick(
            engine,
            ts=base_ts + second_offset,
            price=100.0,
            high=100.0,
            low=99.0,
        )
        assert signal is None, (
            "Dense ticks below the elapsed-time warmup span must not emit a BUY"
        )

    # The next tick reaches the full 3-minute span and becomes the first
    # evaluable breakout boundary.
    signal = _tick(
        engine,
        ts=base_ts + 180,
        price=101.0,
        high=101.0,
        low=100.0,
    )

    assert signal is not None
    assert signal.side == "BUY"
    assert signal.reason == "breakout_entry"


@pytest.mark.unit
def test_no_signal_price_at_exactly_highest_high():
    """
    Boundary: close_now == highest_high must NOT fire (strict >, buffer=0.0).
    """
    config = _make_config()
    engine = _make_engine(config)
    base_ts = 1_700_000_000

    last_ts, last_price = _warmup(engine, base_ts, 100.0, minutes=4)
    # highest_high after warmup = 103.0 (last appended tick).
    # Send exactly 103.0 – must not trigger.
    signal = _tick(engine, ts=last_ts, price=103.0, high=103.0, low=102.0)
    assert signal is None, "Signal must not fire when close_now == highest_high"


@pytest.mark.unit
def test_no_signal_when_risk_blocked():
    """
    risk_blocked gate: even with a valid breakout, no BUY if risk_blocked=True.
    """
    config = _make_config()
    engine = _make_engine(config)
    base_ts = 1_700_000_000

    last_ts, _ = _warmup(engine, base_ts, 100.0, minutes=4)
    signal = _tick(engine, ts=last_ts, price=104.0, risk_blocked=True)
    assert signal is None, "BUY must not fire when risk_blocked=True"


@pytest.mark.unit
def test_no_signal_when_market_state_not_fresh():
    """
    market_state_fresh=False blocks entry even when breakout condition holds.
    regime_fresh=False is implied (service.py: regime_fresh = market_state_fresh and ...).
    """
    config = _make_config()
    engine = _make_engine(config)
    base_ts = 1_700_000_000

    last_ts, _ = _warmup(engine, base_ts, 100.0, minutes=4)
    signal = _tick(
        engine,
        ts=last_ts,
        price=104.0,
        market_state_fresh=False,
        regime_fresh=False,
    )
    assert signal is None, "BUY must not fire when market_state is stale"


@pytest.mark.unit
def test_cooldown_blocks_second_entry():
    """
    min_minutes_between_entries=60: after a BUY, no new BUY within cooldown window.

    The warmup helper fires a BUY on the 4th tick (i=3, ts=base_ts+180s) because
    at that point the window [base_ts, base_ts+180] spans exactly 3 min and
    price=103 > max(100,101,102)=102.  We capture that signal, then verify the
    next tick (base_ts+240, price=104) is blocked by the 60-min cooldown.
    """
    config = _make_config(min_minutes_between_entries=60)
    engine = _make_engine(config)
    base_ts = 1_700_000_000

    # 3 setup ticks (no signal yet – warmup not complete)
    for i in range(3):
        s = _tick(engine, ts=base_ts + i * 60, price=100.0 + i, high=100.0 + i, low=99.0 + i)
        assert s is None, f"Unexpected signal at setup tick {i}"

    # 4th tick: warmup complete, breakout fires → first BUY
    signal1 = _tick(engine, ts=base_ts + 180, price=103.0, high=103.0, low=102.0)
    assert signal1 is not None and signal1.side == "BUY", "Expected first BUY at 4th tick"

    # 5th tick: price still above window high, but cooldown (60 min) is active
    signal2 = _tick(engine, ts=base_ts + 240, price=104.0, high=104.0, low=103.0)
    assert signal2 is None, "Second BUY must be blocked by 60-min cooldown"


@pytest.mark.unit
def test_sell_exit_fires_when_price_below_lowest_low():
    """
    Channel exit (SELL): after an open position, close_now < lowest_low triggers SELL.
    """
    config = _make_config(exit_lookback_minutes=2)
    engine = _make_engine(config)
    base_ts = 1_700_000_000

    # Warmup + open a position
    last_ts, _ = _warmup(engine, base_ts, 100.0, minutes=4)
    buy = _tick(engine, ts=last_ts, price=104.0, high=104.0, low=103.0)
    assert buy is not None and buy.side == "BUY"

    # The exit window (2 min) has lows from the last 2 minutes.
    # After the warmup+entry sequence the most recent lows in the 2-min window
    # are ≥ 102.0.  Send a price clearly below that.
    sell_ts = last_ts + 120  # +2 min – still within exit window of previous lows
    signal = _tick(engine, ts=sell_ts, price=90.0, high=91.0, low=90.0)

    assert signal is not None, "Expected SELL signal"
    assert signal.side == "SELL"
    assert signal.reason == "channel_exit"
    assert signal.price == 90.0


@pytest.mark.unit
def test_no_sell_without_open_position():
    """
    SELL must not fire if no position is open, even if price < lowest_low.

    We use risk_blocked=True during warmup ticks to prevent any BUY from
    opening a position, then confirm that a price drop does not produce a SELL.
    """
    config = _make_config()
    engine = _make_engine(config)
    base_ts = 1_700_000_000

    # Warmup with risk_blocked – builds history but no position opened
    for i in range(4):
        _tick(
            engine,
            ts=base_ts + i * 60,
            price=100.0 + i,
            high=100.0 + i,
            low=99.0 + i,
            risk_blocked=True,
        )

    # Verify position is NOT open
    assert not engine._position_open_by_symbol.get("BTCUSDT", False)

    # Price collapses – no SELL because no open position
    last_ts = base_ts + 4 * 60
    signal = _tick(engine, ts=last_ts, price=80.0, high=81.0, low=80.0)
    assert signal is None, "SELL must not fire without an open position"


@pytest.mark.unit
def test_gap_regression_resets_warmup():
    """
    Regression: after a 1-hour data gap, the new 3-minute window must be
    re-established before a BUY fires.  Old (pruned) history must not count.
    """
    config = _make_config()
    engine = _make_engine(config)
    t0 = 1_700_000_000

    # Initial history (will be pruned after gap)
    for i in range(5):
        _tick(engine, ts=t0 + i, price=100.0, high=100.0, low=99.0, risk_blocked=True)

    # Jump 1 hour forward – old entries are outside the 3-min window
    t_gap = t0 + 3600

    # Rapid ticks after the gap – warmup not yet satisfied
    for i in range(3):
        signal = _tick(engine, ts=t_gap + i, price=110.0, high=110.0, low=109.0)
        assert signal is None, f"Unexpected BUY at post-gap tick {i} (warmup drift)"

    # Exactly at gap + 3 minutes: warmup satisfied, price still > window high
    signal_final = _tick(engine, ts=t_gap + 180, price=115.0, high=115.0, low=114.0)
    assert signal_final is not None, "Expected BUY after re-established warmup"
    assert signal_final.side == "BUY"


@pytest.mark.unit
def test_signal_metadata_fields():
    """
    BUY signal metadata must contain required governance fields:
    strategy_id, config_snapshot, config_hash, signal_reason, signal_inputs.
    """
    config = _make_config()
    engine = _make_engine(config)
    base_ts = 1_700_000_000

    last_ts, _ = _warmup(engine, base_ts, 100.0, minutes=4)
    signal = _tick(engine, ts=last_ts, price=104.0, high=104.0, low=103.0)

    assert signal is not None
    meta = signal.metadata
    assert meta is not None, "metadata must not be None"
    assert meta.get("strategy_id") == "primary_breakout_v1"
    assert "config_snapshot" in meta, "config_snapshot missing from metadata"
    assert "config_hash" in meta, "config_hash missing from metadata"
    assert meta.get("signal_reason") == "breakout_entry"
    assert "signal_inputs" in meta


@pytest.mark.unit
def test_wrong_symbol_ignored():
    """
    Ticks for a symbol other than config.symbol must be silently ignored.
    """
    config = _make_config()
    engine = _make_engine(config)
    base_ts = 1_700_000_000

    # Push history then send breakout tick for ETHUSDT – must return None
    last_ts, _ = _warmup(engine, base_ts, 100.0, minutes=4)

    payload = {
        "symbol": "ETHUSDT",  # wrong symbol
        "timestamp": last_ts,
        "price": 104.0,
        "close": 104.0,
        "high": 104.0,
        "low": 103.0,
        "volume": 200_000.0,
        "market_state_fresh": True,
        "regime_fresh": True,
        "regime_id": "TREND",
    }
    signal = engine.process_market_data(payload)
    assert signal is None, "Signal must not fire for wrong symbol"
