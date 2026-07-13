"""Dispatch tests for Pack-A and Batch-A strategy replay wiring."""

from __future__ import annotations

import pytest

from core.replay.batch_a_strategy_registry import batch_a_strategy_ids
from core.replay.pack_a_breakout_common import (
    BREAKOUT_TREND_FILTER_STRATEGY_ID,
    DONCHIAN_BREAKOUT_STRATEGY_ID,
)
from services.validation.strategy_replay_runner import (
    ARVPReplayConfig,
    _BATCH_A_SHADOW_ADAPTER_ID,
)

pytestmark = pytest.mark.unit

_INPUT_CANDLES = (
    "artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json"
)


@pytest.mark.parametrize(
    ("strategy_id", "adapter_id"),
    [
        ("primary_breakout_v1", "primary_breakout_runner_v1"),
        (DONCHIAN_BREAKOUT_STRATEGY_ID, "donchian_breakout_runner_v1"),
        (BREAKOUT_TREND_FILTER_STRATEGY_ID, "breakout_trend_filter_runner_v1"),
    ],
)
def test_pack_a_strategy_ids_validate(strategy_id: str, adapter_id: str) -> None:
    config = ARVPReplayConfig(
        dataset_source="file",
        input_candles_file=_INPUT_CANDLES,
        strategy_id=strategy_id,
        symbol="BTCUSDT",
        adapter_id=adapter_id,
        scenario_ids=("baseline", "pessimistic_execution", "feed_gap"),
    )
    config.validate()


@pytest.mark.parametrize("strategy_id", sorted(batch_a_strategy_ids()))
def test_batch_a_strategy_ids_validate(strategy_id: str) -> None:
    adapter_id = (
        "range_mean_reversion_runner_v1"
        if strategy_id == "range_mean_reversion_v1"
        else "momentum_capture_runner_v1"
        if strategy_id == "momentum_capture_v1"
        else _BATCH_A_SHADOW_ADAPTER_ID
    )
    config = ARVPReplayConfig(
        dataset_source="file",
        input_candles_file=_INPUT_CANDLES,
        strategy_id=strategy_id,
        symbol="BTCUSDT",
        adapter_id=adapter_id,
        scenario_ids=("baseline", "pessimistic_execution"),
    )
    config.validate()


@pytest.mark.parametrize(
    ("strategy_id", "adapter_id", "binance_window_id"),
    [
        ("range_mean_reversion_v1", "range_mean_reversion_runner_v1", "binance_1m_month_2021_01"),
        ("momentum_capture_v1", "momentum_capture_runner_v1", "binance_1m_month_2021_01"),
    ],
)
def test_batch_a_binance_window_dataset_validates(
    strategy_id: str,
    adapter_id: str,
    binance_window_id: str,
) -> None:
    config = ARVPReplayConfig(
        dataset_source="binance_window",
        binance_window_id=binance_window_id,
        strategy_id=strategy_id,
        symbol="BTCUSDT",
        adapter_id=adapter_id,
        scenario_ids=("baseline",),
    )
    config.validate()


@pytest.mark.unit
def test_pack_a_rejects_unknown_adapter() -> None:
    config = ARVPReplayConfig(
        dataset_source="file",
        input_candles_file="dataset.json",
        strategy_id=DONCHIAN_BREAKOUT_STRATEGY_ID,
        symbol="BTCUSDT",
        adapter_id="unknown_adapter_v1",
    )
    with pytest.raises(ValueError, match="unsupported adapter_id"):
        config.validate()
