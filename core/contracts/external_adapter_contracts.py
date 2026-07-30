"""Minimal contracts for externally dockable strategy and execution adapters.

This module is intentionally runtime-light:
- no registry
- no dynamic loading
- no service wiring
- static adapter registry lives separately in `external_adapter_registry.py`

It defines the smallest shared contract surface that later adapters can
implement without bypassing the existing core safety path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Protocol, runtime_checkable

RunMode = Literal["shadow", "paper", "replay", "live"]
TradeSide = Literal["BUY", "SELL"]
StrategyAdapterId = Literal["momentum_builtin"]
ExecutionAdapterId = Literal["mock_builtin", "mexc_builtin"]
ExecutionStatus = Literal[
    "PENDING",
    "SUBMITTED",
    "FILLED",
    "PARTIALLY_FILLED",
    "REJECTED",
    "CANCELLED",
    "FAILED",
]


@dataclass(frozen=True, slots=True)
class StrategyAdapterRequest:
    """Normalized input that the core may hand to a strategy adapter."""

    symbol: str
    market_event: Mapping[str, Any]
    market_snapshot: Mapping[str, Any]
    runtime_context: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class StrategySignalCandidate:
    """Candidate signal emitted by a strategy adapter before risk approval."""

    strategy_id: str
    symbol: str
    side: TradeSide
    reason: str
    confidence: float | None = None
    price: float | None = None
    pct_change: float | None = None
    signal_id: str | None = None
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class StrategyAdapterResponse:
    """Strategy adapter output.

    Adapters may emit zero, one, or multiple signal candidates.
    """

    signals: tuple[StrategySignalCandidate, ...] = ()
    diagnostics: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ExecutionAdapterRequest:
    """Approved order command passed into an execution adapter."""

    order: Mapping[str, Any]
    run_mode: RunMode
    decision_contract_v1: Mapping[str, Any]
    runtime_context: Mapping[str, Any]
    policy_snapshot: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ExecutionAdapterResponse:
    """Normalized execution response returned to the core."""

    status: ExecutionStatus
    order_id: str
    filled_quantity: float
    price: float | None = None
    venue_order_id: str | None = None
    error_message: str | None = None
    raw_venue_payload: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CancelOrderRequest:
    """Normalized cancel request for an open synthetic or venue order."""

    internal_order_id: str
    venue_order_id: str | None
    symbol: str
    reason_code: str
    kill_event_id: str
    requested_at_utc: str


@dataclass(frozen=True, slots=True)
class CancelOrderResponse:
    """Normalized cancel outcome.

    ``accepted=True`` is not automatically ``confirmed_cancelled=True``.
    A naked bool must not be the only proof surface.
    """

    internal_order_id: str
    venue_order_id: str | None
    accepted: bool
    confirmed_cancelled: bool
    terminal_status: ExecutionStatus | None
    adapter_reason_code: str
    raw_status_redacted: str | None
    observed_at_utc: str


@dataclass(frozen=True, slots=True)
class OpenOrderSnapshot:
    """Point-in-time view of an open or recently observed order."""

    internal_order_id: str
    venue_order_id: str | None
    symbol: str
    status: ExecutionStatus
    filled_quantity: float
    remaining_quantity: float
    observed_at_utc: str


@runtime_checkable
class StrategyAdapter(Protocol):
    """Protocol for future strategy adapters."""

    adapter_id: str

    def evaluate(self, request: StrategyAdapterRequest) -> StrategyAdapterResponse:
        """Return signal candidates for a normalized market snapshot."""


@runtime_checkable
class ExecutionAdapter(Protocol):
    """Protocol for future execution adapters."""

    adapter_id: str

    def execute(self, request: ExecutionAdapterRequest) -> ExecutionAdapterResponse:
        """Execute an already risk-approved order command."""


@runtime_checkable
class CancelCapableExecutionAdapter(Protocol):
    """Optional cancel/list surface for kill-cancel reconciliation (#4185)."""

    adapter_id: str

    def cancel_order(self, request: CancelOrderRequest) -> CancelOrderResponse:
        """Request cancellation and return a normalized outcome."""

    def get_open_order(
        self, *, internal_order_id: str, venue_order_id: str | None = None
    ) -> OpenOrderSnapshot | None:
        """Read back a single order status for cancel confirmation."""

    def list_open_orders(self) -> tuple[OpenOrderSnapshot, ...]:
        """List currently open orders known to the adapter."""
