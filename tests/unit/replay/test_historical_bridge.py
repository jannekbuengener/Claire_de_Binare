"""Unit tests for deterministic primary breakout historical bridge."""

import pytest

from core.replay.historical_bridge import (
    HistoricalBridgeError,
    PrimaryBreakoutBridgeConfig,
    build_primary_breakout_historical_bridge,
)


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

    with pytest.raises(HistoricalBridgeError, match="trade_side_mode must be long_only"):
        build_primary_breakout_historical_bridge(candles, config=config)
