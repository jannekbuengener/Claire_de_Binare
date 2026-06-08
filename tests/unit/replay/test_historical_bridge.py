"""Unit tests for deterministic primary breakout historical bridge."""

from __future__ import annotations

import json
import pathlib
from unittest.mock import patch

import pytest

from core.replay.historical_bridge import (
    HistoricalBridgeError,
    VALID_PRICE_POLICIES,
    PrimaryBreakoutBridgeConfig,
    build_primary_breakout_historical_bridge,
)
from services.signal.config import SignalConfig
from services.signal.service import SignalEngine


def _candles(
    count: int = 245,
    *,
    symbol: str = "BTCUSDT",
    start_ts_ms: int = 1_700_000_000_000,
) -> list[dict]:
    rows: list[dict] = []
    for index in range(count):
        close = 100.0 + index * 0.1
        row = {
            "symbol": symbol,
            "ts_ms": start_ts_ms + index * 60_000,
            "open": close - 0.1,
            "high": close + 0.2,
            "low": close - 0.2,
            "close": close,
            "volume": 10.0 + index,
            "regime_id": 0,
            "market_state_fresh": True,
            "regime_fresh": True,
        }
        rows.append(row)
    return rows


def _make_runtime_engine(config: SignalConfig) -> SignalEngine:
    with patch("services.signal.service.config", config):
        return SignalEngine()


@pytest.mark.unit
def test_bridge_is_deterministic_for_identical_input() -> None:
    candles = _candles()
    first = build_primary_breakout_historical_bridge(candles)
    second = build_primary_breakout_historical_bridge(candles)
    assert first == second


@pytest.mark.unit
def test_bridge_rejects_unsorted_timestamps_fail_closed() -> None:
    candles = _candles()
    candles[51]["ts_ms"] = candles[50]["ts_ms"]

    with pytest.raises(HistoricalBridgeError, match="strictly increasing"):
        build_primary_breakout_historical_bridge(candles)


@pytest.mark.unit
def test_bridge_rejects_non_1m_cadence_fail_closed() -> None:
    candles = _candles()
    candles[100]["ts_ms"] += 1000

    with pytest.raises(HistoricalBridgeError, match="strict 1m cadence"):
        build_primary_breakout_historical_bridge(candles)


@pytest.mark.unit
def test_bridge_rejects_missing_required_field_fail_closed() -> None:
    candles = _candles()
    del candles[30]["high"]

    with pytest.raises(HistoricalBridgeError, match="missing required field: high"):
        build_primary_breakout_historical_bridge(candles)


@pytest.mark.unit
def test_bridge_rejects_wrong_symbol_fail_closed() -> None:
    candles = _candles(symbol="ETHUSDT")

    with pytest.raises(HistoricalBridgeError, match="unexpected symbol"):
        build_primary_breakout_historical_bridge(candles)


@pytest.mark.unit
def test_bridge_output_is_adapter_ready_for_primary_breakout() -> None:
    candles = _candles()
    # Force a breakout on the first emitted request.
    warmup_idx = 240
    candles[warmup_idx]["close"] = candles[warmup_idx - 1]["high"] * 1.01
    candles[warmup_idx]["high"] = candles[warmup_idx]["close"] + 0.2
    candles[warmup_idx]["low"] = candles[warmup_idx]["close"] - 0.2

    requests = build_primary_breakout_historical_bridge(candles)
    first_request = requests[0]

    assert first_request.symbol == "BTCUSDT"
    assert first_request.runtime_context["strategy_id"] == "primary_breakout_v1"
    assert first_request.market_event["market_state"]["highest_high"] > 0
    assert first_request.market_event["market_state"]["lowest_low"] > 0
    assert first_request.market_event["market_state"]["regime_id"] in {0, "TREND"}


