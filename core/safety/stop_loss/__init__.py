"""Stop-loss protection components (Issue #4186).

Composition: price trigger contract -> deterministic protection event ->
persistent dedup state -> exactly one reduce-only exit intent.

This package does not activate a productive queue, exchange adapter, or exit
execution path. The canonical protection status stays ``UNAVAILABLE`` until the
evidence ledger in ``core.safety.stop_loss_protection`` is complete.
"""

from core.safety.stop_loss.consumer import (
    StopLossConsumeDecision,
    StopLossConsumeOutcome,
    StopLossConsumer,
)
from core.safety.stop_loss.contracts import (
    STOP_LOSS_TRIGGER_CONTRACT_VERSION,
    PositionSide,
    PositionSnapshot,
    PriceObservation,
    StopLossContractError,
    StopLossProtectionEvent,
    StopLossReason,
    StopLossTriggerConfig,
    StopLossTriggerDecision,
    StopLossTriggerResult,
    compute_stop_price,
    evaluate_stop_loss_trigger,
)
from core.safety.stop_loss.dedup_state import (
    DEDUP_STATE_SCHEMA_VERSION,
    DedupRecordState,
    FileStopLossDedupStore,
    InMemoryStopLossDedupStore,
    StopLossDedupRecord,
    StopLossDedupStateError,
    StopLossDedupStore,
)
from core.safety.stop_loss.exit_intent import (
    EXIT_INTENT_SCHEMA_VERSION,
    DisabledProductiveExitAdapter,
    ExitIntentSink,
    ExitIntentV1,
    RecordingExitIntentSink,
    build_exit_intent_v1,
)
from core.safety.stop_loss.shadow import (
    SHADOW_REPORT_SCHEMA_VERSION,
    ShadowRunReport,
    ShadowStep,
    candle_observations,
    run_stop_loss_shadow,
)

__all__ = [
    "DEDUP_STATE_SCHEMA_VERSION",
    "EXIT_INTENT_SCHEMA_VERSION",
    "SHADOW_REPORT_SCHEMA_VERSION",
    "STOP_LOSS_TRIGGER_CONTRACT_VERSION",
    "DedupRecordState",
    "DisabledProductiveExitAdapter",
    "ExitIntentSink",
    "ExitIntentV1",
    "FileStopLossDedupStore",
    "InMemoryStopLossDedupStore",
    "PositionSide",
    "PositionSnapshot",
    "PriceObservation",
    "RecordingExitIntentSink",
    "ShadowRunReport",
    "ShadowStep",
    "StopLossConsumeDecision",
    "StopLossConsumeOutcome",
    "StopLossConsumer",
    "StopLossContractError",
    "StopLossDedupRecord",
    "StopLossDedupStateError",
    "StopLossDedupStore",
    "StopLossProtectionEvent",
    "StopLossReason",
    "StopLossTriggerConfig",
    "StopLossTriggerDecision",
    "StopLossTriggerResult",
    "build_exit_intent_v1",
    "candle_observations",
    "compute_stop_price",
    "evaluate_stop_loss_trigger",
    "run_stop_loss_shadow",
]
