"""Protective exit intent contract v1 (Issue #4186).

An exit intent is the *only* output of a stop-loss protection event. It is a
reduce-only intent: it can never increase a position and never flip its side.
The intent is not an order and does not reach any productive adapter in this
slice; dispatch stays ``NOT_DISPATCHED`` until a separate proven exit path
exists (#4184 owns the reduce-only execution contract and is parked).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Protocol, runtime_checkable

from core.replay.canonical_json import canonical_hash
from core.safety.stop_loss.contracts import (
    PositionSide,
    StopLossContractError,
    StopLossProtectionEvent,
    StopLossReason,
)

EXIT_INTENT_SCHEMA_VERSION = "cdb-stop-loss-exit-intent/v1"

INTENT_KIND_PROTECTIVE_EXIT = "PROTECTIVE_EXIT"
DISPATCH_STATE_NOT_DISPATCHED = "NOT_DISPATCHED"

_INTENT_ID_PREFIX = "slx"
_INTENT_ID_HASH_LEN = 32

_EXIT_SIDE_FOR_POSITION = {
    PositionSide.LONG: "SELL",
    PositionSide.SHORT: "BUY",
}


@dataclass(frozen=True)
class ExitIntentV1:
    """Reduce-only protective exit intent derived from one protection event."""

    schema_version: str
    intent_id: str
    protection_event_id: str
    trigger_contract_version: str
    symbol: str
    side: str
    quantity: Decimal
    reduce_only: bool
    intent_kind: str
    stop_price: Decimal
    observed_price: Decimal
    position_side: PositionSide
    position_quantity: Decimal
    created_at_ms: int
    dispatch_state: str = DISPATCH_STATE_NOT_DISPATCHED
    productive_adapter_enabled: bool = False

    def to_dict(self) -> dict:
        """Canonical, JSON-serializable representation (decimals as strings)."""
        return {
            "schema_version": self.schema_version,
            "intent_id": self.intent_id,
            "protection_event_id": self.protection_event_id,
            "trigger_contract_version": self.trigger_contract_version,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": str(self.quantity),
            "reduce_only": self.reduce_only,
            "intent_kind": self.intent_kind,
            "stop_price": str(self.stop_price),
            "observed_price": str(self.observed_price),
            "position_side": self.position_side.value,
            "position_quantity": str(self.position_quantity),
            "created_at_ms": self.created_at_ms,
            "dispatch_state": self.dispatch_state,
            "productive_adapter_enabled": self.productive_adapter_enabled,
        }


def build_exit_intent_v1(
    event: StopLossProtectionEvent,
    *,
    created_at_ms: int,
    quantity: Optional[Decimal] = None,
) -> ExitIntentV1:
    """Build the reduce-only exit intent for a protection event.

    Args:
        event: Deterministic protection event from the trigger contract.
        created_at_ms: Wall-clock stamp for the intent (not part of its identity).
        quantity: Optional partial exit quantity; defaults to the full position.

    Raises:
        StopLossContractError: if the intent would increase the position, flip
            its side, or carry a non-positive quantity.
    """
    exit_side = _EXIT_SIDE_FOR_POSITION.get(event.position_side)
    if exit_side is None:
        raise StopLossContractError(
            f"{StopLossReason.EXIT_INTENT_INVALID.value}: no reducing side for "
            f"position side {event.position_side.value}"
        )

    position_quantity = event.position_quantity
    if position_quantity <= 0:
        raise StopLossContractError(
            f"{StopLossReason.EXIT_INTENT_INVALID.value}: position quantity must be "
            f"positive, got {position_quantity}"
        )

    exit_quantity = position_quantity if quantity is None else quantity
    if not isinstance(exit_quantity, Decimal):
        raise StopLossContractError(
            f"{StopLossReason.EXIT_INTENT_INVALID.value}: quantity must be Decimal"
        )
    if exit_quantity <= 0:
        raise StopLossContractError(
            f"{StopLossReason.EXIT_INTENT_INVALID.value}: exit quantity must be "
            f"positive, got {exit_quantity}"
        )
    if exit_quantity > position_quantity:
        raise StopLossContractError(
            f"{StopLossReason.EXIT_INTENT_INVALID.value}: exit quantity "
            f"{exit_quantity} would exceed position quantity {position_quantity} "
            "(position increase / side flip forbidden)"
        )

    intent_identity = {
        "schema_version": EXIT_INTENT_SCHEMA_VERSION,
        "protection_event_id": event.event_id,
        "symbol": event.symbol,
        "side": exit_side,
        "quantity": str(exit_quantity),
    }
    intent_id = (
        f"{_INTENT_ID_PREFIX}-{canonical_hash(intent_identity)[:_INTENT_ID_HASH_LEN]}"
    )

    return ExitIntentV1(
        schema_version=EXIT_INTENT_SCHEMA_VERSION,
        intent_id=intent_id,
        protection_event_id=event.event_id,
        trigger_contract_version=event.contract_version,
        symbol=event.symbol,
        side=exit_side,
        quantity=exit_quantity,
        reduce_only=True,
        intent_kind=INTENT_KIND_PROTECTIVE_EXIT,
        stop_price=event.stop_price,
        observed_price=event.observed_price,
        position_side=event.position_side,
        position_quantity=position_quantity,
        created_at_ms=created_at_ms,
    )


@runtime_checkable
class ExitIntentSink(Protocol):
    """Destination for protective exit intents."""

    def accept(self, intent: ExitIntentV1) -> None:
        """Accept an exit intent or raise to signal a failed handoff."""


class RecordingExitIntentSink:
    """In-memory sink for tests, shadow runs, and mock harnesses."""

    def __init__(self) -> None:
        self.intents: list[ExitIntentV1] = []

    def accept(self, intent: ExitIntentV1) -> None:
        self.intents.append(intent)

    @property
    def intent_ids(self) -> list[str]:
        return [intent.intent_id for intent in self.intents]


class DisabledProductiveExitAdapter:
    """Placeholder for the productive exit path; always refuses.

    Proves that this slice does not activate a productive queue or exchange
    adapter: any attempt to hand an intent to production fails closed.
    """

    def accept(self, intent: ExitIntentV1) -> None:
        raise StopLossContractError(
            f"{StopLossReason.PRODUCTIVE_ADAPTER_DISABLED.value}: intent "
            f"{intent.intent_id} must not reach a productive exit adapter in this slice"
        )
