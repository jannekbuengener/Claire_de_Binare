"""Restart-safe stop-loss consumer (Issue #4186).

Guarantees enforced here:

- Exactly one exit intent per unique protection event.
- Restart or replay never produces a second intent for the same event.
- A newer protection event (new position, re-armed stop) is never swallowed by
  an older dedup entry, because the event identity covers the position epoch
  and the armed stop.
- Missing, corrupt, unknown, or contradictory state blocks fail-closed.
- A failed sink handoff or a failed finalize is reported as a block, never as a
  silent partial success.

The consumer never raises for operational failures: it returns a blocking
outcome with a stable reason code so the caller can surface it as evidence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from core.safety.stop_loss.contracts import (
    PositionSnapshot,
    PriceObservation,
    StopLossContractError,
    StopLossProtectionEvent,
    StopLossReason,
    StopLossTriggerConfig,
    evaluate_stop_loss_trigger,
)
from core.safety.stop_loss.dedup_state import (
    DedupRecordState,
    StopLossDedupRecord,
    StopLossDedupStateError,
    StopLossDedupStore,
)
from core.safety.stop_loss.exit_intent import (
    ExitIntentSink,
    ExitIntentV1,
    build_exit_intent_v1,
)

logger = logging.getLogger(__name__)


class StopLossConsumeDecision(str, Enum):
    """Outcome classes of one consume cycle."""

    EXIT_INTENT_EMITTED = "EXIT_INTENT_EMITTED"
    DUPLICATE_SUPPRESSED = "DUPLICATE_SUPPRESSED"
    NO_TRIGGER = "NO_TRIGGER"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class StopLossConsumeOutcome:
    """Result of one consume cycle, always carrying a stable reason code."""

    decision: StopLossConsumeDecision
    reason_code: str
    detail: str = ""
    event_id: Optional[str] = None
    intent: Optional[ExitIntentV1] = None

    @property
    def blocked(self) -> bool:
        return self.decision is StopLossConsumeDecision.BLOCKED

    @property
    def emitted(self) -> bool:
        return self.decision is StopLossConsumeDecision.EXIT_INTENT_EMITTED


class StopLossConsumer:
    """Deterministic stop-loss consumer over a persistent dedup store."""

    def __init__(
        self,
        *,
        store: StopLossDedupStore,
        sink: ExitIntentSink,
        config: StopLossTriggerConfig,
        clock_ms: Callable[[], int],
    ) -> None:
        self._store = store
        self._sink = sink
        self._config = config
        self._clock_ms = clock_ms

    def consume(
        self,
        position: PositionSnapshot,
        observation: PriceObservation,
    ) -> StopLossConsumeOutcome:
        """Evaluate one price observation and emit at most one exit intent."""
        now_ms = self._clock_ms()
        trigger = evaluate_stop_loss_trigger(
            position, observation, self._config, now_ms=now_ms
        )

        if trigger.blocked:
            return StopLossConsumeOutcome(
                decision=StopLossConsumeDecision.BLOCKED,
                reason_code=trigger.reason_code,
                detail=trigger.detail,
            )
        if not trigger.triggered:
            return StopLossConsumeOutcome(
                decision=StopLossConsumeDecision.NO_TRIGGER,
                reason_code=trigger.reason_code,
                detail=trigger.detail,
            )

        event = trigger.event
        assert event is not None  # guaranteed by StopLossTriggerDecision.TRIGGERED

        try:
            stored = self._store.load(event.event_id)
        except StopLossDedupStateError as exc:
            return self._blocked(exc.reason, str(exc), event)
        except Exception as exc:  # pragma: no cover - defensive fail-closed path
            return self._blocked(StopLossReason.DEDUP_STATE_CORRUPT, str(exc), event)

        if stored is not None:
            return self._evaluate_stored_record(stored, event)

        return self._emit_exit_intent(event, now_ms=now_ms)

    def _evaluate_stored_record(
        self,
        stored: StopLossDedupRecord,
        event: StopLossProtectionEvent,
    ) -> StopLossConsumeOutcome:
        if stored.fingerprint != event.fingerprint:
            return self._blocked(
                StopLossReason.DEDUP_STATE_CONTRADICTORY,
                f"stored fingerprint {stored.fingerprint} does not match protection "
                f"event fingerprint {event.fingerprint}",
                event,
            )
        if stored.state is DedupRecordState.PREPARED:
            return self._blocked(
                StopLossReason.PREPARE_INCOMPLETE,
                f"dedup record for {event.event_id} is still PREPARED; delivery of a "
                "prior exit intent is unproven, refusing to emit a second one",
                event,
            )
        return StopLossConsumeOutcome(
            decision=StopLossConsumeDecision.DUPLICATE_SUPPRESSED,
            reason_code=StopLossReason.DUPLICATE_SUPPRESSED.value,
            detail=(
                f"protection event {event.event_id} already produced intent "
                f"{stored.intent_id}"
            ),
            event_id=event.event_id,
        )

    def _emit_exit_intent(
        self,
        event: StopLossProtectionEvent,
        *,
        now_ms: int,
    ) -> StopLossConsumeOutcome:
        try:
            intent = build_exit_intent_v1(event, created_at_ms=now_ms)
        except StopLossContractError as exc:
            return self._blocked(StopLossReason.EXIT_INTENT_INVALID, str(exc), event)

        record = StopLossDedupRecord(
            event_id=event.event_id,
            fingerprint=event.fingerprint,
            state=DedupRecordState.PREPARED,
            symbol=event.symbol,
            position_id=event.position_id,
            prepared_at_ms=now_ms,
            intent_id=intent.intent_id,
        )

        # Prepare before emitting: a crash after this point can only lose the
        # intent, never duplicate it.
        try:
            self._store.prepare(record)
        except Exception as exc:
            return self._blocked(StopLossReason.DEDUP_PREPARE_FAILED, str(exc), event)

        try:
            self._sink.accept(intent)
        except Exception as exc:
            logger.error(
                "Stop-loss exit intent sink failed for event %s: %s",
                event.event_id,
                exc,
            )
            return self._blocked(
                StopLossReason.EXIT_INTENT_SINK_FAILED,
                f"exit intent {intent.intent_id} was not accepted: {exc}; dedup record "
                "stays PREPARED and further attempts block",
                event,
            )

        try:
            self._store.finalize(
                StopLossDedupRecord(
                    event_id=record.event_id,
                    fingerprint=record.fingerprint,
                    state=DedupRecordState.FINALIZED,
                    symbol=record.symbol,
                    position_id=record.position_id,
                    prepared_at_ms=record.prepared_at_ms,
                    intent_id=intent.intent_id,
                    finalized_at_ms=now_ms,
                )
            )
        except Exception as exc:
            # The intent was accepted but the state commit failed: report the
            # partial success explicitly instead of claiming a clean emit.
            logger.error(
                "Stop-loss dedup finalize failed after intent %s was accepted: %s",
                intent.intent_id,
                exc,
            )
            return StopLossConsumeOutcome(
                decision=StopLossConsumeDecision.BLOCKED,
                reason_code=StopLossReason.DEDUP_FINALIZE_FAILED.value,
                detail=(
                    f"exit intent {intent.intent_id} was accepted but the dedup state "
                    f"commit failed: {exc}; record stays PREPARED"
                ),
                event_id=event.event_id,
                intent=intent,
            )

        return StopLossConsumeOutcome(
            decision=StopLossConsumeDecision.EXIT_INTENT_EMITTED,
            reason_code=StopLossReason.EXIT_INTENT_EMITTED.value,
            detail=f"exit intent {intent.intent_id} emitted for {event.event_id}",
            event_id=event.event_id,
            intent=intent,
        )

    @staticmethod
    def _blocked(
        reason: StopLossReason,
        detail: str,
        event: Optional[StopLossProtectionEvent] = None,
    ) -> StopLossConsumeOutcome:
        return StopLossConsumeOutcome(
            decision=StopLossConsumeDecision.BLOCKED,
            reason_code=reason.value,
            detail=detail,
            event_id=event.event_id if event is not None else None,
        )
