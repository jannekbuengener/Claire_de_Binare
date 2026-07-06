"""Dispatch tests for Pack-A strategy replay wiring."""

from __future__ import annotations

import pytest

from core.replay.pack_a_breakout_common import (
    BREAKOUT_TREND_FILTER_STRATEGY_ID,
    DONCHIAN_BREAKOUT_STRATEGY_ID,
)
from services.validation.strategy_replay_runner import ARVPReplayConfig


@pytest.mark.unit
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
        input_candles_file="artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json",
        strategy_id=strategy_id,
        symbol="BTCUSDT",
        adapter_id=adapter_id,
        scenario_ids=("baseline", "pessimistic_execution", "feed_gap"),
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