@pytest.mark.unit
def test_bridge_marks_gap_rows_as_insufficient_input_requests() -> None:
    candles = _candles()
    gap_idx = 240
    stale_source = dict(candles[gap_idx - 1])
    candles[gap_idx] = {
        **stale_source,
        "ts_ms": candles[gap_idx]["ts_ms"],
        "volume": 0.0,
        "market_state_fresh": False,
        "regime_fresh": False,
        "data_gap_active": True,
    }

    requests = build_primary_breakout_historical_bridge(candles)
    gap_request = requests[0]

    assert gap_request.market_event["market_state"]["data_gap_active"] is True
    assert gap_request.market_event["market_state"]["market_state_fresh"] is False
    assert gap_request.market_event["market_state"]["regime_fresh"] is False
    assert "close_now" not in gap_request.market_event["market_state"]
    assert "price" not in gap_request.market_event
    assert "close" not in gap_request.market_event
    assert "close" not in gap_request.market_snapshot
    assert "high" not in gap_request.market_snapshot
    assert "low" not in gap_request.market_snapshot


@pytest.mark.unit
def test_bridge_rejects_invalid_trade_side_mode_in_config() -> None:
    candles = _candles()
    config = PrimaryBreakoutBridgeConfig(trade_side_mode="both")

    with pytest.raises(
        HistoricalBridgeError, match="trade_side_mode must be long_only"
    ):
        build_primary_breakout_historical_bridge(candles, config=config)


@pytest.mark.unit
def test_runtime_and_historical_bridge_align_on_first_evaluable_breakout() -> None:
    bridge_config = PrimaryBreakoutBridgeConfig(
        entry_lookback_minutes=3,
        exit_lookback_minutes=2,
        breakout_buffer=0.0,
        min_minutes_between_entries=0,
    )
    signal_config = SignalConfig(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        min_volume=100.0,
        entry_lookback_minutes=3,
        exit_lookback_minutes=2,
        breakout_buffer=0.0,
        min_minutes_between_entries=0,
        trade_side_mode="long_only",
    )
    base_ts_ms = 1_700_000_000_000
    candles = [
        {
            "symbol": "BTCUSDT",
            "ts_ms": base_ts_ms + index * 60_000,
            "open": 99.5 + index,
            "high": 100.0 + index,
            "low": 99.0 + index,
            "close": 100.0 + index,
            "volume": 10_000.0 + index,
            "regime_id": 0,
            "market_state_fresh": True,
            "regime_fresh": True,
        }
        for index in range(4)
    ]

    runtime_engine = _make_runtime_engine(signal_config)
    runtime_signal = None
    runtime_signal_index = None
    for index, candle in enumerate(candles):
        signal = runtime_engine.process_market_data(
            {
                "symbol": candle["symbol"],
                "timestamp": candle["ts_ms"] // 1000,
                "price": candle["close"],
                "close": candle["close"],
                "high": candle["high"],
                "low": candle["low"],
                "volume": candle["volume"],
                "regime_id": candle["regime_id"],
                "market_state_fresh": candle["market_state_fresh"],
                "regime_fresh": candle["regime_fresh"],
            }
        )
        if signal is not None:
            runtime_signal = signal
            runtime_signal_index = index

    requests = build_primary_breakout_historical_bridge(candles, config=bridge_config)

    assert len(requests) == 1
    assert runtime_signal is not None
    assert runtime_signal_index == 3
    assert runtime_signal.side == "BUY"
    assert runtime_signal.reason == "breakout_entry"

    first_request = requests[0]
    assert (
        int(first_request.market_event["ts_ms"])
        == candles[runtime_signal_index]["ts_ms"]
    )
    assert (
        first_request.market_event["market_state"]["close_now"] == runtime_signal.price
    )
    assert (
        first_request.market_event["market_state"]["highest_high"]
        == runtime_signal.metadata["highest_high"]
        == 102.0
    )


@pytest.mark.unit
def test_price_policy_default_is_close() -> None:
    config = PrimaryBreakoutBridgeConfig()
    assert config.price_policy == "close"


@pytest.mark.unit
def test_price_policy_accepts_valid_values() -> None:
    for policy in ("close", "high", "hlc3", "ohlc4"):
        config = PrimaryBreakoutBridgeConfig(price_policy=policy)
        assert config.price_policy == policy


@pytest.mark.unit
def test_price_policy_rejects_invalid_value() -> None:
    with pytest.raises(HistoricalBridgeError, match="price_policy must be one of"):
        PrimaryBreakoutBridgeConfig(price_policy="midpoint").validate()


