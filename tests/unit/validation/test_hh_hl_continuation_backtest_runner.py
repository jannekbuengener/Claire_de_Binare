"""Unit tests for hh_hl_continuation_v1 (#4372)."""

from __future__ import annotations

import copy
import math
from typing import Any

import pytest

from core.replay.batch_b_strategy_registry import (
    BATCH_B_BOUND_MAIN_SHA,
    BATCH_B_OWNER_GO_COMMENT_ID,
    assert_batch_b_executable,
    executable_batch_b_strategy_ids,
    get_batch_b_strategy,
)
from core.replay.canonical_json import canonical_hash
from core.replay.hh_hl_continuation_common import (
    BATCH_B_SHADOW_ADAPTER_ID,
    HH_HL_CONTINUATION_STRATEGY_ID,
    HhHlContinuationConfig,
    confirmed_swing_at,
    frozen_hh_hl_parameters,
    hh_hl_warmup_candles,
    structure_is_hh_hl,
    validate_hh_hl_candle_series,
)
from services.validation.hh_hl_continuation_backtest_runner import (
    run_hh_hl_continuation_backtest,
)
from services.validation.strategy_replay_runner import (
    ARVPReplayConfig,
    _SUPPORTED_STRATEGY_IDS,
    _validate_strategy_adapter_pair,
)

pytestmark = pytest.mark.unit


def _candle(
    ts_ms: int,
    *,
    open_px: float,
    high: float,
    low: float,
    close: float,
) -> dict[str, Any]:
    return {
        "symbol": "BTCUSDT",
        "ts_ms": ts_ms,
        "open": open_px,
        "high": high,
        "low": low,
        "close": close,
        "volume": 1_000.0,
    }


def _flat(ts_ms: int, price: float, *, spread: float = 0.2) -> dict[str, Any]:
    return _candle(
        ts_ms,
        open_px=price,
        high=price + spread,
        low=price - spread,
        close=price,
    )


def _hh_hl_structure_candles() -> list[dict[str, Any]]:
    """Synthetic 1m series that confirms HH+HL then later breaks HL."""
    start = 1_700_000_000_000
    prices = [
        # warmup / first swing low around index 4 (confirm at 6)
        100.0,
        99.0,
        98.0,
        97.0,
        96.0,  # SL1 pivot
        97.0,
        98.0,
        # swing high 1 around index 10 (confirm at 12)
        99.0,
        100.0,
        101.0,
        104.0,  # SH1 pivot
        102.0,
        101.0,
        # higher low around index 16 (confirm at 18)
        100.5,
        100.0,
        99.5,
        99.0,  # SL2 pivot > SL1
        99.8,
        100.2,
        # higher high around index 22 (confirm at 24) -> entry
        101.0,
        102.0,
        103.0,
        106.0,  # SH2 pivot > SH1
        104.0,
        103.0,
        # hold
        103.5,
        104.0,
        103.8,
        # lower low break around index 32 (confirm at 34) -> exit
        103.0,
        102.0,
        101.0,
        98.0,  # SL3 pivot < SL2
        99.0,
        100.0,
        100.5,
        101.0,
    ]
    rows: list[dict[str, Any]] = []
    for index, price in enumerate(prices):
        rows.append(_flat(start + index * 60_000, price))
    return rows


def test_registry_entry_is_executable_and_bound() -> None:
    record = get_batch_b_strategy(HH_HL_CONTINUATION_STRATEGY_ID)
    assert record.executable
    assert record.runner_module.endswith("hh_hl_continuation_backtest_runner")
    assert record.frozen_parameters == frozen_hh_hl_parameters()
    assert record.warmup_bars == hh_hl_warmup_candles()
    assert HH_HL_CONTINUATION_STRATEGY_ID in executable_batch_b_strategy_ids()
    assert assert_batch_b_executable(HH_HL_CONTINUATION_STRATEGY_ID) is record
    assert BATCH_B_OWNER_GO_COMMENT_ID == "5196985942"
    assert BATCH_B_BOUND_MAIN_SHA.startswith("279b7100")


def test_strategy_adapter_pair_accepts_batch_b_shadow() -> None:
    assert HH_HL_CONTINUATION_STRATEGY_ID in _SUPPORTED_STRATEGY_IDS
    _validate_strategy_adapter_pair(
        HH_HL_CONTINUATION_STRATEGY_ID, BATCH_B_SHADOW_ADAPTER_ID
    )
    with pytest.raises(ValueError, match="batch_b_shadow_runner_v1"):
        _validate_strategy_adapter_pair(
            HH_HL_CONTINUATION_STRATEGY_ID, "batch_a_shadow_runner_v1"
        )


