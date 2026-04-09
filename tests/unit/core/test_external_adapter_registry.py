"""Unit tests for the static external adapter registry (#1579)."""

import pytest

from core.contracts.external_adapter_contracts import (
    ExecutionAdapterRequest,
    StrategyAdapterRequest,
)
from core.contracts.external_adapter_registry import (
    EXECUTION_ADAPTER_ENV_VAR,
    MEXC_BUILTIN,
    MOCK_BUILTIN,
    MOMENTUM_BUILTIN,
    SIGNAL_ADAPTER_ENV_VAR,
    BuiltinMomentumStrategyAdapter,
    MexcExecutionAdapter,
    MockExecutionAdapter,
    build_execution_adapter,
    build_strategy_adapter,
    default_execution_adapter_id,
    default_strategy_adapter_id,
    list_execution_adapter_ids,
    list_strategy_adapter_ids,
    resolve_execution_adapter_id,
    resolve_strategy_adapter_id,
)
from services.execution.mock_executor import MockExecutor


def test_registry_exposes_fixed_adapter_env_names() -> None:
    assert SIGNAL_ADAPTER_ENV_VAR == "SIGNAL_ADAPTER_ID"
    assert EXECUTION_ADAPTER_ENV_VAR == "EXECUTION_ADAPTER_ID"


def test_strategy_registry_is_static_and_defaulted_to_momentum_builtin() -> None:
    assert list_strategy_adapter_ids() == (MOMENTUM_BUILTIN,)
    assert default_strategy_adapter_id() == MOMENTUM_BUILTIN
    assert resolve_strategy_adapter_id(None) == MOMENTUM_BUILTIN


def test_execution_registry_is_static_and_defaults_follow_mock_trading() -> None:
    assert list_execution_adapter_ids() == (MOCK_BUILTIN, MEXC_BUILTIN)
    assert default_execution_adapter_id(mock_trading=True) == MOCK_BUILTIN
    assert default_execution_adapter_id(mock_trading=False) == MEXC_BUILTIN
    assert resolve_execution_adapter_id(None, mock_trading=True) == MOCK_BUILTIN
    assert resolve_execution_adapter_id(None, mock_trading=False) == MEXC_BUILTIN


def test_unknown_adapter_ids_fail_closed() -> None:
    with pytest.raises(KeyError, match="Unknown strategy adapter id"):
        resolve_strategy_adapter_id("does_not_exist")

    with pytest.raises(KeyError, match="Unknown execution adapter id"):
        resolve_execution_adapter_id("does_not_exist", mock_trading=True)


def test_built_in_momentum_strategy_adapter_emits_buy_candidate() -> None:
    adapter = build_strategy_adapter()
    assert isinstance(adapter, BuiltinMomentumStrategyAdapter)

    response = adapter.evaluate(
        StrategyAdapterRequest(
            symbol="BTCUSDT",
            market_event={"price": 50000.0},
            market_snapshot={"pct_change": 3.5, "volume": 200000.0},
            runtime_context={
                "threshold_pct": 3.0,
                "min_volume": 100000.0,
                "strategy_id": "paper",
                "bot_id": "bot-1",
            },
        )
    )

    assert len(response.signals) == 1
    signal = response.signals[0]
    assert signal.strategy_id == "paper"
    assert signal.symbol == "BTCUSDT"
    assert signal.side == "BUY"
    assert signal.reason == "Momentum: +3.5000% > 3.0%"
    assert signal.pct_change == pytest.approx(3.5)
    assert signal.metadata == {"adapter_id": MOMENTUM_BUILTIN, "bot_id": "bot-1"}
    assert response.diagnostics == {
        "adapter_id": MOMENTUM_BUILTIN,
        "status": "signal_emitted",
    }


def test_built_in_momentum_strategy_adapter_returns_no_signal_below_threshold() -> None:
    adapter = BuiltinMomentumStrategyAdapter()
    response = adapter.evaluate(
        StrategyAdapterRequest(
            symbol="BTCUSDT",
            market_event={},
            market_snapshot={"pct_change": 2.0, "volume": 200000.0},
            runtime_context={
                "threshold_pct": 3.0,
                "min_volume": 100000.0,
                "strategy_id": "paper",
            },
        )
    )

    assert response.signals == ()
    assert response.diagnostics == {
        "adapter_id": MOMENTUM_BUILTIN,
        "status": "no_signal",
        "pct_change": 2.0,
        "threshold_pct": 3.0,
        "volume": 200000.0,
        "min_volume": 100000.0,
    }


def test_mock_execution_adapter_wraps_current_mock_executor_path() -> None:
    adapter = MockExecutionAdapter(
        executor=MockExecutor(
            success_rate=1.0,
            min_latency_ms=0,
            max_latency_ms=0,
            base_slippage_pct=0.0,
        )
    )
    response = adapter.execute(
        ExecutionAdapterRequest(
            order={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "quantity": 0.01,
                "timestamp": 1700000000,
            },
            run_mode="paper",
            decision_contract_v1={"contract_version": "decision_contract_v1"},
            runtime_context={},
        )
    )

    assert response.status == "FILLED"
    assert response.order_id.startswith("MOCK_")
    assert response.filled_quantity == pytest.approx(0.01)
    assert response.raw_venue_payload == {"adapter_id": MOCK_BUILTIN}


def test_execution_registry_can_build_mexc_adapter_without_wiring_service() -> None:
    class DummyExecutor:
        def execute_order(self, order):
            class DummyResult:
                status = "FILLED"
                order_id = "MEXC_123"
                filled_quantity = order.quantity
                price = order.price
                error_message = None

            return DummyResult()

    adapter = build_execution_adapter(
        MEXC_BUILTIN, mock_trading=False, executor=DummyExecutor()
    )
    assert isinstance(adapter, MexcExecutionAdapter)

    response = adapter.execute(
        ExecutionAdapterRequest(
            order={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "quantity": 0.02,
                "price": 50000.0,
                "timestamp": 1700000000,
            },
            run_mode="paper",
            decision_contract_v1={"contract_version": "decision_contract_v1"},
            runtime_context={},
        )
    )

    assert response.status == "FILLED"
    assert response.order_id == "MEXC_123"
    assert response.venue_order_id == "MEXC_123"
    assert response.filled_quantity == pytest.approx(0.02)
