"""Batch-B strategy registry metadata (#4372 slice 1).

Read-only dispatch metadata for Batch-B candidates. Only implemented runners
are marked executable. Identity lock remains in
``docs/contracts/batch_b_funnel_manifest.v1.json``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from core.replay.hh_hl_continuation_common import (
    BATCH_B_SHADOW_ADAPTER_ID,
    HH_HL_CONTINUATION_SPEC_REF,
    HH_HL_CONTINUATION_STRATEGY_ID,
    MIN_MINUTES_BETWEEN_ENTRIES,
    SWING_LEFT_BARS,
    SWING_RIGHT_BARS,
    frozen_hh_hl_parameters,
    hh_hl_warmup_candles,
)

BATCH_B_ID = "batch_b_established_strategy_funnel_v1"
BATCH_B_SOURCE_ISSUE = "#4069"
BATCH_B_PARENT_CONTROL = "#1900"
BATCH_B_IMPLEMENTATION_ISSUE = "#4372"
BATCH_B_MANIFEST_REF = "docs/contracts/batch_b_funnel_manifest.v1.json"
BATCH_B_OWNER_GO_COMMENT_ID = "5196985942"
BATCH_B_BOUND_MAIN_SHA = "279b7100df899276a92386ee83161734811e9e7c"


class ImplementationMode(str, Enum):
    NEW = "NEW"


class ImplementationStatus(str, Enum):
    IMPLEMENTED = "implemented"
    SPEC_REQUIRED = "spec_required"


@dataclass(frozen=True, slots=True)
class BatchBStrategyRecord:
    strategy_id: str
    implementation_mode: ImplementationMode
    implementation_status: ImplementationStatus
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


BATCH_B_STRATEGY_REGISTRY: dict[str, BatchBStrategyRecord] = {
    HH_HL_CONTINUATION_STRATEGY_ID: BatchBStrategyRecord(
        strategy_id=HH_HL_CONTINUATION_STRATEGY_ID,
        implementation_mode=ImplementationMode.NEW,
        implementation_status=ImplementationStatus.IMPLEMENTED,
        adapter_id=None,
        runner_module="services.validation.hh_hl_continuation_backtest_runner",
        parameter_source=HH_HL_CONTINUATION_SPEC_REF,
        contract_ref=HH_HL_CONTINUATION_SPEC_REF,
        frozen_parameters=frozen_hh_hl_parameters(),
        warmup_bars=hh_hl_warmup_candles(),
        direction="long_only",
        data_fields=("open", "high", "low", "close"),
        evidence_class="historical_cross_venue_research",
    ),
}


def batch_b_strategy_ids() -> frozenset[str]:
    return frozenset(BATCH_B_STRATEGY_REGISTRY)


def get_batch_b_strategy(strategy_id: str) -> BatchBStrategyRecord:
    try:
        return BATCH_B_STRATEGY_REGISTRY[strategy_id]
    except KeyError as exc:
        raise KeyError(f"unknown Batch-B strategy_id: {strategy_id}") from exc


def executable_batch_b_strategy_ids() -> frozenset[str]:
    return frozenset(
        strategy_id
        for strategy_id, record in BATCH_B_STRATEGY_REGISTRY.items()
        if record.executable
    )


def assert_batch_b_executable(strategy_id: str) -> BatchBStrategyRecord:
    record = get_batch_b_strategy(strategy_id)
    if not record.executable:
        raise ValueError(f"Batch-B strategy not executable: {strategy_id}")
    return record


def batch_b_shadow_adapter_id() -> str:
    return BATCH_B_SHADOW_ADAPTER_ID


# Touch frozen constants so accidental drift is visible in imports.
_ = (SWING_LEFT_BARS, SWING_RIGHT_BARS, MIN_MINUTES_BETWEEN_ENTRIES)