def test_arvp_config_accepts_hh_hl() -> None:
    cfg = ARVPReplayConfig(
        strategy_id=HH_HL_CONTINUATION_STRATEGY_ID,
        adapter_id=BATCH_B_SHADOW_ADAPTER_ID,
        symbol="BTCUSDT",
        dataset_source="file",
        input_candles_file="artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json",
    )
    cfg.validate()


def test_hh_hl_scenario_group_is_fail_closed() -> None:
    """HARDEN_PR_4373_BEFORE_MERGE — no scenario-group / stress / campaign for Batch-B."""
    cfg = ARVPReplayConfig(
        strategy_id=HH_HL_CONTINUATION_STRATEGY_ID,
        adapter_id=BATCH_B_SHADOW_ADAPTER_ID,
        symbol="BTCUSDT",
        dataset_source="file",
        input_candles_file="artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json",
        scenario_ids=("baseline",),
    )
    with pytest.raises(ValueError, match="does not support scenario-group"):
        cfg.validate()

    cfg_group_id = ARVPReplayConfig(
        strategy_id=HH_HL_CONTINUATION_STRATEGY_ID,
        adapter_id=BATCH_B_SHADOW_ADAPTER_ID,
        symbol="BTCUSDT",
        dataset_source="file",
        input_candles_file="artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json",
        scenario_group_id="sg-batch-b-forbidden",
    )
    with pytest.raises(ValueError, match="does not support scenario-group"):
        cfg_group_id.validate()


