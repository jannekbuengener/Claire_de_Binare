"""Minimal contracts for externally dockable strategy and execution adapters.

This module is intentionally runtime-light:
- no registry
- no dynamic loading
- no service wiring

It defines the smallest shared contract surface that later adapters can
implement without bypassing the existing core safety path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Protocol, runtime_checkable


RunMode = Literal["shadow", "paper", "replay", "live"]
TradeSide = Literal["BUY", "SELL"]
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
