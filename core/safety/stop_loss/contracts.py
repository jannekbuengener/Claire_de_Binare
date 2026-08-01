"""Stop-loss price trigger contract v1 (Issue #4186).

Deterministic, fail-closed evaluation of a protective stop-loss trigger.

Design boundaries:
- Monetary and quantity inputs are ``Decimal``/``int``/``str`` only; ``float``
  is rejected on the protection path (no-float rule, CDB canon).
- Any missing, unknown, or contradictory position/price input BLOCKS. A block is
  never reported as "no trigger".
- A protection event identity is derived only from the *protection situation*
  (position identity + armed stop), never from the observing tick. Repeated
  ticks below the same stop therefore map to exactly one protection event,
  while a new position or a re-armed stop yields a new protection event.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_UP
from enum import Enum
from typing import Optional

from core.replay.canonical_json import canonical_hash

STOP_LOSS_TRIGGER_CONTRACT_VERSION = "cdb-stop-loss-trigger/v1"

# Quantization mirrors core/contracts/decision_contract_v1.py money/ratio grids.
_MONEY_Q = Decimal("0.00000001")
_RATIO_Q = Decimal("0.000001")
_QTY_Q = Decimal("0.00000001")

_EVENT_ID_PREFIX = "slp"
_EVENT_ID_HASH_LEN = 32


class StopLossContractError(ValueError):
    """Raised when a stop-loss contract invariant is violated."""


class PositionSide(str, Enum):
    """Protection-relevant position side."""

    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"
    UNKNOWN = "UNKNOWN"


class StopLossTriggerDecision(str, Enum):
    """Outcome classes of a trigger evaluation."""

    TRIGGERED = "TRIGGERED"
    NO_TRIGGER = "NO_TRIGGER"
    BLOCKED = "BLOCKED"


class StopLossReason(str, Enum):
    """Stable reason codes for trigger, dedup, and consumer outcomes."""

    # Trigger outcomes
    TRIGGERED = "STOP_LOSS_TRIGGERED"
    NO_TRIGGER_PRICE_ABOVE_STOP = "STOP_LOSS_NO_TRIGGER_PRICE_WITHIN_STOP"
    NO_OPEN_POSITION = "STOP_LOSS_NO_OPEN_POSITION"

    # Fail-closed trigger blocks
    SYMBOL_MISMATCH = "STOP_LOSS_SYMBOL_MISMATCH"
    POSITION_STATE_UNKNOWN = "STOP_LOSS_POSITION_STATE_UNKNOWN"
    POSITION_QUANTITY_UNKNOWN = "STOP_LOSS_POSITION_QUANTITY_UNKNOWN"
    POSITION_IDENTITY_UNKNOWN = "STOP_LOSS_POSITION_IDENTITY_UNKNOWN"
    ENTRY_PRICE_UNKNOWN = "STOP_LOSS_ENTRY_PRICE_UNKNOWN"
    PRICE_INVALID = "STOP_LOSS_PRICE_INVALID"
    PRICE_STALE = "STOP_LOSS_PRICE_STALE"
    CONFIG_INVALID = "STOP_LOSS_CONFIG_INVALID"

    # Dedup / persistence blocks
    DEDUP_STATE_MISSING = "STOP_LOSS_DEDUP_STATE_MISSING"
    DEDUP_STATE_CORRUPT = "STOP_LOSS_DEDUP_STATE_CORRUPT"
    DEDUP_STATE_CONTRADICTORY = "STOP_LOSS_DEDUP_STATE_CONTRADICTORY"
    DEDUP_PREPARE_FAILED = "STOP_LOSS_DEDUP_PREPARE_FAILED"
    DEDUP_FINALIZE_FAILED = "STOP_LOSS_DEDUP_FINALIZE_FAILED"
    PREPARE_INCOMPLETE = "STOP_LOSS_PREPARE_INCOMPLETE"

    # Consumer outcomes
    EXIT_INTENT_EMITTED = "STOP_LOSS_EXIT_INTENT_EMITTED"
    DUPLICATE_SUPPRESSED = "STOP_LOSS_DUPLICATE_SUPPRESSED"
    EXIT_INTENT_SINK_FAILED = "STOP_LOSS_EXIT_INTENT_SINK_FAILED"
    EXIT_INTENT_INVALID = "STOP_LOSS_EXIT_INTENT_INVALID"
    PRODUCTIVE_ADAPTER_DISABLED = "STOP_LOSS_PRODUCTIVE_ADAPTER_DISABLED"


def to_protection_decimal(value: object, *, field: str) -> Decimal:
    """Convert to ``Decimal`` on the protection path, rejecting ``float``/``bool``.

    Raises:
        StopLossContractError: for ``None``, ``bool``, ``float``, or unparsable input.
    """
    if value is None:
        raise StopLossContractError(f"{field} must not be None")
    if isinstance(value, bool):
        raise StopLossContractError(f"{field} must not be bool")
    if isinstance(value, float):
        raise StopLossContractError(
            f"{field} must not be float on the protection path (use Decimal/str/int)"
        )
    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, (int, str)):
        try:
            decimal_value = Decimal(value)
        except (InvalidOperation, ValueError) as exc:
            raise StopLossContractError(
                f"{field} is not a valid decimal: {value!r}"
            ) from exc
    else:
        raise StopLossContractError(
            f"{field} has unsupported type {type(value).__name__}"
        )
    if not decimal_value.is_finite():
        raise StopLossContractError(f"{field} must be finite: {value!r}")
    return decimal_value


@dataclass(frozen=True)
class PositionSnapshot:
    """Authoritative position view used for protection decisions.

    ``None`` values are intentionally allowed at construction time so that an
    unknown upstream state can be represented honestly; the trigger evaluation
    then blocks instead of assuming a flat or safe position.
    """

    symbol: str
    side: PositionSide
    quantity: object = None
    entry_price: object = None
    position_id: Optional[str] = None
    opened_at_ms: Optional[int] = None


@dataclass(frozen=True)
class PriceObservation:
    """Single observed price used to evaluate the stop trigger."""

    symbol: str
    price: object
    observed_at_ms: Optional[int]
    source: str


@dataclass(frozen=True)
class StopLossTriggerConfig:
    """Armed stop configuration for one position."""

    stop_loss_pct: object
    max_price_age_ms: int = 120_000


@dataclass(frozen=True)
class StopLossProtectionEvent:
    """Deterministic identity of one protection situation."""

    event_id: str
    fingerprint: str
    contract_version: str
    symbol: str
    position_id: str
    position_side: PositionSide
    position_quantity: Decimal
    entry_price: Decimal
    stop_price: Decimal
    stop_loss_pct: Decimal
    observed_price: Decimal
    observed_at_ms: int
    price_source: str
    position_opened_at_ms: Optional[int] = None

    def identity(self) -> dict:
        """Return the dedup-relevant identity payload (no observing-tick data)."""
        return _identity_payload(
            contract_version=self.contract_version,
            symbol=self.symbol,
            position_id=self.position_id,
            position_side=self.position_side,
            position_quantity=self.position_quantity,
            entry_price=self.entry_price,
            stop_price=self.stop_price,
            stop_loss_pct=self.stop_loss_pct,
            opened_at_ms=self.position_opened_at_ms,
        )


@dataclass(frozen=True)
class StopLossTriggerResult:
    """Result of one trigger evaluation."""

    decision: StopLossTriggerDecision
    reason_code: str
    detail: str = ""
    stop_price: Optional[Decimal] = None
    event: Optional[StopLossProtectionEvent] = None

    @property
    def triggered(self) -> bool:
        return self.decision is StopLossTriggerDecision.TRIGGERED

    @property
    def blocked(self) -> bool:
        return self.decision is StopLossTriggerDecision.BLOCKED


def _q(value: Decimal, quantum: Decimal, rounding: str) -> Decimal:
    return value.quantize(quantum, rounding=rounding)


def _identity_payload(
    *,
    contract_version: str,
    symbol: str,
    position_id: str,
    position_side: PositionSide,
    position_quantity: Decimal,
    entry_price: Decimal,
    stop_price: Decimal,
    stop_loss_pct: Decimal,
    opened_at_ms: Optional[int],
) -> dict:
    return {
        "contract_version": contract_version,
        "symbol": symbol,
        "position_id": position_id,
        "position_side": position_side.value,
        "position_quantity": str(position_quantity),
        "entry_price": str(entry_price),
        "stop_price": str(stop_price),
        "stop_loss_pct": str(stop_loss_pct),
        "position_opened_at_ms": opened_at_ms,
    }


def compute_stop_price(
    *,
    side: PositionSide,
    entry_price: Decimal,
    stop_loss_pct: Decimal,
) -> Decimal:
    """Compute the armed stop price with protective rounding.

    LONG stops round up and SHORT stops round down, so quantization can only
    make protection fire earlier, never later.
    """
    if side is PositionSide.LONG:
        raw = entry_price * (Decimal(1) - stop_loss_pct)
        return _q(raw, _MONEY_Q, ROUND_UP)
    if side is PositionSide.SHORT:
        raw = entry_price * (Decimal(1) + stop_loss_pct)
        return _q(raw, _MONEY_Q, ROUND_DOWN)
    raise StopLossContractError(f"stop price undefined for side {side.value}")


def _blocked(reason: StopLossReason, detail: str) -> StopLossTriggerResult:
    return StopLossTriggerResult(
        decision=StopLossTriggerDecision.BLOCKED,
        reason_code=reason.value,
        detail=detail,
    )


def _no_trigger(
    reason: StopLossReason, detail: str, stop_price: Optional[Decimal] = None
) -> StopLossTriggerResult:
    return StopLossTriggerResult(
        decision=StopLossTriggerDecision.NO_TRIGGER,
        reason_code=reason.value,
        detail=detail,
        stop_price=stop_price,
    )


def evaluate_stop_loss_trigger(
    position: PositionSnapshot,
    observation: PriceObservation,
    config: StopLossTriggerConfig,
    *,
    now_ms: int,
) -> StopLossTriggerResult:
    """Evaluate the versioned stop-loss price trigger, fail-closed.

    Returns a ``BLOCKED`` result for every unknown, invalid, or stale input; a
    ``TRIGGERED`` result carries the deterministic protection event.
    """
    if position.symbol != observation.symbol:
        return _blocked(
            StopLossReason.SYMBOL_MISMATCH,
            f"position symbol {position.symbol!r} != observation symbol "
            f"{observation.symbol!r}",
        )

    if (
        not isinstance(position.side, PositionSide)
        or position.side is PositionSide.UNKNOWN
    ):
        return _blocked(
            StopLossReason.POSITION_STATE_UNKNOWN,
            f"position side is not protection-evaluable: {position.side!r}",
        )

    try:
        stop_loss_pct = _q(
            to_protection_decimal(config.stop_loss_pct, field="stop_loss_pct"),
            _RATIO_Q,
            ROUND_DOWN,
        )
    except StopLossContractError as exc:
        return _blocked(StopLossReason.CONFIG_INVALID, str(exc))
    if stop_loss_pct <= 0 or stop_loss_pct >= 1:
        return _blocked(
            StopLossReason.CONFIG_INVALID,
            f"stop_loss_pct must be in (0, 1): {stop_loss_pct}",
        )
    if not isinstance(config.max_price_age_ms, int) or config.max_price_age_ms <= 0:
        return _blocked(
            StopLossReason.CONFIG_INVALID,
            f"max_price_age_ms must be a positive int: {config.max_price_age_ms!r}",
        )

    if position.side is PositionSide.FLAT:
        return _no_trigger(
            StopLossReason.NO_OPEN_POSITION,
            f"no open position for {position.symbol}",
        )

    try:
        quantity = _q(
            to_protection_decimal(position.quantity, field="position.quantity"),
            _QTY_Q,
            ROUND_DOWN,
        )
    except StopLossContractError as exc:
        return _blocked(StopLossReason.POSITION_QUANTITY_UNKNOWN, str(exc))
    if quantity <= 0:
        return _blocked(
            StopLossReason.POSITION_QUANTITY_UNKNOWN,
            f"non-flat position requires positive quantity, got {quantity}",
        )

    try:
        entry_price = _q(
            to_protection_decimal(position.entry_price, field="position.entry_price"),
            _MONEY_Q,
            ROUND_DOWN,
        )
    except StopLossContractError as exc:
        return _blocked(StopLossReason.ENTRY_PRICE_UNKNOWN, str(exc))
    if entry_price <= 0:
        return _blocked(
            StopLossReason.ENTRY_PRICE_UNKNOWN,
            f"entry price must be positive, got {entry_price}",
        )

    position_id = (position.position_id or "").strip()
    if not position_id:
        return _blocked(
            StopLossReason.POSITION_IDENTITY_UNKNOWN,
            "position_id is required to derive a stable protection event identity",
        )

    try:
        observed_price = _q(
            to_protection_decimal(observation.price, field="observation.price"),
            _MONEY_Q,
            ROUND_DOWN,
        )
    except StopLossContractError as exc:
        return _blocked(StopLossReason.PRICE_INVALID, str(exc))
    if observed_price <= 0:
        return _blocked(
            StopLossReason.PRICE_INVALID,
            f"observed price must be positive, got {observed_price}",
        )

    observed_at_ms = observation.observed_at_ms
    if not isinstance(observed_at_ms, int) or isinstance(observed_at_ms, bool):
        return _blocked(
            StopLossReason.PRICE_STALE,
            f"observed_at_ms must be int, got {observed_at_ms!r}",
        )
    if observed_at_ms > now_ms:
        return _blocked(
            StopLossReason.PRICE_STALE,
            f"observation is in the future (observed_at_ms={observed_at_ms}, now_ms={now_ms})",
        )
    age_ms = now_ms - observed_at_ms
    if age_ms > config.max_price_age_ms:
        return _blocked(
            StopLossReason.PRICE_STALE,
            f"price age {age_ms}ms exceeds max_price_age_ms {config.max_price_age_ms}",
        )

    stop_price = compute_stop_price(
        side=position.side, entry_price=entry_price, stop_loss_pct=stop_loss_pct
    )

    if position.side is PositionSide.LONG:
        triggered = observed_price <= stop_price
    else:
        triggered = observed_price >= stop_price

    if not triggered:
        return _no_trigger(
            StopLossReason.NO_TRIGGER_PRICE_ABOVE_STOP,
            f"price {observed_price} has not breached stop {stop_price} "
            f"for {position.side.value}",
            stop_price=stop_price,
        )

    identity = _identity_payload(
        contract_version=STOP_LOSS_TRIGGER_CONTRACT_VERSION,
        symbol=position.symbol,
        position_id=position_id,
        position_side=position.side,
        position_quantity=quantity,
        entry_price=entry_price,
        stop_price=stop_price,
        stop_loss_pct=stop_loss_pct,
        opened_at_ms=position.opened_at_ms,
    )
    fingerprint = canonical_hash(identity)
    event_id = f"{_EVENT_ID_PREFIX}-{fingerprint[:_EVENT_ID_HASH_LEN]}"

    event = StopLossProtectionEvent(
        event_id=event_id,
        fingerprint=fingerprint,
        contract_version=STOP_LOSS_TRIGGER_CONTRACT_VERSION,
        symbol=position.symbol,
        position_id=position_id,
        position_side=position.side,
        position_quantity=quantity,
        entry_price=entry_price,
        stop_price=stop_price,
        stop_loss_pct=stop_loss_pct,
        observed_price=observed_price,
        observed_at_ms=observed_at_ms,
        price_source=observation.source,
        position_opened_at_ms=position.opened_at_ms,
    )
    return StopLossTriggerResult(
        decision=StopLossTriggerDecision.TRIGGERED,
        reason_code=StopLossReason.TRIGGERED.value,
        detail=f"price {observed_price} breached stop {stop_price}",
        stop_price=stop_price,
        event=event,
    )
