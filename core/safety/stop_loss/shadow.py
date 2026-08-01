"""Mock/shadow harness for the stop-loss consumer (Issue #4186).

Replays a candle-shaped price series through the consumer and reports every
decision. The harness is deterministic and container-free: no Redis, no
Postgres, no exchange adapter. It proves the path from price trigger to exit
intent, and it can simulate a consumer restart mid-series by rebuilding the
consumer against the same persistent dedup state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional, Sequence

from core.safety.stop_loss.consumer import (
    StopLossConsumeDecision,
    StopLossConsumeOutcome,
    StopLossConsumer,
)
from core.safety.stop_loss.contracts import (
    PositionSnapshot,
    PriceObservation,
    StopLossTriggerConfig,
)
from core.safety.stop_loss.dedup_state import StopLossDedupStore
from core.safety.stop_loss.exit_intent import ExitIntentSink

SHADOW_REPORT_SCHEMA_VERSION = "cdb-stop-loss-shadow-report/v1"


@dataclass(frozen=True)
class ShadowStep:
    """One replayed observation and its consumer outcome."""

    index: int
    close: str
    observed_at_ms: int
    decision: str
    reason_code: str
    event_id: Optional[str]
    intent_id: Optional[str]
    restarted_before_step: bool = False

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "close": self.close,
            "observed_at_ms": self.observed_at_ms,
            "decision": self.decision,
            "reason_code": self.reason_code,
            "event_id": self.event_id,
            "intent_id": self.intent_id,
            "restarted_before_step": self.restarted_before_step,
        }


@dataclass
class ShadowRunReport:
    """Aggregate result of one shadow replay."""

    schema_version: str = SHADOW_REPORT_SCHEMA_VERSION
    symbol: str = ""
    steps: list[ShadowStep] = field(default_factory=list)
    emitted_intent_ids: list[str] = field(default_factory=list)
    productive_adapter_enabled: bool = False

    @property
    def emitted_count(self) -> int:
        return len(self.emitted_intent_ids)

    def decision_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for step in self.steps:
            counts[step.decision] = counts.get(step.decision, 0) + 1
        return counts

    def reason_codes(self) -> list[str]:
        seen: list[str] = []
        for step in self.steps:
            if step.reason_code not in seen:
                seen.append(step.reason_code)
        return seen

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "symbol": self.symbol,
            "steps": [step.to_dict() for step in self.steps],
            "emitted_intent_ids": list(self.emitted_intent_ids),
            "emitted_intent_count": self.emitted_count,
            "unique_emitted_intent_count": len(set(self.emitted_intent_ids)),
            "decision_counts": self.decision_counts(),
            "reason_codes": self.reason_codes(),
            "productive_adapter_enabled": self.productive_adapter_enabled,
        }


def candle_observations(
    candles: Iterable[dict],
    *,
    symbol: str,
    source: str = "shadow.candles_1m",
) -> list[PriceObservation]:
    """Convert candle-stream shaped dicts into price observations.

    Expects the candle payload contract of ``services/candles/models.py``:
    ``ts`` in seconds and ``close`` as a decimal string.
    """
    observations: list[PriceObservation] = []
    for candle in candles:
        observations.append(
            PriceObservation(
                symbol=symbol,
                price=str(candle["close"]),
                observed_at_ms=int(candle["ts"]) * 1000,
                source=source,
            )
        )
    return observations


def run_stop_loss_shadow(
    *,
    position: PositionSnapshot,
    observations: Sequence[PriceObservation],
    config: StopLossTriggerConfig,
    store: StopLossDedupStore,
    sink: ExitIntentSink,
    now_ms_for: Callable[[PriceObservation], int] | None = None,
    restart_before_indices: Sequence[int] = (),
) -> ShadowRunReport:
    """Replay observations through the consumer and collect a shadow report.

    Args:
        restart_before_indices: Step indices at which a fresh consumer instance
            is built against the same store, simulating a process restart.
    """
    report = ShadowRunReport(symbol=position.symbol)
    restart_points = set(restart_before_indices)
    resolve_now = now_ms_for or (lambda obs: int(obs.observed_at_ms or 0))

    # The consumer reads the clock during consume(), so the harness advances a
    # single cursor instead of rebuilding the consumer for every observation.
    cursor: dict[str, PriceObservation] = {}

    def clock_ms() -> int:
        return resolve_now(cursor["observation"])

    def build_consumer() -> StopLossConsumer:
        return StopLossConsumer(
            store=store, sink=sink, config=config, clock_ms=clock_ms
        )

    consumer = build_consumer()
    for index, obs in enumerate(observations):
        if index in restart_points:
            consumer = build_consumer()
        cursor["observation"] = obs

        outcome: StopLossConsumeOutcome = consumer.consume(position, obs)
        if outcome.decision is StopLossConsumeDecision.EXIT_INTENT_EMITTED:
            assert outcome.intent is not None
            report.emitted_intent_ids.append(outcome.intent.intent_id)

        report.steps.append(
            ShadowStep(
                index=index,
                close=str(obs.price),
                observed_at_ms=int(obs.observed_at_ms or 0),
                decision=outcome.decision.value,
                reason_code=outcome.reason_code,
                event_id=outcome.event_id,
                intent_id=outcome.intent.intent_id if outcome.intent else None,
                restarted_before_step=index in restart_points,
            )
        )

    return report
