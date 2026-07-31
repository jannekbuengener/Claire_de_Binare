"""Fail-closed reduce-only execution contract.

The contract uses signed base-asset quantities:

* positive position: long
* negative position: short
* zero: no position

It is deliberately venue-neutral. Persistent preparation/finalization lives in
the execution database layer; this module owns the deterministic invariants.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

REDUCE_ONLY_POSITION_UNKNOWN = "REDUCE_ONLY_POSITION_UNKNOWN"
REDUCE_ONLY_NO_POSITION = "REDUCE_ONLY_NO_POSITION"
REDUCE_ONLY_INVALID_QUANTITY = "REDUCE_ONLY_INVALID_QUANTITY"
REDUCE_ONLY_QUANTITY_CLAMPED = "REDUCE_ONLY_QUANTITY_CLAMPED"
REDUCE_ONLY_SIDE_MISMATCH = "REDUCE_ONLY_SIDE_MISMATCH"
REDUCE_ONLY_REJECTED = "REDUCE_ONLY_REJECTED"
REDUCE_ONLY_PARTIAL_FILL = "REDUCE_ONLY_PARTIAL_FILL"
REDUCE_ONLY_DUPLICATE_RESULT = "REDUCE_ONLY_DUPLICATE_RESULT"
REDUCE_ONLY_CONCURRENT_CLAIM_BLOCKED = "REDUCE_ONLY_CONCURRENT_CLAIM_BLOCKED"
REDUCE_ONLY_POSITION_INCREASE_BLOCKED = "REDUCE_ONLY_POSITION_INCREASE_BLOCKED"
REDUCE_ONLY_FILLED = "REDUCE_ONLY_FILLED"
REDUCE_ONLY_READY = "REDUCE_ONLY_READY"


@dataclass(frozen=True, slots=True)
class ReduceOnlyPreparation:
    """Decision made before an adapter may receive a reduce-only order."""

    allowed: bool
    position_before: Decimal | None
    requested_quantity: Decimal
    submitted_quantity: Decimal
    side: str
    reason_code: str


@dataclass(frozen=True, slots=True)
class ReduceOnlyOutcome:
    """Deterministic result of applying one adapter outcome at most once."""

    applied: bool
    position_after: Decimal
    remaining_position_quantity: Decimal
    filled_quantity: Decimal
    reason_code: str
    position_increase_observed: bool
    side_flip_observed: bool


def _decimal(value: object) -> Decimal:
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("invalid decimal") from exc


def _valid_positive(value: Decimal) -> bool:
    return value.is_finite() and value > 0


def _side_matches(position: Decimal, side: str) -> bool:
    normalized = str(side).upper()
    return (position > 0 and normalized == "SELL") or (
        position < 0 and normalized == "BUY"
    )


def prepare_reduce_only(
    *,
    position_before: Decimal | None,
    side: str,
    requested_quantity: Decimal,
    reserved_quantity: Decimal = Decimal("0"),
) -> ReduceOnlyPreparation:
    """Validate and clamp a reduce-only request before adapter submission."""

    normalized_side = str(side).upper()
    try:
        requested = _decimal(requested_quantity)
        reserved = _decimal(reserved_quantity)
    except ValueError:
        requested = Decimal("0")
        reserved = Decimal("0")

    if not _valid_positive(requested) or not reserved.is_finite() or reserved < 0:
        return ReduceOnlyPreparation(
            allowed=False,
            position_before=position_before,
            requested_quantity=requested,
            submitted_quantity=Decimal("0"),
            side=normalized_side,
            reason_code=REDUCE_ONLY_INVALID_QUANTITY,
        )

    if position_before is None:
        return ReduceOnlyPreparation(
            allowed=False,
            position_before=None,
            requested_quantity=requested,
            submitted_quantity=Decimal("0"),
            side=normalized_side,
            reason_code=REDUCE_ONLY_POSITION_UNKNOWN,
        )

    try:
        position = _decimal(position_before)
    except ValueError:
        position = Decimal("NaN")
    if not position.is_finite():
        return ReduceOnlyPreparation(
            allowed=False,
            position_before=None,
            requested_quantity=requested,
            submitted_quantity=Decimal("0"),
            side=normalized_side,
            reason_code=REDUCE_ONLY_POSITION_UNKNOWN,
        )
    if position == 0:
        return ReduceOnlyPreparation(
            allowed=False,
            position_before=position,
            requested_quantity=requested,
            submitted_quantity=Decimal("0"),
            side=normalized_side,
            reason_code=REDUCE_ONLY_NO_POSITION,
        )
    if reserved > 0:
        return ReduceOnlyPreparation(
            allowed=False,
            position_before=position,
            requested_quantity=requested,
            submitted_quantity=Decimal("0"),
            side=normalized_side,
            reason_code=REDUCE_ONLY_CONCURRENT_CLAIM_BLOCKED,
        )
    if not _side_matches(position, normalized_side):
        return ReduceOnlyPreparation(
            allowed=False,
            position_before=position,
            requested_quantity=requested,
            submitted_quantity=Decimal("0"),
            side=normalized_side,
            reason_code=REDUCE_ONLY_SIDE_MISMATCH,
        )

    available = max(Decimal("0"), abs(position) - reserved)
    if available == 0:
        return ReduceOnlyPreparation(
            allowed=False,
            position_before=position,
            requested_quantity=requested,
            submitted_quantity=Decimal("0"),
            side=normalized_side,
            reason_code=REDUCE_ONLY_NO_POSITION,
        )

    submitted = min(requested, available)
    reason_code = (
        REDUCE_ONLY_QUANTITY_CLAMPED if submitted < requested else REDUCE_ONLY_READY
    )
    return ReduceOnlyPreparation(
        allowed=True,
        position_before=position,
        requested_quantity=requested,
        submitted_quantity=submitted,
        side=normalized_side,
        reason_code=reason_code,
    )


def apply_reduce_only_result(
    preparation: ReduceOnlyPreparation,
    *,
    status: str,
    filled_quantity: Decimal,
    already_applied: bool = False,
    persisted_position: Decimal | None = None,
) -> ReduceOnlyOutcome:
    """Apply one result while enforcing non-increase and no-side-flip."""

    before = preparation.position_before
    if before is None:
        before = Decimal("0")

    if already_applied:
        after = before if persisted_position is None else _decimal(persisted_position)
        return ReduceOnlyOutcome(
            applied=False,
            position_after=after,
            remaining_position_quantity=abs(after),
            filled_quantity=Decimal("0"),
            reason_code=REDUCE_ONLY_DUPLICATE_RESULT,
            position_increase_observed=abs(after) > abs(before),
            side_flip_observed=before * after < 0,
        )

    normalized_status = str(status).upper()
    try:
        filled = _decimal(filled_quantity)
    except ValueError:
        filled = Decimal("NaN")

    if normalized_status in {"REJECTED", "FAILED", "CANCELLED", "ERROR"}:
        if not filled.is_finite() or filled != 0:
            return ReduceOnlyOutcome(
                applied=False,
                position_after=before,
                remaining_position_quantity=abs(before),
                filled_quantity=Decimal("0"),
                reason_code=REDUCE_ONLY_POSITION_INCREASE_BLOCKED,
                position_increase_observed=False,
                side_flip_observed=False,
            )
        return ReduceOnlyOutcome(
            applied=False,
            position_after=before,
            remaining_position_quantity=abs(before),
            filled_quantity=Decimal("0"),
            reason_code=REDUCE_ONLY_REJECTED,
            position_increase_observed=False,
            side_flip_observed=False,
        )

    if normalized_status not in {"FILLED", "PARTIALLY_FILLED"}:
        return ReduceOnlyOutcome(
            applied=False,
            position_after=before,
            remaining_position_quantity=abs(before),
            filled_quantity=Decimal("0"),
            reason_code=REDUCE_ONLY_POSITION_INCREASE_BLOCKED,
            position_increase_observed=False,
            side_flip_observed=False,
        )

    if (
        not filled.is_finite()
        or filled < 0
        or filled > preparation.submitted_quantity
        or not preparation.allowed
    ):
        return ReduceOnlyOutcome(
            applied=False,
            position_after=before,
            remaining_position_quantity=abs(before),
            filled_quantity=Decimal("0"),
            reason_code=REDUCE_ONLY_POSITION_INCREASE_BLOCKED,
            position_increase_observed=False,
            side_flip_observed=False,
        )

    delta = filled if preparation.side == "BUY" else -filled
    after = before + delta
    position_increase = abs(after) > abs(before)
    side_flip = before * after < 0
    if position_increase or side_flip:
        return ReduceOnlyOutcome(
            applied=False,
            position_after=before,
            remaining_position_quantity=abs(before),
            filled_quantity=Decimal("0"),
            reason_code=REDUCE_ONLY_POSITION_INCREASE_BLOCKED,
            position_increase_observed=position_increase,
            side_flip_observed=side_flip,
        )

    partial = filled < preparation.submitted_quantity
    return ReduceOnlyOutcome(
        applied=filled > 0,
        position_after=after,
        remaining_position_quantity=abs(after),
        filled_quantity=filled,
        reason_code=REDUCE_ONLY_PARTIAL_FILL if partial else REDUCE_ONLY_FILLED,
        position_increase_observed=False,
        side_flip_observed=False,
    )
