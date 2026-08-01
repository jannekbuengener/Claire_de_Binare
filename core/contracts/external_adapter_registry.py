"""Static, repo-owned adapter registry for strategy and execution selection.

Issue #1579 intentionally stops at a small, fixed registry layer:
- no discovery
- no remote loading
- no service wiring
- no risk/policy bypass

The active services still use their existing first-party paths. This module
only makes those paths selectable by fixed in-repo adapter IDs so that #1580
can wire them in later without inventing a plugin system.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any, Callable, Mapping, cast

from .external_adapter_contracts import (
    CancelOrderRequest,
    CancelOrderResponse,
    ExecutionAdapter,
    ExecutionAdapterId,
    ExecutionAdapterRequest,
    ExecutionAdapterResponse,
    OpenOrderSnapshot,
    StrategyAdapter,
    StrategyAdapterId,
    StrategyAdapterRequest,
    StrategyAdapterResponse,
    StrategySignalCandidate,
)

SIGNAL_ADAPTER_ENV_VAR = "SIGNAL_ADAPTER_ID"
EXECUTION_ADAPTER_ENV_VAR = "EXECUTION_ADAPTER_ID"

MOMENTUM_BUILTIN = cast(StrategyAdapterId, "momentum_builtin")
MOCK_BUILTIN = cast(ExecutionAdapterId, "mock_builtin")
MEXC_BUILTIN = cast(ExecutionAdapterId, "mexc_builtin")

StrategyAdapterFactory = Callable[..., StrategyAdapter]
ExecutionAdapterFactory = Callable[..., ExecutionAdapter]


def _parse_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _first_number(*values: Any) -> float | None:
    for value in values:
        parsed = _parse_float(value)
        if parsed is not None:
            return parsed
    return None


class BuiltinMomentumStrategyAdapter:
    """First-party shim for the current built-in momentum signal rule."""

    adapter_id: StrategyAdapterId = MOMENTUM_BUILTIN

    def __init__(
        self,
        evaluate_fn: (
            Callable[[StrategyAdapterRequest], StrategyAdapterResponse] | None
        ) = None,
    ) -> None:
        self._evaluate_fn = evaluate_fn

    def evaluate(self, request: StrategyAdapterRequest) -> StrategyAdapterResponse:
        if self._evaluate_fn is not None:
            return self._evaluate_fn(request)

        snapshot = request.market_snapshot
        event = request.market_event
        runtime_context = request.runtime_context

        symbol = str(
            request.symbol or snapshot.get("symbol") or event.get("symbol") or ""
        ).upper()
        pct_change = _first_number(snapshot.get("pct_change"), event.get("pct_change"))
        volume = _first_number(
            snapshot.get("volume"),
            snapshot.get("volume_15m"),
            event.get("volume"),
            event.get("trade_qty"),
            snapshot.get("trade_qty"),
        )
        price = _first_number(snapshot.get("price"), event.get("price"))
        threshold_pct = _first_number(runtime_context.get("threshold_pct"))
        min_volume = _first_number(runtime_context.get("min_volume"))
        strategy_id = str(runtime_context.get("strategy_id") or self.adapter_id)
        bot_id = runtime_context.get("bot_id")

        if (
            not symbol
            or pct_change is None
            or volume is None
            or threshold_pct is None
            or min_volume is None
        ):
            return StrategyAdapterResponse(
                diagnostics={
                    "adapter_id": self.adapter_id,
                    "status": "insufficient_input",
                }
            )

        if pct_change < threshold_pct or volume < min_volume:
            return StrategyAdapterResponse(
                diagnostics={
                    "adapter_id": self.adapter_id,
                    "status": "no_signal",
                    "pct_change": pct_change,
                    "threshold_pct": threshold_pct,
                    "volume": volume,
                    "min_volume": min_volume,
                }
            )

        metadata: dict[str, Any] = {"adapter_id": self.adapter_id}
        if bot_id not in (None, ""):
            metadata["bot_id"] = bot_id

        signal = StrategySignalCandidate(
            strategy_id=strategy_id,
            symbol=symbol,
            side="BUY",
            reason=f"Momentum: {pct_change:+.4f}% > {threshold_pct}%",
            price=price,
            pct_change=pct_change,
            metadata=metadata,
        )
        return StrategyAdapterResponse(
            signals=(signal,),
            diagnostics={
                "adapter_id": self.adapter_id,
                "status": "signal_emitted",
            },
        )


class MockExecutionAdapter:
    """First-party shim for the current mock execution path."""

    adapter_id: ExecutionAdapterId = MOCK_BUILTIN
    supports_reduce_only = True
    supports_cancel: bool = True

    def __init__(self, executor=None, **executor_kwargs: Any) -> None:
        if executor is None:
            from services.execution.mock_executor import MockExecutor

            executor = MockExecutor(**executor_kwargs)
        self._executor = executor

    def execute(self, request: ExecutionAdapterRequest) -> ExecutionAdapterResponse:
        from services.execution.models import Order

        order = Order.from_event(dict(request.order))
        if request.reduce_only is not order.reduce_only:
            raise ValueError("reduce-only adapter flag mismatch")
        if request.reduce_only:
            try:
                position = Decimal(str(request.position_before))
                maximum = Decimal(str(request.max_executable_quantity))
                quantity = Decimal(str(order.quantity))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ValueError("invalid reduce-only adapter quantities") from exc
            if not (
                request.reduce_only_contract_version == "execution_reduce_only_v1"
                and order.reduce_only is True
                and position.is_finite()
                and position != 0
                and maximum.is_finite()
                and maximum > 0
                and maximum <= abs(position)
                and quantity.is_finite()
                and quantity > 0
                and quantity <= maximum
                and (
                    (position > 0 and order.side == "SELL")
                    or (position < 0 and order.side == "BUY")
                )
            ):
                raise ValueError("reduce-only adapter contract rejected")
        result = self._executor.execute_order(order)
        return ExecutionAdapterResponse(
            status=result.status,
            order_id=result.order_id,
            filled_quantity=result.filled_quantity,
            price=result.price,
            venue_order_id=result.order_id,
            error_message=result.error_message,
            raw_venue_payload={"adapter_id": self.adapter_id},
            reduce_only_acknowledged=request.reduce_only,
        )

    def cancel_order(self, request: CancelOrderRequest) -> CancelOrderResponse:
        from core.utils.clock import utcnow
        from services.execution.models import OrderStatus

        order_id = request.venue_order_id or request.internal_order_id
        behavior = getattr(self._executor, "cancel_behavior_by_id", {}).get(
            order_id, getattr(self._executor, "cancel_behavior", "confirm")
        )
        observed = utcnow().isoformat()

        if behavior == "error":
            raise RuntimeError(f"mock adapter cancel error for {order_id}")
        if behavior == "malformed":
            # Intentionally invalid payload shape for contract tests; caller maps
            # non-CancelOrderResponse to STATUS_UNKNOWN. We still return a response
            # object but with empty/ambiguous fields that are not confirmed.
            return CancelOrderResponse(
                internal_order_id=request.internal_order_id,
                venue_order_id=request.venue_order_id,
                accepted=False,
                confirmed_cancelled=False,
                terminal_status=None,
                adapter_reason_code="OPEN_ORDER_STATUS_UNKNOWN",
                raw_status_redacted="malformed",
                observed_at_utc=observed,
            )
        if behavior == "reject":
            return CancelOrderResponse(
                internal_order_id=request.internal_order_id,
                venue_order_id=request.venue_order_id or order_id,
                accepted=False,
                confirmed_cancelled=False,
                terminal_status=None,
                adapter_reason_code="CANCEL_REQUEST_REJECTED",
                raw_status_redacted="rejected",
                observed_at_utc=observed,
            )
        if behavior == "accepted_unconfirmed":
            return CancelOrderResponse(
                internal_order_id=request.internal_order_id,
                venue_order_id=request.venue_order_id or order_id,
                accepted=True,
                confirmed_cancelled=False,
                terminal_status=None,
                adapter_reason_code="CANCEL_CONFIRMATION_MISSING",
                raw_status_redacted="accepted_unconfirmed",
                observed_at_utc=observed,
            )

        existing = self._executor.get_order_status(order_id)
        if existing is None:
            # Try internal id
            existing = self._executor.get_order_status(request.internal_order_id)
            if existing is not None:
                order_id = request.internal_order_id

        if existing is None:
            return CancelOrderResponse(
                internal_order_id=request.internal_order_id,
                venue_order_id=request.venue_order_id,
                accepted=False,
                confirmed_cancelled=False,
                terminal_status=None,
                adapter_reason_code="CANCEL_REQUEST_REJECTED",
                raw_status_redacted="not_found",
                observed_at_utc=observed,
            )

        if existing.status in {
            OrderStatus.FILLED.value,
            OrderStatus.CANCELLED.value,
            OrderStatus.REJECTED.value,
        }:
            return CancelOrderResponse(
                internal_order_id=request.internal_order_id,
                venue_order_id=order_id,
                accepted=True,
                confirmed_cancelled=existing.status == OrderStatus.CANCELLED.value,
                terminal_status=existing.status,
                adapter_reason_code="CANCEL_ALREADY_CONFIRMED",
                raw_status_redacted=existing.status,
                observed_at_utc=observed,
            )

        ok = self._executor.cancel_order(order_id)
        if not ok:
            return CancelOrderResponse(
                internal_order_id=request.internal_order_id,
                venue_order_id=order_id,
                accepted=False,
                confirmed_cancelled=False,
                terminal_status=None,
                adapter_reason_code="CANCEL_REQUEST_REJECTED",
                raw_status_redacted="cancel_false",
                observed_at_utc=observed,
            )
        return CancelOrderResponse(
            internal_order_id=request.internal_order_id,
            venue_order_id=order_id,
            accepted=True,
            confirmed_cancelled=True,
            terminal_status="CANCELLED",
            adapter_reason_code="KILL_CANCEL_PASS",
            raw_status_redacted="CANCELLED",
            observed_at_utc=observed,
        )

    def get_open_order(
        self, *, internal_order_id: str, venue_order_id: str | None = None
    ) -> OpenOrderSnapshot | None:
        from core.utils.clock import utcnow

        order_id = venue_order_id or internal_order_id
        existing = self._executor.get_order_status(order_id)
        if existing is None and venue_order_id:
            existing = self._executor.get_order_status(internal_order_id)
            order_id = internal_order_id
        if existing is None:
            return None
        remaining = max(float(existing.quantity) - float(existing.filled_quantity), 0.0)
        return OpenOrderSnapshot(
            internal_order_id=internal_order_id,
            venue_order_id=order_id,
            symbol=existing.symbol,
            status=existing.status,
            filled_quantity=float(existing.filled_quantity),
            remaining_quantity=remaining,
            observed_at_utc=utcnow().isoformat(),
        )

    def list_open_orders(self) -> tuple[OpenOrderSnapshot, ...]:
        from core.utils.clock import utcnow
        from services.execution.models import OrderStatus

        open_statuses = {
            OrderStatus.PENDING.value,
            OrderStatus.SUBMITTED.value,
            OrderStatus.PARTIALLY_FILLED.value,
        }
        snapshots = []
        now = utcnow().isoformat()
        for order_id, existing in sorted(self._executor.orders.items()):
            if existing.status not in open_statuses:
                continue
            remaining = max(
                float(existing.quantity) - float(existing.filled_quantity), 0.0
            )
            snapshots.append(
                OpenOrderSnapshot(
                    internal_order_id=order_id,
                    venue_order_id=order_id,
                    symbol=existing.symbol,
                    status=existing.status,
                    filled_quantity=float(existing.filled_quantity),
                    remaining_quantity=remaining,
                    observed_at_utc=now,
                )
            )
        return tuple(snapshots)


class MexcExecutionAdapter:
    """First-party shim for the current MEXC-backed execution path."""

    adapter_id: ExecutionAdapterId = MEXC_BUILTIN
    # No venue-native or equivalent reduce-only behavior is proven for this shim.
    supports_reduce_only = False
    supports_cancel: bool = False

    def __init__(self, executor=None, **executor_kwargs: Any) -> None:
        if executor is None:
            from services.execution.live_executor import LiveExecutor

            executor = LiveExecutor(**executor_kwargs)
        self._executor = executor

    def execute(self, request: ExecutionAdapterRequest) -> ExecutionAdapterResponse:
        from services.execution.models import Order

        order = Order.from_event(dict(request.order))
        result = self._executor.execute_order(order)
        return ExecutionAdapterResponse(
            status=result.status,
            order_id=result.order_id,
            filled_quantity=result.filled_quantity,
            price=result.price,
            venue_order_id=result.order_id,
            error_message=result.error_message,
            raw_venue_payload={"adapter_id": self.adapter_id},
            reduce_only_acknowledged=False,
        )

    def cancel_order(self, request: CancelOrderRequest) -> CancelOrderResponse:
        """Productive cancel is intentionally unsupported in this slice (#4185)."""
        from core.utils.clock import utcnow

        return CancelOrderResponse(
            internal_order_id=request.internal_order_id,
            venue_order_id=request.venue_order_id,
            accepted=False,
            confirmed_cancelled=False,
            terminal_status=None,
            adapter_reason_code="CANCEL_ADAPTER_UNSUPPORTED",
            raw_status_redacted="mexc_cancel_unsupported_in_scope",
            observed_at_utc=utcnow().isoformat(),
        )

    def get_open_order(
        self, *, internal_order_id: str, venue_order_id: str | None = None
    ) -> OpenOrderSnapshot | None:
        return None

    def list_open_orders(self) -> tuple[OpenOrderSnapshot, ...]:
        return ()


_STRATEGY_ADAPTER_REGISTRY: dict[StrategyAdapterId, StrategyAdapterFactory] = {
    MOMENTUM_BUILTIN: BuiltinMomentumStrategyAdapter,
}
_EXECUTION_ADAPTER_REGISTRY: dict[ExecutionAdapterId, ExecutionAdapterFactory] = {
    MOCK_BUILTIN: MockExecutionAdapter,
    MEXC_BUILTIN: MexcExecutionAdapter,
}

STRATEGY_ADAPTER_REGISTRY: Mapping[StrategyAdapterId, StrategyAdapterFactory] = (
    MappingProxyType(_STRATEGY_ADAPTER_REGISTRY)
)
EXECUTION_ADAPTER_REGISTRY: Mapping[ExecutionAdapterId, ExecutionAdapterFactory] = (
    MappingProxyType(_EXECUTION_ADAPTER_REGISTRY)
)


def list_strategy_adapter_ids() -> tuple[StrategyAdapterId, ...]:
    return tuple(_STRATEGY_ADAPTER_REGISTRY.keys())


def list_execution_adapter_ids() -> tuple[ExecutionAdapterId, ...]:
    return tuple(_EXECUTION_ADAPTER_REGISTRY.keys())


def default_strategy_adapter_id() -> StrategyAdapterId:
    return MOMENTUM_BUILTIN


def default_execution_adapter_id(*, mock_trading: bool) -> ExecutionAdapterId:
    return MOCK_BUILTIN if mock_trading else MEXC_BUILTIN


def resolve_strategy_adapter_id(adapter_id: str | None = None) -> StrategyAdapterId:
    candidate = (adapter_id or default_strategy_adapter_id()).strip()
    if candidate not in _STRATEGY_ADAPTER_REGISTRY:
        raise KeyError(f"Unknown strategy adapter id: {candidate}")
    return cast(StrategyAdapterId, candidate)


def resolve_execution_adapter_id(
    adapter_id: str | None = None, *, mock_trading: bool
) -> ExecutionAdapterId:
    candidate = (
        adapter_id or default_execution_adapter_id(mock_trading=mock_trading)
    ).strip()
    if candidate not in _EXECUTION_ADAPTER_REGISTRY:
        raise KeyError(f"Unknown execution adapter id: {candidate}")
    return cast(ExecutionAdapterId, candidate)


def build_strategy_adapter(
    adapter_id: str | None = None, **kwargs: Any
) -> StrategyAdapter:
    resolved = resolve_strategy_adapter_id(adapter_id)
    factory = _STRATEGY_ADAPTER_REGISTRY[resolved]
    return factory(**kwargs)


def build_execution_adapter(
    adapter_id: str | None = None, *, mock_trading: bool, **kwargs: Any
) -> ExecutionAdapter:
    resolved = resolve_execution_adapter_id(adapter_id, mock_trading=mock_trading)
    factory = _EXECUTION_ADAPTER_REGISTRY[resolved]
    return factory(**kwargs)
