"""Deterministic replay execution wrapper and FillEnvelope emission.

This module provides a narrow replay-only execution layer that converts
deterministic replay signals plus market context into simulated execution
results and deterministic FillEnvelopeV1 outputs.

Design rules:
  - All monetary/quantity/ratio fields quantized via Decimal before serialization
  - ts_ms / created_at derived exclusively from ClockContextProtocol (no wall-clock)
  - event_id derived deterministically from replay inputs (no random, no UUID)
  - Fail-closed: invalid/missing market context raises ReplayExecutionError immediately
  - FillEnvelopeV1 payload schema is fully documented (see ReplayFillPayload)
  - No Redis, no network, no async, no event-loop logic
  - Reuses ExecutionSimulator without modifying it

Governance: Issue #1802 (LR-021 Replay Execution Wrapper)

FillEnvelopeV1 payload schema (ReplayFillPayload.to_dict() keys):
  filled_quantity   str   Decimal(QTY_Q=8dp)   — actual filled quantity
  avg_fill_price    str   Decimal(MONEY_Q=8dp)  — avg fill price incl. slippage
  slippage_bps      str   Decimal(BPS_Q=2dp)    — total slippage in basis points
  fees_usdt         str   Decimal(MONEY_Q=8dp)  — total trading fees (quote currency)
  fill_ratio        str   Decimal(RATIO_Q=6dp)  — filled / requested size (0..1)
  partial_fill      bool                         — True if this was a partial fill
  order_side        str                          — "BUY" or "SELL" (normalised)
  symbol            str                          — trading symbol (e.g. "BTCUSDT")
  notes             str   optional               — execution notes from simulator

relations:
  role: replay_execution_wrapper
  domain: replay
  upstream:
    - services.execution.simulator
    - core.replay.envelopes
    - core.replay.clock_context
    - core.replay.canonical_json
    - core.contracts.external_adapter_contracts
  downstream:
    - core.replay.event_loop (future, Issue #1803)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Optional

from core.contracts.external_adapter_contracts import StrategySignalCandidate
from core.replay.canonical_json import canonical_hash
from core.replay.clock_context import ClockContextProtocol
from core.replay.envelopes import FillEnvelopeV1
from services.execution.simulator import ExecutionSimulator

# ---------------------------------------------------------------------------
# Quantization constants — mirrors decision_contract_v1._MONEY_Q / _RATIO_Q
# ---------------------------------------------------------------------------
_MONEY_Q = Decimal("0.00000001")   # 8dp — prices and fees
_QTY_Q = Decimal("0.00000001")     # 8dp — quantities
_RATIO_Q = Decimal("0.000001")     # 6dp — ratios (fill_ratio)
_BPS_Q = Decimal("0.01")           # 2dp — basis points


class ReplayExecutionError(ValueError):
    """Raised when replay execution cannot proceed due to invalid inputs."""


# ---------------------------------------------------------------------------
# Quantization helpers
# ---------------------------------------------------------------------------

def _q_money(value: float) -> str:
    """Quantize a float to MONEY_Q (8dp) as a deterministic decimal string.

    Args:
        value: Raw float value (e.g. fill price, fee amount).

    Returns:
        Fixed-precision decimal string (e.g. "50075.00000000").

    Raises:
        ReplayExecutionError: If value is not finite.
    """
    d = Decimal(str(value))
    if not d.is_finite():
        raise ReplayExecutionError(f"Non-finite monetary value: {value!r}")
    return format(d.quantize(_MONEY_Q, rounding=ROUND_HALF_EVEN), "f")


def _q_qty(value: float) -> str:
    """Quantize a float to QTY_Q (8dp) as a deterministic decimal string.

    Args:
        value: Raw float quantity value.

    Returns:
        Fixed-precision decimal string (e.g. "0.50000000").

    Raises:
        ReplayExecutionError: If value is not finite.
    """
    d = Decimal(str(value))
    if not d.is_finite():
        raise ReplayExecutionError(f"Non-finite quantity value: {value!r}")
    return format(d.quantize(_QTY_Q, rounding=ROUND_HALF_EVEN), "f")


def _q_ratio(value: float) -> str:
    """Quantize a float to RATIO_Q (6dp) as a deterministic decimal string.

    Args:
        value: Raw float ratio value (expected range: 0.0..1.0).

    Returns:
        Fixed-precision decimal string (e.g. "1.000000").

    Raises:
        ReplayExecutionError: If value is not finite.
    """
    d = Decimal(str(value))
    if not d.is_finite():
        raise ReplayExecutionError(f"Non-finite ratio value: {value!r}")
    return format(d.quantize(_RATIO_Q, rounding=ROUND_HALF_EVEN), "f")


def _q_bps(value: float) -> str:
    """Quantize a float to BPS_Q (2dp) as a deterministic decimal string.

    Args:
        value: Raw float value in basis points.

    Returns:
        Fixed-precision decimal string (e.g. "15.00").

    Raises:
        ReplayExecutionError: If value is not finite.
    """
    d = Decimal(str(value))
    if not d.is_finite():
        raise ReplayExecutionError(f"Non-finite bps value: {value!r}")
    return format(d.quantize(_BPS_Q, rounding=ROUND_HALF_EVEN), "f")


# ---------------------------------------------------------------------------
# Deterministic ID derivation
# ---------------------------------------------------------------------------

def _derive_fill_event_id(
    replay_run_id: str,
    ts_ms: int,
    side: str,
    symbol: str,
    envelope_index: int,
) -> str:
    """Derive a deterministic fill event_id from replay-context inputs.

    Uses canonical_hash over a fixed key set so identical inputs always
    produce identical event_ids regardless of call time.

    Args:
        replay_run_id: Replay run identifier (e.g. "replay-abc123").
        ts_ms: Event timestamp in milliseconds (from ReplayClockContext).
        side: Order side ("BUY" or "SELL", normalised to upper).
        symbol: Trading symbol (e.g. "BTCUSDT").
        envelope_index: Zero-based position of this fill in the replay stream.

    Returns:
        Deterministic event_id string prefixed with "fill-".
    """
    key = {
        "t": "fill",
        "rid": replay_run_id,
        "ts": ts_ms,
        "side": side.upper(),
        "sym": symbol,
        "idx": envelope_index,
    }
    return f"fill-{canonical_hash(key)[:16]}"


# ---------------------------------------------------------------------------
# Input and output dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ReplayMarketContext:
    """Immutable market/simulation context for a single replay execution step.

    All fields are explicit; there are no defaults for determinism-critical
    numeric parameters. Validation is performed in __post_init__.

    Attributes:
        current_price: Mid-market price in quote currency (e.g. USDT).
            Must be strictly positive.
        order_book_depth: Available liquidity in quote currency.
            Must be strictly positive.
        volatility: Current realized/implied volatility (e.g. 0.02 = 2%).
            Must be non-negative.
        order_size: Order size in base currency (e.g. BTC).
            Must be strictly positive.
    """

    current_price: float
    order_book_depth: float
    volatility: float
    order_size: float

    def __post_init__(self) -> None:
        if not isinstance(self.current_price, (int, float)):
            raise ReplayExecutionError("current_price must be numeric")
        if self.current_price <= 0:
            raise ReplayExecutionError(
                f"current_price must be > 0, got {self.current_price!r}"
            )
        if not isinstance(self.order_book_depth, (int, float)):
            raise ReplayExecutionError("order_book_depth must be numeric")
        if self.order_book_depth <= 0:
            raise ReplayExecutionError(
                f"order_book_depth must be > 0, got {self.order_book_depth!r}"
            )
        if not isinstance(self.volatility, (int, float)):
            raise ReplayExecutionError("volatility must be numeric")
        if self.volatility < 0:
            raise ReplayExecutionError(
                f"volatility must be >= 0, got {self.volatility!r}"
            )
        if not isinstance(self.order_size, (int, float)):
            raise ReplayExecutionError("order_size must be numeric")
        if self.order_size <= 0:
            raise ReplayExecutionError(
                f"order_size must be > 0, got {self.order_size!r}"
            )


@dataclass(frozen=True, slots=True)
class ReplayFillPayload:
    """Quantized, deterministic fill result from a replay execution step.

    All numeric fields are fixed-precision decimal strings to avoid
    float serialization variance. Identical simulator inputs always
    produce identical ReplayFillPayload instances.

    This dataclass is the authoritative definition of the FillEnvelopeV1
    payload schema for replay-produced fills. See module docstring for
    the full field contract.

    Attributes:
        filled_quantity:  Actual filled quantity (8dp decimal string).
        avg_fill_price:   Average fill price including slippage (8dp).
        slippage_bps:     Total slippage in basis points (2dp).
        fees_usdt:        Total trading fees in quote currency (8dp).
        fill_ratio:       Filled / requested ratio in range [0, 1] (6dp).
        partial_fill:     True if this was a partial fill.
        order_side:       Normalised order side: "BUY" or "SELL".
        symbol:           Trading symbol (e.g. "BTCUSDT").
        notes:            Optional execution notes from simulator.
    """

    filled_quantity: str
    avg_fill_price: str
    slippage_bps: str
    fees_usdt: str
    fill_ratio: str
    partial_fill: bool
    order_side: str
    symbol: str
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        """Return canonical payload dict for FillEnvelopeV1.

        None-valued fields (notes) are omitted so the output is
        deterministically compact.
        """
        result: dict = {
            "filled_quantity": self.filled_quantity,
            "avg_fill_price": self.avg_fill_price,
            "slippage_bps": self.slippage_bps,
            "fees_usdt": self.fees_usdt,
            "fill_ratio": self.fill_ratio,
            "partial_fill": self.partial_fill,
            "order_side": self.order_side,
            "symbol": self.symbol,
        }
        if self.notes is not None:
            result["notes"] = self.notes
        return result


# ---------------------------------------------------------------------------
# Execution wrapper
# ---------------------------------------------------------------------------

class ReplayExecutionWrapper:
    """Narrow replay-only wrapper around ExecutionSimulator.

    Responsibilities:
    - Accept replay signal + market context + replay clock + run identifiers
    - Call ExecutionSimulator.simulate_market_order() for the given signal
    - Quantize float simulator outputs into deterministic string fields
    - Derive ts_ms / created_at from ClockContextProtocol (no wall-clock)
    - Derive event_id deterministically from replay-context inputs
    - Emit a valid (ReplayFillPayload, FillEnvelopeV1) pair

    The simulator instance is injected and not modified. No scheduling,
    no event loop, no Redis, no async.

    Usage::

        simulator = ExecutionSimulator()
        wrapper = ReplayExecutionWrapper(simulator=simulator)

        fill_payload, fill_envelope = wrapper.execute(
            signal=signal_candidate,
            market_ctx=ReplayMarketContext(
                current_price=50000.0,
                order_book_depth=1_000_000.0,
                volatility=0.02,
                order_size=0.5,
            ),
            clock=ReplayClockContext(ts_ms=envelope.ts_ms),
            replay_run_id="replay-abc123",
            envelope_index=0,
        )
    """

    def __init__(self, simulator: ExecutionSimulator) -> None:
        """Initialise with an injected ExecutionSimulator.

        Args:
            simulator: ExecutionSimulator instance (not modified by this wrapper).
        """
        self._simulator = simulator

    def execute(
        self,
        *,
        signal: StrategySignalCandidate,
        market_ctx: ReplayMarketContext,
        clock: ClockContextProtocol,
        replay_run_id: str,
        envelope_index: int = 0,
    ) -> tuple[ReplayFillPayload, FillEnvelopeV1]:
        """Execute one replay signal and return a quantized fill + FillEnvelopeV1.

        Args:
            signal: Strategy signal candidate (provides side and symbol).
            market_ctx: Explicit market/simulation context (price, depth, vol, size).
            clock: Replay clock context — ts_ms and created_at come from here only.
            replay_run_id: Replay run identifier used for deterministic event_id.
            envelope_index: Zero-based ordinal of this fill in the replay stream.

        Returns:
            Tuple of (ReplayFillPayload, FillEnvelopeV1). The fill envelope's
            payload is ReplayFillPayload.to_dict().

        Raises:
            ReplayExecutionError: If market_ctx is invalid, or if simulator
                produces non-finite numeric outputs.
        """
        ts_ms = clock.now_ts_ms()
        created_at = clock.now_iso()

        raw = self._simulator.simulate_market_order(
            side=signal.side.lower(),
            size=market_ctx.order_size,
            current_price=market_ctx.current_price,
            order_book_depth=market_ctx.order_book_depth,
            volatility=market_ctx.volatility,
        )

        fill_payload = ReplayFillPayload(
            filled_quantity=_q_qty(raw.filled_size),
            avg_fill_price=_q_money(raw.avg_fill_price),
            slippage_bps=_q_bps(raw.slippage_bps),
            fees_usdt=_q_money(raw.fees),
            fill_ratio=_q_ratio(raw.fill_ratio),
            partial_fill=raw.partial_fill,
            order_side=signal.side.upper(),
            symbol=signal.symbol,
            notes=raw.notes,
        )

        event_id = _derive_fill_event_id(
            replay_run_id=replay_run_id,
            ts_ms=ts_ms,
            side=signal.side,
            symbol=signal.symbol,
            envelope_index=envelope_index,
        )

        fill_envelope = FillEnvelopeV1(
            schema_version="envelope.v1",
            event_type="FILL",
            event_id=event_id,
            ts_ms=ts_ms,
            created_at=created_at,
            payload=fill_payload.to_dict(),
            replay_run_id=replay_run_id,
            replay_envelope_index=envelope_index,
        )

        return fill_payload, fill_envelope
