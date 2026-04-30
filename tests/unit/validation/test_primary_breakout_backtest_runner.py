"""Tests for the deterministic primary_breakout_v1 backtest runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

import services.validation.strategy_backtest_runner as backtest_runner
from core.contracts.external_adapter_contracts import (
    StrategyAdapterRequest,
    StrategyAdapterResponse,
    StrategySignalCandidate,
)
from services.validation.strategy_backtest_runner import (
    _build_data_integrity_diagnostics,
    PrimaryBreakoutBacktestError,
    PrimaryBreakoutBacktestRunConfig,
    run_primary_breakout_backtest,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = PROJECT_ROOT / "docs" / "contracts" / "strategy_validation_report_v1.schema.json"


def _candles() -> list[dict]:
    rows: list[dict] = []
    close = 100.0
    start_ts_ms = 1_700_000_000_000
    for index in range(380):
        if index < 240:
            close = 100.0
        elif index == 240:
            close = 101.5
        elif 241 <= index <= 360:
            close += 0.2
        elif index == 361:
            close = 100.0
        else:
            close += 0.05
        rows.append(
            {
                "symbol": "BTCUSDT",
                "ts_ms": start_ts_ms + index * 60_000,
                "open": close - 0.1,
                "high": close + 0.2,
                "low": close - 0.2,
                "close": close,
                "volume": 10_000.0 + index,
                "regime_id": 0,
                "market_state_fresh": True,
                "regime_fresh": True,
            }
        )
    return rows


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _bridge_requests() -> list[StrategyAdapterRequest]:
    base_ts_ms = 1_700_000_000_000
    closes = (100.0, 101.0, 102.0)
    return [
        StrategyAdapterRequest(
            symbol="BTCUSDT",
            market_event={
                "ts_ms": base_ts_ms + index * 60_000,
                "market_state": {
                    "market_state_fresh": True,
                    "regime_fresh": True,
                },
            },
            market_snapshot={
                "open": close - 0.5,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": 1_000.0,
            },
            runtime_context={},
        )
        for index, close in enumerate(closes)
    ]


@pytest.mark.unit
def test_primary_breakout_backtest_runner_is_deterministic_and_schema_valid() -> None:
    candles = _candles()
    config = PrimaryBreakoutBacktestRunConfig()

    first = run_primary_breakout_backtest(candles, run_config=config, code_commit="a9a62be")
    second = run_primary_breakout_backtest(candles, run_config=config, code_commit="a9a62be")

    assert first == second

    validator = Draft7Validator(_load_schema())
    assert list(validator.iter_errors(first)) == []
    assert first["strategy_id"] == "primary_breakout_v1"
    assert first["run_metadata"]["source"] == "historical_backtest_v1"
    assert first["metrics"]["closed_trades_total"] >= 1
    assert first["gate_result"]["status"] in {"PASS", "REVIEW", "FAIL"}


@pytest.mark.unit
def test_primary_breakout_backtest_runner_period_window_semantics() -> None:
    """Requested vs effective period boundaries are distinct and correctly related.

    _candles() produces 380 candles starting at ts_ms=1_700_000_000_000 with 1m cadence.
    With entry_lookback_minutes=240 the bridge warm-up consumes candles[0..239], so the
    first effective bridge request corresponds to candles[240].
    """
    candles = _candles()
    config = PrimaryBreakoutBacktestRunConfig()
    report = run_primary_breakout_backtest(candles, run_config=config, code_commit="a9a62be")

    ds = report["dataset_summary"]
    start_ts = 1_700_000_000_000
    end_ts = start_ts + 379 * 60_000
    max_lookback = max(
        config.bridge.entry_lookback_minutes, config.bridge.exit_lookback_minutes
    )

    assert ds["requested_period_start_ts_ms"] == start_ts
    assert ds["requested_period_end_ts_ms"] == end_ts
    # Effective start is offset by exactly max_lookback * 60_000 ms from requested start.
    assert ds["period_start_ts_ms"] == start_ts + max_lookback * 60_000
    # Effective end aligns with the last raw candle.
    assert ds["period_end_ts_ms"] == end_ts
    # Invariant: effective start must be strictly after requested start.
    assert ds["period_start_ts_ms"] > ds["requested_period_start_ts_ms"]


@pytest.mark.unit
def test_primary_breakout_backtest_runner_fail_closed_on_invalid_config() -> None:
    candles = _candles()
    config = PrimaryBreakoutBacktestRunConfig(order_size=0.0)

    with pytest.raises(PrimaryBreakoutBacktestError, match="order_size must be > 0"):
        run_primary_breakout_backtest(candles, run_config=config, code_commit="a9a62be")


@pytest.mark.unit
def test_primary_breakout_backtest_runner_surfaces_clean_end_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candles = _candles()[:3]
    requests = _bridge_requests()

    def fake_build_bridge(
        _candles_input: list[dict],
        *,
        config: PrimaryBreakoutBacktestRunConfig,
    ) -> list[StrategyAdapterRequest]:
        return requests

    def fake_evaluate(
        request: StrategyAdapterRequest,
        *,
        position_open: bool,
        last_entry_ts_ms: int | None,
        config: PrimaryBreakoutBacktestRunConfig,
        gate_trace_callback: object = None,
    ) -> tuple[StrategyAdapterResponse, int | None]:
        ts_ms = int(request.market_event["ts_ms"])
        if ts_ms == int(requests[0].market_event["ts_ms"]):
            return (
                StrategyAdapterResponse(
                    signals=(
                        StrategySignalCandidate(
                            strategy_id="primary_breakout_v1",
                            symbol="BTCUSDT",
                            side="BUY",
                            reason="test_entry",
                            price=100.0,
                            metadata={"adapter_id": "test"},
                        ),
                    ),
                    diagnostics={"status": "signal_emitted"},
                ),
                last_entry_ts_ms,
            )
        if ts_ms == int(requests[1].market_event["ts_ms"]):
            return (
                StrategyAdapterResponse(
                    signals=(
                        StrategySignalCandidate(
                            strategy_id="primary_breakout_v1",
                            symbol="BTCUSDT",
                            side="SELL",
                            reason="test_exit",
                            price=101.0,
                            metadata={"adapter_id": "test"},
                        ),
                    ),
                    diagnostics={"status": "signal_emitted"},
                ),
                last_entry_ts_ms,
            )
        return StrategyAdapterResponse(diagnostics={"status": "no_signal"}), last_entry_ts_ms

    def fake_simulate_trade(
        *,
        side: str,
        price: float,
        ts_ms: int,
        volume: float,
        simulator: object,
        order_size: float,
        order_book_depth_multiplier: float,
        volatility: float,
    ) -> dict[str, float | bool | str | None]:
        return {
            "side": side,
            "ts_ms": ts_ms,
            "filled_size": order_size,
            "avg_fill_price": price,
            "slippage_bps": 0.0,
            "fees": 0.0,
            "partial_fill": False,
            "fill_ratio": 1.0,
            "notes": None,
        }

    monkeypatch.setattr(
        backtest_runner,
        "build_primary_breakout_historical_bridge",
        fake_build_bridge,
    )
    monkeypatch.setattr(
        backtest_runner,
        "_evaluate_primary_breakout_request",
        fake_evaluate,
    )
    monkeypatch.setattr(backtest_runner, "_simulate_trade", fake_simulate_trade)

    report = run_primary_breakout_backtest(
        candles,
        run_config=PrimaryBreakoutBacktestRunConfig(),
        code_commit="a9a62be",
    )

    diagnostics = report["metrics"]["data_integrity_diagnostics"]
    assert report["metrics"]["data_integrity_ok"] is True
    assert diagnostics["data_integrity_reason"] == "clean"
    assert diagnostics["open_position_at_end"] is None
    assert diagnostics["pending_signals_at_end"] == []


@pytest.mark.unit
def test_primary_breakout_backtest_runner_surfaces_open_position_end_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candles = _candles()[:3]
    requests = _bridge_requests()

    def fake_build_bridge(
        _candles_input: list[dict],
        *,
        config: PrimaryBreakoutBacktestRunConfig,
    ) -> list[StrategyAdapterRequest]:
        return requests

    def fake_evaluate(
        request: StrategyAdapterRequest,
        *,
        position_open: bool,
        last_entry_ts_ms: int | None,
        config: PrimaryBreakoutBacktestRunConfig,
        gate_trace_callback: object = None,
    ) -> tuple[StrategyAdapterResponse, int | None]:
        ts_ms = int(request.market_event["ts_ms"])
        if ts_ms == int(requests[0].market_event["ts_ms"]):
            return (
                StrategyAdapterResponse(
                    signals=(
                        StrategySignalCandidate(
                            strategy_id="primary_breakout_v1",
                            symbol="BTCUSDT",
                            side="BUY",
                            reason="test_entry",
                            price=100.0,
                            metadata={"adapter_id": "test"},
                        ),
                    ),
                    diagnostics={"status": "signal_emitted"},
                ),
                last_entry_ts_ms,
            )
        return StrategyAdapterResponse(diagnostics={"status": "no_signal"}), last_entry_ts_ms

    def fake_simulate_trade(
        *,
        side: str,
        price: float,
        ts_ms: int,
        volume: float,
        simulator: object,
        order_size: float,
        order_book_depth_multiplier: float,
        volatility: float,
    ) -> dict[str, float | bool | str | None]:
        return {
            "side": side,
            "ts_ms": ts_ms,
            "filled_size": order_size,
            "avg_fill_price": price,
            "slippage_bps": 0.0,
            "fees": 0.0,
            "partial_fill": False,
            "fill_ratio": 1.0,
            "notes": None,
        }

    monkeypatch.setattr(
        backtest_runner,
        "build_primary_breakout_historical_bridge",
        fake_build_bridge,
    )
    monkeypatch.setattr(
        backtest_runner,
        "_evaluate_primary_breakout_request",
        fake_evaluate,
    )
    monkeypatch.setattr(backtest_runner, "_simulate_trade", fake_simulate_trade)

    report = run_primary_breakout_backtest(
        candles,
        run_config=PrimaryBreakoutBacktestRunConfig(),
        code_commit="a9a62be",
    )

    diagnostics = report["metrics"]["data_integrity_diagnostics"]
    assert report["metrics"]["data_integrity_ok"] is False
    assert diagnostics["data_integrity_reason"] == "open_position_at_end"
    assert diagnostics["open_position_at_end"] == {
        "entry_price": 100.0,
        "entry_ts_ms": int(requests[0].market_event["ts_ms"]),
        "entry_fee": 0.0,
    }
    assert diagnostics["pending_signals_at_end"] == []


@pytest.mark.unit
def test_build_data_integrity_diagnostics_surfaces_pending_signals() -> None:
    diagnostics = _build_data_integrity_diagnostics(
        None,
        (
            {
                "side": "BUY",
                "target_idx": 7,
                "execution_price": 101.25,
                "ts_ms": 1_700_000_060_000,
                "volume": 2.5,
                "volatility": 0.01,
            },
        ),
    )

    assert diagnostics["data_integrity_reason"] == "pending_signals_at_end"
    assert diagnostics["open_position_at_end"] is None
    assert diagnostics["pending_signals_at_end"] == [
        {
            "side": "BUY",
            "target_idx": 7,
            "execution_price": 101.25,
            "ts_ms": 1_700_000_060_000,
            "volume": 2.5,
            "volatility": 0.01,
        }
    ]


@pytest.mark.unit
def test_primary_breakout_backtest_runner_delays_execution_by_bar_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candles = _candles()[:3]
    requests = _bridge_requests()
    baseline_calls: list[dict[str, float]] = []
    delayed_calls: list[dict[str, float]] = []
    active_calls = baseline_calls

    def fake_build_bridge(
        _candles_input: list[dict],
        *,
        config: PrimaryBreakoutBacktestRunConfig,
    ) -> list[StrategyAdapterRequest]:
        return requests

    def fake_evaluate(
        request: StrategyAdapterRequest,
        *,
        position_open: bool,
        last_entry_ts_ms: int | None,
        config: PrimaryBreakoutBacktestRunConfig,
        gate_trace_callback: object = None,
    ) -> tuple[StrategyAdapterResponse, int | None]:
        ts_ms = int(request.market_event["ts_ms"])
        if ts_ms == int(requests[0].market_event["ts_ms"]):
            return (
                StrategyAdapterResponse(
                    signals=(
                        StrategySignalCandidate(
                            strategy_id="primary_breakout_v1",
                            symbol="BTCUSDT",
                            side="BUY",
                            reason="test_entry",
                            price=100.0,
                            metadata={"adapter_id": "test"},
                        ),
                    ),
                    diagnostics={"status": "signal_emitted"},
                ),
                last_entry_ts_ms,
            )
        if ts_ms == int(requests[1].market_event["ts_ms"]):
            return (
                StrategyAdapterResponse(
                    signals=(
                        StrategySignalCandidate(
                            strategy_id="primary_breakout_v1",
                            symbol="BTCUSDT",
                            side="SELL",
                            reason="test_exit",
                            price=101.0,
                            metadata={"adapter_id": "test"},
                        ),
                    ),
                    diagnostics={"status": "signal_emitted"},
                ),
                last_entry_ts_ms,
            )
        return StrategyAdapterResponse(diagnostics={"status": "no_signal"}), last_entry_ts_ms

    def fake_simulate_trade(
        *,
        side: str,
        price: float,
        ts_ms: int,
        volume: float,
        simulator: object,
        order_size: float,
        order_book_depth_multiplier: float,
        volatility: float,
    ) -> dict[str, float | bool | str | None]:
        active_calls.append({"price": price, "ts_ms": ts_ms})
        return {
            "side": side,
            "ts_ms": ts_ms,
            "filled_size": order_size,
            "avg_fill_price": price,
            "slippage_bps": 0.0,
            "fees": 0.0,
            "partial_fill": False,
            "fill_ratio": 1.0,
            "notes": None,
        }

    monkeypatch.setattr(
        backtest_runner,
        "build_primary_breakout_historical_bridge",
        fake_build_bridge,
    )
    monkeypatch.setattr(
        backtest_runner,
        "_evaluate_primary_breakout_request",
        fake_evaluate,
    )
    monkeypatch.setattr(backtest_runner, "_simulate_trade", fake_simulate_trade)

    baseline_report = run_primary_breakout_backtest(
        candles,
        run_config=PrimaryBreakoutBacktestRunConfig(),
        code_commit="a9a62be",
    )
    active_calls = delayed_calls
    delayed_report = run_primary_breakout_backtest(
        candles,
        run_config=PrimaryBreakoutBacktestRunConfig(),
        simulator_config={"EXECUTION_DELAY_BARS": 1},
        code_commit="a9a62be",
    )

    assert [call["ts_ms"] for call in baseline_calls] == [
        int(requests[0].market_event["ts_ms"]),
        int(requests[1].market_event["ts_ms"]),
    ]
    assert [call["ts_ms"] for call in delayed_calls] == [
        int(requests[1].market_event["ts_ms"]),
        int(requests[2].market_event["ts_ms"]),
    ]
    assert baseline_calls[0]["price"] == 100.0
    assert delayed_calls[0]["price"] == 101.0
    assert baseline_report["metrics"]["closed_trades_total"] == 1
    assert delayed_report["metrics"]["closed_trades_total"] == 1
    assert baseline_report["metrics"]["expectancy_r"] != delayed_report["metrics"]["expectancy_r"]


@pytest.mark.unit
def test_primary_breakout_backtest_runner_fails_closed_on_out_of_range_delay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candles = _candles()[:3]
    requests = _bridge_requests()

    def fake_build_bridge(
        _candles_input: list[dict],
        *,
        config: PrimaryBreakoutBacktestRunConfig,
    ) -> list[StrategyAdapterRequest]:
        return requests

    def fake_evaluate(
        request: StrategyAdapterRequest,
        *,
        position_open: bool,
        last_entry_ts_ms: int | None,
        config: PrimaryBreakoutBacktestRunConfig,
        gate_trace_callback: object = None,
    ) -> tuple[StrategyAdapterResponse, int | None]:
        if int(request.market_event["ts_ms"]) == int(requests[-1].market_event["ts_ms"]):
            return (
                StrategyAdapterResponse(
                    signals=(
                        StrategySignalCandidate(
                            strategy_id="primary_breakout_v1",
                            symbol="BTCUSDT",
                            side="BUY",
                            reason="late_entry",
                            price=102.0,
                            metadata={"adapter_id": "test"},
                        ),
                    ),
                    diagnostics={"status": "signal_emitted"},
                ),
                last_entry_ts_ms,
            )
        return StrategyAdapterResponse(diagnostics={"status": "no_signal"}), last_entry_ts_ms

    monkeypatch.setattr(
        backtest_runner,
        "build_primary_breakout_historical_bridge",
        fake_build_bridge,
    )
    monkeypatch.setattr(
        backtest_runner,
        "_evaluate_primary_breakout_request",
        fake_evaluate,
    )

    with pytest.raises(PrimaryBreakoutBacktestError, match="Delayed execution out of range"):
        run_primary_breakout_backtest(
            candles,
            run_config=PrimaryBreakoutBacktestRunConfig(),
            simulator_config={"EXECUTION_DELAY_BARS": 1},
            code_commit="a9a62be",
        )


@pytest.mark.unit
def test_primary_breakout_backtest_runner_gate_trace_path_is_opt_in(tmp_path: Path) -> None:
    """Verify that without gate_trace_path, no file is created and results remain stable."""
    candles = _candles()[:250]
    trace_path = tmp_path / "not_created.jsonl"

    # Run twice to ensure no side effects
    report_1 = run_primary_breakout_backtest(
        candles,
        run_config=PrimaryBreakoutBacktestRunConfig(),
        code_commit="opt-in-test",
    )
    report_2 = run_primary_breakout_backtest(
        candles,
        run_config=PrimaryBreakoutBacktestRunConfig(),
        code_commit="opt-in-test",
    )

    assert not trace_path.exists()
    assert report_1 == report_2


@pytest.mark.unit
def test_primary_breakout_backtest_runner_gate_trace_schema_and_single_pass(tmp_path: Path) -> None:
    """Verify JSONL schema and ensure determinism pass does not double-write traces."""
    candles = _candles()[:250]
    trace_path = tmp_path / "gate_trace.jsonl"

    run_primary_breakout_backtest(
        candles,
        run_config=PrimaryBreakoutBacktestRunConfig(),
        code_commit="trace-schema-test",
        gate_trace_path=trace_path,
    )

    assert trace_path.exists()
    lines = trace_path.read_text(encoding="utf-8").strip().split("\n")

    # Count should match bridge requests (250 candles - 240 warmup = 10 requests)
    assert len(lines) == 10

    required_fields = {
        "request_index", "ts_ms", "symbol", "close_now", "highest_high",
        "breakout_threshold", "breakout_buffer", "market_state_fresh",
        "regime_fresh", "regime_id", "has_trend_regime", "entry_blocked",
        "entry_cooldown_active", "position_open", "last_entry_ts_ms",
        "entry_ready", "status"
    }

    for line in lines:
        record = json.loads(line)
        missing = required_fields - set(record.keys())
        assert not missing, f"Missing fields in trace record: {missing}"


@pytest.mark.unit
def test_gate_trace_shows_fresh_trend_but_not_entry_ready_when_breakout_not_met(
    tmp_path: Path,
) -> None:
    candles = _candles()[:250]
    for candle in candles:
        candle["open"] = 99.9
        candle["high"] = 100.2
        candle["low"] = 99.8
        candle["close"] = 100.0
        candle["market_state_fresh"] = True
        candle["regime_fresh"] = True
        candle["regime_id"] = 0

    trace_path = tmp_path / "fresh_trend_no_breakout.jsonl"

    report = run_primary_breakout_backtest(
        candles,
        run_config=PrimaryBreakoutBacktestRunConfig(),
        code_commit="trace-no-breakout-test",
        gate_trace_path=trace_path,
    )

    assert report["metrics"]["signals_total"] == 0
    lines = trace_path.read_text(encoding="utf-8").strip().split("\n")
    assert lines

    first_record = json.loads(lines[0])
    assert first_record["market_state_fresh"] is True
    assert first_record["regime_fresh"] is True
    assert first_record["regime_id"] == 0
    assert first_record["has_trend_regime"] is True
    assert first_record["entry_blocked"] is False
    assert first_record["entry_cooldown_active"] is False
    assert first_record["entry_ready"] is False
    assert first_record["status"] == "no_signal"
    assert first_record["close_now"] < first_record["breakout_threshold"]
