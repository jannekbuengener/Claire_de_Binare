"""Batch-A strategy registry metadata (#4031 slice 2a).

Read-only dispatch metadata for the ten ``BATCH_A_LOCKED`` candidates. Only
implemented runners are marked executable; later slices register new runners.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from core.replay.historical_bridge import (
    MOMENTUM_CAPTURE_STRATEGY_ID,
    PRIMARY_BREAKOUT_STRATEGY_ID,
    RANGE_MEAN_REVERSION_STRATEGY_ID,
)
from core.replay.pack_a_breakout_common import (
    BREAKOUT_TREND_FILTER_STRATEGY_ID,
    DONCHIAN_BREAKOUT_STRATEGY_ID,
)

BATCH_A_ID = "batch_a_established_strategy_funnel_v1"
BATCH_A_SOURCE_ISSUE = "#4030"
BATCH_A_PARENT_CONTROL = "#4029"
BATCH_A_MANIFEST_REF = "docs/contracts/batch_a_funnel_manifest.v1.json"

# Prior #3990 campaign — explicitly excluded from Batch A.
ALREADY_TESTED_STRATEGY_IDS: frozenset[str] = frozenset(
    {
        PRIMARY_BREAKOUT_STRATEGY_ID,
        DONCHIAN_BREAKOUT_STRATEGY_ID,
        BREAKOUT_TREND_FILTER_STRATEGY_ID,
    }
)


class ImplementationMode(str, Enum):
    EXTEND = "EXTEND"
    NEW = "NEW"
    REUSE_RESCREEN_CROSS_VENUE_WITH_PRIOR_NEGATIVE_EVIDENCE = (
        "REUSE_RESCREEN_CROSS_VENUE_WITH_PRIOR_NEGATIVE_EVIDENCE"
    )


class ImplementationStatus(str, Enum):
    IMPLEMENTED = "implemented"
    IMPLEMENTATION_PENDING = "implementation_pending"


@dataclass(frozen=True, slots=True)
class BatchAStrategyRecord:
    strategy_id: str
    implementation_mode: ImplementationMode
    implementation_status: ImplementationStatus
    later_slice: str
    adapter_id: str | None
    runner_module: str | None
    parameter_source: str
    frozen_parameters: Mapping[str, Any]
    warmup_bars: int | None
    direction: str
    data_fields: tuple[str, ...]
    evidence_class: str
    contract_ref: str | None = None

    @property
    def executable(self) -> bool:
        return self.implementation_status == ImplementationStatus.IMPLEMENTED


BATCH_A_STRATEGY_REGISTRY: dict[str, BatchAStrategyRecord] = {
    "breakout_volatility_filter_v1": BatchAStrategyRecord(
        strategy_id="breakout_volatility_filter_v1",
        implementation_mode=ImplementationMode.EXTEND,
        implementation_status=ImplementationStatus.IMPLEMENTATION_PENDING,
        later_slice="2b",
        adapter_id=None,
        runner_module=(
            "services.validation.breakout_volatility_filter_backtest_runner"
        ),
        parameter_source="docs/evidence/arvp_pack_a_breakout_baseline_spec_3748.md §7.4",
        frozen_parameters={
            "entry_channel_bars": 20,
            "exit_channel_bars": 10,
            "atr_period": 14,
            "vol_floor": 0.0003,
            "vol_ceiling": 0.0030,
            "min_minutes_between_entries": 30,
            "trade_side_mode": "long_only",
        },
        warmup_bars=34,
        direction="long_only",
        data_fields=("open", "high", "low", "close", "volume"),
        evidence_class="historical_cross_venue_research",
    ),
    "volatility_breakout_v1": BatchAStrategyRecord(
        strategy_id="volatility_breakout_v1",
        implementation_mode=ImplementationMode.NEW,
        implementation_status=ImplementationStatus.IMPLEMENTATION_PENDING,
        later_slice="2b",
        adapter_id=None,
        runner_module="services.validation.volatility_breakout_backtest_runner",
        parameter_source="docs/evidence/arvp_pack_a_breakout_baseline_spec_3748.md §7.5",
        frozen_parameters={
            "breakout_lookback": 20,
            "exit_lookback": 10,
            "atr_period": 14,
            "expansion_lag": 5,
            "expansion_multiplier": 1.15,
            "min_minutes_between_entries": 30,
        },
        warmup_bars=25,
        direction="long_only",
        data_fields=("open", "high", "low", "close"),
        evidence_class="historical_cross_venue_research",
    ),
    "ema_trend_follow_v1": BatchAStrategyRecord(
        strategy_id="ema_trend_follow_v1",
        implementation_mode=ImplementationMode.NEW,
        implementation_status=ImplementationStatus.IMPLEMENTATION_PENDING,
        later_slice="2c",
        adapter_id=None,
        runner_module="services.validation.ema_trend_follow_backtest_runner",
        parameter_source="core/indicators/trend.py (canonical defaults)",
        frozen_parameters={
            "fast_ema_period": 20,
            "slow_ema_period": 50,
            "min_minutes_between_entries": 60,
        },
        warmup_bars=50,
        direction="long_only",
        data_fields=("open", "high", "low", "close"),
        evidence_class="historical_cross_venue_research",
    ),
    "ma_crossover_v1": BatchAStrategyRecord(
        strategy_id="ma_crossover_v1",
        implementation_mode=ImplementationMode.NEW,
        implementation_status=ImplementationStatus.IMPLEMENTATION_PENDING,
        later_slice="2c",
        adapter_id=None,
        runner_module="services.validation.ma_crossover_backtest_runner",
        parameter_source="canonical SMA defaults",
        frozen_parameters={
            "fast_sma_period": 20,
            "slow_sma_period": 50,
            "min_minutes_between_entries": 60,
        },
        warmup_bars=50,
        direction="long_only",
        data_fields=("open", "high", "low", "close"),
        evidence_class="historical_cross_venue_research",
    ),
    RANGE_MEAN_REVERSION_STRATEGY_ID: BatchAStrategyRecord(
        strategy_id=RANGE_MEAN_REVERSION_STRATEGY_ID,
        implementation_mode=(
            ImplementationMode.REUSE_RESCREEN_CROSS_VENUE_WITH_PRIOR_NEGATIVE_EVIDENCE
        ),
        implementation_status=ImplementationStatus.IMPLEMENTED,
        later_slice="2d",
        adapter_id="range_mean_reversion_runner_v1",
        runner_module="services.validation.rmr_backtest_runner",
        parameter_source=(
            "docs/evidence/profitability_candidate_range_mean_reversion_v1_3157.json"
        ),
        contract_ref=(
            "docs/evidence/profitability_candidate_range_mean_reversion_v1_3157.json"
        ),
        frozen_parameters={
            "zscore_lookback_periods": 20,
            "entry_zscore_threshold": 2.0,
            "exit_zscore_threshold": 0.0,
            "atr_period": 14,
            "atr_stop_multiplier": 1.5,
            "cooldown_minutes": 60,
            "position_sizing_pct": 0.01,
        },
        warmup_bars=240,
        direction="long_only",
        data_fields=("open", "high", "low", "close", "regime_id"),
        evidence_class="historical_cross_venue_research",
    ),
    "bollinger_squeeze_breakout_v1": BatchAStrategyRecord(
        strategy_id="bollinger_squeeze_breakout_v1",
        implementation_mode=ImplementationMode.NEW,
        implementation_status=ImplementationStatus.IMPLEMENTATION_PENDING,
        later_slice="2b",
        adapter_id=None,
        runner_module=(
            "services.validation.bollinger_squeeze_breakout_backtest_runner"
        ),
        parameter_source="Bollinger canonical (20/2.0) + neutral squeeze constants",
        frozen_parameters={
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "squeeze_threshold": 0.015,
            "squeeze_bars_min": 5,
            "expansion_ceiling": 0.04,
            "min_minutes_between_entries": 60,
        },
        warmup_bars=20,
        direction="long_only",
        data_fields=("open", "high", "low", "close"),
        evidence_class="historical_cross_venue_research",
    ),
    "roc_breakout_confirm_v1": BatchAStrategyRecord(
        strategy_id="roc_breakout_confirm_v1",
        implementation_mode=ImplementationMode.NEW,
        implementation_status=ImplementationStatus.IMPLEMENTATION_PENDING,
        later_slice="2d",
        adapter_id=None,
        runner_module="services.validation.roc_breakout_confirm_backtest_runner",
        parameter_source="ROC period 12 canonical; thresholds neutral",
        frozen_parameters={
            "breakout_lookback": 20,
            "exit_lookback": 10,
            "roc_period": 12,
            "roc_entry_threshold": 0.005,
            "roc_exit_threshold": 0.0,
            "min_minutes_between_entries": 30,
        },
        warmup_bars=20,
        direction="long_only",
        data_fields=("open", "high", "low", "close"),
        evidence_class="historical_cross_venue_research",
    ),
    "opening_range_breakout_v1": BatchAStrategyRecord(
        strategy_id="opening_range_breakout_v1",
        implementation_mode=ImplementationMode.NEW,
        implementation_status=ImplementationStatus.IMPLEMENTATION_PENDING,
        later_slice="2c",
        adapter_id=None,
        runner_module="services.validation.opening_range_breakout_backtest_runner",
        parameter_source="WP1 frozen neutral UTC boundary",
        frozen_parameters={
            "or_start_utc": "00:00",
            "or_end_utc": "01:00",
            "trade_end_utc": "20:00",
            "min_minutes_between_entries": 1440,
        },
        warmup_bars=60,
        direction="long_only",
        data_fields=("open", "high", "low", "close", "timestamp_ms"),
        evidence_class="historical_cross_venue_research",
    ),
    "atr_expansion_v1": BatchAStrategyRecord(
        strategy_id="atr_expansion_v1",
        implementation_mode=ImplementationMode.NEW,
        implementation_status=ImplementationStatus.IMPLEMENTATION_PENDING,
        later_slice="2b",
        adapter_id=None,
        runner_module="services.validation.atr_expansion_backtest_runner",
        parameter_source="ATR period canonical; ratio thresholds neutral",
        frozen_parameters={
            "atr_period": 14,
            "atr_ratio_threshold": 0.0025,
            "atr_ratio_exit": 0.0018,
            "sma_period": 20,
            "min_minutes_between_entries": 60,
        },
        warmup_bars=50,
        direction="long_only",
        data_fields=("open", "high", "low", "close"),
        evidence_class="historical_cross_venue_research",
    ),
    MOMENTUM_CAPTURE_STRATEGY_ID: BatchAStrategyRecord(
        strategy_id=MOMENTUM_CAPTURE_STRATEGY_ID,
        implementation_mode=(
            ImplementationMode.REUSE_RESCREEN_CROSS_VENUE_WITH_PRIOR_NEGATIVE_EVIDENCE
        ),
        implementation_status=ImplementationStatus.IMPLEMENTED,
        later_slice="2d",
        adapter_id="momentum_capture_runner_v1",
        runner_module="services.validation.momentum_backtest_runner",
        parameter_source=(
            "docs/evidence/profitability_candidate_momentum_capture_v1_3166.json"
        ),
        contract_ref=(
            "docs/evidence/profitability_candidate_momentum_capture_v1_3166.json"
        ),
        frozen_parameters={
            "directional_candle_atr_multiple": 1.0,
            "exit_atr_contraction_multiple": 0.6,
            "exit_trailing_stop_atr_multiple": 0.5,
            "max_hold_bars": 240,
            "cooldown_minutes": 60,
            "position_sizing_pct": 0.01,
            "atr_period": 14,
        },
        warmup_bars=240,
        direction="long_only",
        data_fields=("open", "high", "low", "close", "regime_id"),
        evidence_class="historical_cross_venue_research",
    ),
}


def batch_a_strategy_ids() -> tuple[str, ...]:
    return tuple(BATCH_A_STRATEGY_REGISTRY.keys())


def get_batch_a_strategy(strategy_id: str) -> BatchAStrategyRecord:
    try:
        return BATCH_A_STRATEGY_REGISTRY[strategy_id]
    except KeyError as exc:
        raise KeyError(f"Unknown Batch-A strategy_id: {strategy_id!r}") from exc


def executable_batch_a_strategy_ids() -> frozenset[str]:
    return frozenset(
        record.strategy_id
        for record in BATCH_A_STRATEGY_REGISTRY.values()
        if record.executable
    )


def pending_batch_a_strategy_ids() -> frozenset[str]:
    return frozenset(
        record.strategy_id
        for record in BATCH_A_STRATEGY_REGISTRY.values()
        if record.implementation_status == ImplementationStatus.IMPLEMENTATION_PENDING
    )


def assert_batch_a_executable(strategy_id: str) -> BatchAStrategyRecord:
    record = get_batch_a_strategy(strategy_id)
    if not record.executable:
        raise ValueError(
            f"strategy_id {strategy_id!r} is implementation_pending "
            f"(later slice {record.later_slice})"
        )
    return record