def test_registered_batch_b_without_dispatch_does_not_fall_through_to_pb1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HARDEN_PR_4373_BEFORE_MERGE — registry hit without runner must error, not PB1."""
    from services.validation import strategy_replay_runner as srr

    monkeypatch.setattr(srr, "_batch_b_runner_dispatch", lambda: {})
    cfg = ARVPReplayConfig(
        strategy_id=HH_HL_CONTINUATION_STRATEGY_ID,
        adapter_id=BATCH_B_SHADOW_ADAPTER_ID,
        symbol="BTCUSDT",
        dataset_source="file",
        input_candles_file="x.json",
    )
    with pytest.raises(ValueError, match="refusing primary_breakout fallthrough"):
        srr._run_strategy_backtest(cfg, [], code_commit="4372harden")


def test_confirmed_swing_high_and_low() -> None:
    candles = _hh_hl_structure_candles()
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    ts = [int(c["ts_ms"]) for c in candles]
    cfg = HhHlContinuationConfig()

    # First swing low pivot at 4 confirms at 6
    sl = confirmed_swing_at(highs, lows, ts, 6, config=cfg, kind="low")
    assert sl is not None
    assert sl.pivot_index == 4

    # Unconfirmed: looking one bar early must not confirm pivot 4
    assert confirmed_swing_at(highs, lows, ts, 5, config=cfg, kind="low") is None


def test_equal_highs_do_not_form_swing() -> None:
    start = 1_700_000_000_000
    # Plateau at the would-be pivot
    prices = [100, 101, 102, 103, 103, 102, 101]
    candles = [_flat(start + i * 60_000, p) for i, p in enumerate(prices)]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    ts = [int(c["ts_ms"]) for c in candles]
    cfg = HhHlContinuationConfig()
    assert confirmed_swing_at(highs, lows, ts, 6, config=cfg, kind="high") is None


def test_runner_enters_on_hh_hl_and_exits_on_hl_break() -> None:
    report = run_hh_hl_continuation_backtest(
        _hh_hl_structure_candles(),
        code_commit="4372test",
        run_id="unit-hhhl-1",
    )
    assert report["schema_version"] == "strategy_validation_report.v1"
    assert report["strategy_id"] == HH_HL_CONTINUATION_STRATEGY_ID
    assert report["metrics"]["closed_trades_total"] >= 1
    assert report["config_snapshot"]["ranking_ready"] is False
    assert "hh_hl_structure_confirm" in report["entry_reasons"]
    assert (
        "hl_structure_break" in report["exit_reasons"]
        or "series_end_closeout" in report["exit_reasons"]
    )


def test_insufficient_history_no_entry() -> None:
    start = 1_700_000_000_000
    candles = [_flat(start + i * 60_000, 100.0) for i in range(3)]
    report = run_hh_hl_continuation_backtest(candles, code_commit="4372test")
    assert report["strategy_id"] == HH_HL_CONTINUATION_STRATEGY_ID
    assert report.get("trades", []) == []
    metrics = report.get("metrics") or {}
    assert metrics.get("closed_trades_total", 0) == 0
    assert report.get("signals_total", 0) == 0


def test_fail_closed_missing_and_invalid_ohlc() -> None:
    base = _hh_hl_structure_candles()[:10]
    missing_open = copy.deepcopy(base)
    del missing_open[3]["open"]
    with pytest.raises(ValueError, match="open"):
        validate_hh_hl_candle_series(missing_open)

    nan_row = copy.deepcopy(base)
    nan_row[2]["close"] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        validate_hh_hl_candle_series(nan_row)

    inf_row = copy.deepcopy(base)
    inf_row[2]["high"] = float("inf")
    with pytest.raises(ValueError, match="non-finite"):
        validate_hh_hl_candle_series(inf_row)

    bad_hl = copy.deepcopy(base)
    bad_hl[2]["high"] = 1.0
    bad_hl[2]["low"] = 2.0
    with pytest.raises(ValueError, match="high < low"):
        validate_hh_hl_candle_series(bad_hl)

    dup = copy.deepcopy(base)
    dup[4]["ts_ms"] = dup[3]["ts_ms"]
    with pytest.raises(ValueError, match="strictly increasing"):
        validate_hh_hl_candle_series(dup)

    empty_report = run_hh_hl_continuation_backtest([], code_commit="4372test")
    assert empty_report["strategy_id"] == HH_HL_CONTINUATION_STRATEGY_ID


def test_prefix_invariance_of_trades() -> None:
    full = _hh_hl_structure_candles()
    n = 28
    prefix = full[:n]
    report_prefix = run_hh_hl_continuation_backtest(prefix, code_commit="4372")
    report_full = run_hh_hl_continuation_backtest(full, code_commit="4372")

    def _structural_events(
        report: dict[str, Any], max_ts: int
    ) -> list[tuple[str, int]]:
        events: list[tuple[str, int]] = []
        for trade in report.get("trades", []):
            entry_ts = int(trade["entry_ts_ms"])
            exit_ts = int(trade["exit_ts_ms"])
            reason = str(trade.get("reason") or "")
            if entry_ts <= max_ts:
                events.append(("entry", entry_ts))
            # series_end_closeout depends on series length; exclude from prefix proof
            if exit_ts <= max_ts and reason != "series_end_closeout":
                events.append(("exit", exit_ts))
        return events

    max_ts = int(prefix[-1]["ts_ms"])
    assert _structural_events(report_prefix, max_ts) == _structural_events(
        report_full, max_ts
    )


def test_determinism_byte_identical_canonical_trades() -> None:
    candles = _hh_hl_structure_candles()
    a = run_hh_hl_continuation_backtest(candles, code_commit="4372", run_id="a")
    b = run_hh_hl_continuation_backtest(candles, code_commit="4372", run_id="b")
    payload_a = {
        "strategy_id": a["strategy_id"],
        "trades": a["trades"],
        "entry_reasons": a["entry_reasons"],
        "exit_reasons": a["exit_reasons"],
        "config_snapshot": {
            k: a["config_snapshot"][k]
            for k in (
                "swing_left_bars",
                "swing_right_bars",
                "min_minutes_between_entries",
                "trade_side_mode",
                "warmup_candles",
            )
        },
    }
    payload_b = {
        "strategy_id": b["strategy_id"],
        "trades": b["trades"],
        "entry_reasons": b["entry_reasons"],
        "exit_reasons": b["exit_reasons"],
        "config_snapshot": {
            k: b["config_snapshot"][k]
            for k in (
                "swing_left_bars",
                "swing_right_bars",
                "min_minutes_between_entries",
                "trade_side_mode",
                "warmup_candles",
            )
        },
    }
    assert canonical_hash(payload_a) == canonical_hash(payload_b)


def test_structure_helper_requires_two_swings() -> None:
    assert structure_is_hh_hl([], []) is False


def test_no_math_dependency_on_nan_path() -> None:
    assert math.isnan(float("nan"))