def _policy_candle_series(count: int = 245) -> list[dict]:
    """Monotonically increasing candle series for price policy tests."""
    return [
        {
            "symbol": "BTCUSDT",
            "ts_ms": 1_700_000_000_000 + i * 60_000,
            "open": 100.0 + i * 0.1,
            "high": 101.0 + i * 0.1,
            "low": 99.0 + i * 0.1,
            "close": 100.0 + i * 0.1,
            "volume": 10000.0 + i,
            "regime_id": 0,
            "market_state_fresh": True,
            "regime_fresh": True,
        }
        for i in range(count)
    ]


@pytest.mark.unit
def test_price_policy_high_produces_at_least_as_many_breakouts() -> None:
    """high policy should produce >= breakouts vs close on monotonically rising data."""
    candles = _candles(count=250)
    close_requests = build_primary_breakout_historical_bridge(
        candles,
        config=PrimaryBreakoutBridgeConfig(price_policy="close"),
    )
    high_requests = build_primary_breakout_historical_bridge(
        candles,
        config=PrimaryBreakoutBridgeConfig(price_policy="high"),
    )
    assert len(high_requests) >= len(close_requests)


@pytest.mark.unit
def test_price_policy_hlc3_computes_typical_price() -> None:
    candles = _policy_candle_series(250)
    close_req = build_primary_breakout_historical_bridge(
        candles,
        config=PrimaryBreakoutBridgeConfig(price_policy="close"),
    )
    hlc3_req = build_primary_breakout_historical_bridge(
        candles,
        config=PrimaryBreakoutBridgeConfig(price_policy="hlc3"),
    )
    if close_req:
        close_now_close = close_req[0].market_event["market_state"]["close_now"]
        close_now_hlc3 = hlc3_req[0].market_event["market_state"]["close_now"]
        candle_240 = candles[240]
        expected_hlc3 = round(
            (candle_240["high"] + candle_240["low"] + candle_240["close"]) / 3.0, 2
        )
        assert close_now_hlc3 == expected_hlc3
        assert close_now_close == candle_240["close"]


@pytest.mark.unit
def test_price_policy_ohlc4_computes_average_price() -> None:
    candles = _policy_candle_series(250)
    ohlc4_req = build_primary_breakout_historical_bridge(
        candles,
        config=PrimaryBreakoutBridgeConfig(price_policy="ohlc4"),
    )
    if ohlc4_req:
        candle_240 = candles[240]
        expected = round(
            (
                candle_240["open"]
                + candle_240["high"]
                + candle_240["low"]
                + candle_240["close"]
            )
            / 4.0,
            2,
        )
        assert ohlc4_req[0].market_event["market_state"]["close_now"] == expected


@pytest.mark.unit
def test_price_policy_all_policies_produce_valid_close_now() -> None:
    candles = _policy_candle_series(250)
    for policy in sorted(VALID_PRICE_POLICIES):
        requests = build_primary_breakout_historical_bridge(
            candles,
            config=PrimaryBreakoutBridgeConfig(price_policy=policy),
        )
        assert len(requests) > 0
        for req in requests:
            close_now = req.market_event["market_state"]["close_now"]
            assert isinstance(close_now, float)
            assert close_now > 0


@pytest.mark.unit
def test_price_policy_pilot_evaluation_differs() -> None:
    """Smoke check: at least one non-close policy must produce different close_now
    values on the real pilot candle dataset."""

    pilot = json.loads(
        pathlib.Path("artifacts/calibration/2961/pilot_candles.json").read_text("utf-8")
    )
    close_reqs = build_primary_breakout_historical_bridge(
        pilot,
        config=PrimaryBreakoutBridgeConfig(price_policy="close"),
    )
    high_reqs = build_primary_breakout_historical_bridge(
        pilot,
        config=PrimaryBreakoutBridgeConfig(price_policy="high"),
    )
    ohlc4_reqs = build_primary_breakout_historical_bridge(
        pilot,
        config=PrimaryBreakoutBridgeConfig(price_policy="ohlc4"),
    )
    # At least one of high or ohlc4 must produce different close_now values
    close_prices = {req.market_event["market_state"]["close_now"] for req in close_reqs}
    high_prices = {req.market_event["market_state"]["close_now"] for req in high_reqs}
    ohlc4_prices = {req.market_event["market_state"]["close_now"] for req in ohlc4_reqs}
    assert (
        close_prices != high_prices or close_prices != ohlc4_prices
    ), f"All policies produced identical close_now values: {close_prices}"
