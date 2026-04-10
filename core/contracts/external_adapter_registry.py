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

from types import MappingProxyType
from typing import Any, Callable, Mapping, cast

from .external_adapter_contracts import (
    ExecutionAdapter,
    ExecutionAdapterId,
    ExecutionAdapterRequest,
    ExecutionAdapterResponse,
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
        evaluate_fn: Callable[[StrategyAdapterRequest], StrategyAdapterResponse]
        | None = None,
    ) -> None:
        self._evaluate_fn = evaluate_fn

    def evaluate(self, request: StrategyAdapterRequest) -> StrategyAdapterResponse:
        if self._evaluate_fn is not None:
            return self._evaluate_fn(request)

        snapshot = request.market_snapshot
        event = request.market_event
        runtime_context = request.runtime_context

        symbol = str(
            request.symbol
            or snapshot.get("symbol")
            or event.get("symbol")
            or ""
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

    def __init__(self, executor=None, **executor_kwargs: Any) -> None:
        if executor is None:
            from services.execution.mock_executor import MockExecutor

            executor = MockExecutor(**executor_kwargs)
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
            venue_order_id=None,
            error_message=result.error_message,
            raw_venue_payload={"adapter_id": self.adapter_id},
        )


class MexcExecutionAdapter:
    """First-party shim for the current MEXC-backed execution path."""

    adapter_id: ExecutionAdapterId = MEXC_BUILTIN

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
        )


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
    candidate = (adapter_id or default_execution_adapter_id(mock_trading=mock_trading)).strip()
    if candidate not in _EXECUTION_ADAPTER_REGISTRY:
        raise KeyError(f"Unknown execution adapter id: {candidate}")
    return cast(ExecutionAdapterId, candidate)


def build_strategy_adapter(adapter_id: str | None = None, **kwargs: Any) -> StrategyAdapter:
    resolved = resolve_strategy_adapter_id(adapter_id)
    factory = _STRATEGY_ADAPTER_REGISTRY[resolved]
    return factory(**kwargs)


def build_execution_adapter(
    adapter_id: str | None = None, *, mock_trading: bool, **kwargs: Any
) -> ExecutionAdapter:
    resolved = resolve_execution_adapter_id(adapter_id, mock_trading=mock_trading)
    factory = _EXECUTION_ADAPTER_REGISTRY[resolved]
    return factory(**kwargs)
