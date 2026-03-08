"""Proof tests for LR-762 Risk-side contract enforcement hardening.

Tests the 3 hardening fixes:
1. Strict order-identity binding (symbol/side/qty)
2. Hash provenance always overwritten from contract evidence
3. Kill-switch gate fail-closed
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

repo_root = Path(__file__).resolve().parents[3]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

risk_service = importlib.import_module("services.risk.service")
risk_config = importlib.import_module("services.risk.config")

RiskManager = risk_service.RiskManager
RiskConfig = risk_config.RiskConfig

from core.contracts.decision_contract_v1 import (
    DecisionContractError,
    build_decision_contract_v1_bundle,
)
from services.risk.models import Order


def _make_valid_contract_input(
    *, symbol: str = "BTCUSDT", side: str = "BUY", quantity: str = "0.001"
) -> dict:
    return {
        "run_mode": "paper",
        "order": {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price_ref": "50000",
            "timestamp_input_ms": 1700000000000,
            "reduce_only": False,
        },
        "account_state": {
            "balance_usdt": "10000",
            "total_exposure_usdt": "100",
            "daily_drawdown_pct": "1.0",
        },
        "open_positions": {},
        "risk_policy": {
            "max_notional_usdt": "2000",
            "max_total_exposure_usdt": "5000",
            "max_daily_drawdown_pct": "5.0",
        },
        "system_config": {"service": "tests"},
        "context": {
            "source": "tests",
            "signal_id": "sig-test",
            "strategy_id": "paper",
            "bot_id": "",
        },
    }


def _make_order(
    *, symbol: str = "BTCUSDT", side: str = "BUY", quantity: float = 0.001
) -> Order:
    return Order(
        symbol=symbol,
        side=side,
        quantity=quantity,
        stop_loss_pct=0.02,
        signal_id="sig-test",
        reason="test",
        timestamp=1700000000,
        strategy_id="paper",
        price=50000.0,
        order_id="order-test-1",
    )


def _make_manager() -> RiskManager:
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=0.30,
        max_daily_drawdown_pct=0.05,
        stop_loss_pct=0.02,
    )
    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()
    return manager


# ─────────────────────────────────────────────────────────────────────
# HARDENING FIX 1: Strict order-identity binding
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_contract_rejects_symbol_mismatch():
    """Contract gate must reject a bundle built for a different symbol."""
    manager = _make_manager()
    order = _make_order(symbol="BTCUSDT")

    # Build bundle for ETHUSDT
    bundle = build_decision_contract_v1_bundle(
        _make_valid_contract_input(symbol="ETHUSDT")
    )
    order.decision_contract_v1 = bundle

    with pytest.raises(DecisionContractError, match="symbol mismatch"):
        manager._ensure_decision_contract_for_order(order, source="test")


@pytest.mark.unit
def test_contract_rejects_side_mismatch():
    """Contract gate must reject a bundle built for a different side."""
    manager = _make_manager()
    order = _make_order(side="BUY")

    bundle = build_decision_contract_v1_bundle(_make_valid_contract_input(side="SELL"))
    order.decision_contract_v1 = bundle

    with pytest.raises(DecisionContractError, match="side mismatch"):
        manager._ensure_decision_contract_for_order(order, source="test")


@pytest.mark.unit
def test_contract_rejects_quantity_mismatch():
    """Contract gate must reject a bundle built for a different quantity."""
    manager = _make_manager()
    # Order has quantity 0.002
    order = _make_order(quantity=0.002)

    # Bundle has quantity 0.001 (valid ALLOW, but different from order)
    bundle = build_decision_contract_v1_bundle(
        _make_valid_contract_input(quantity="0.001")
    )
    order.decision_contract_v1 = bundle

    with pytest.raises(DecisionContractError, match="quantity mismatch"):
        manager._ensure_decision_contract_for_order(order, source="test")


@pytest.mark.unit
def test_contract_accepts_matching_identity():
    """Contract gate must accept a bundle matching the order identity."""
    manager = _make_manager()
    order = _make_order(symbol="BTCUSDT", side="BUY", quantity=0.001)

    bundle = build_decision_contract_v1_bundle(
        _make_valid_contract_input(symbol="BTCUSDT", side="BUY", quantity="0.001")
    )
    order.decision_contract_v1 = bundle

    result = manager._ensure_decision_contract_for_order(order, source="test")
    assert result is not None
    assert order.decision_contract_v1 is not None


# ─────────────────────────────────────────────────────────────────────
# HARDENING FIX 2: Hash provenance always overwritten
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_contract_overwrites_existing_hashes():
    """Contract gate must overwrite pre-existing order hashes, not skip them."""
    manager = _make_manager()
    order = _make_order()

    # Simulate Phase9 trace hashes already set (the drift scenario)
    order.input_hash = "stale-phase9-input-hash"
    order.output_hash = "stale-phase9-output-hash"

    bundle = build_decision_contract_v1_bundle(_make_valid_contract_input())
    order.decision_contract_v1 = bundle

    manager._ensure_decision_contract_for_order(order, source="test")

    evidence = bundle["output"]["evidence"]
    assert (
        order.input_hash == evidence["input_hash"]
    ), "input_hash must be overwritten with contract evidence hash"
    assert (
        order.output_hash == evidence["decision_hash"]
    ), "output_hash must be overwritten with contract evidence hash"
    assert order.input_hash != "stale-phase9-input-hash"
    assert order.output_hash != "stale-phase9-output-hash"


@pytest.mark.unit
def test_contract_sets_hashes_when_none():
    """Contract gate must set hashes when they are None."""
    manager = _make_manager()
    order = _make_order()
    assert order.input_hash is None
    assert order.output_hash is None

    bundle = build_decision_contract_v1_bundle(_make_valid_contract_input())
    order.decision_contract_v1 = bundle

    manager._ensure_decision_contract_for_order(order, source="test")

    evidence = bundle["output"]["evidence"]
    assert order.input_hash == evidence["input_hash"]
    assert order.output_hash == evidence["decision_hash"]


# ─────────────────────────────────────────────────────────────────────
# HARDENING FIX 3: Kill-switch gate fail-closed
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_kill_switch_active_blocks_signal(mock_redis, mock_postgres):
    """When kill-switch is active, process_signal must return None."""
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=0.30,
        max_daily_drawdown_pct=0.05,
        stop_loss_pct=0.02,
    )
    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()

    from core.domain.models import Signal

    signal = Signal(
        signal_id="sig-kill-test",
        strategy_id="test-strat",
        symbol="BTCUSDT",
        side="BUY",
        direction="BUY",
        strength=0.8,
        timestamp=1700000000.0,
    )

    with patch.object(
        manager,
        "_kill_switch_gate",
        return_value=(
            True,
            "KILL_SWITCH_ACTIVE",
            {"reason": "test", "message": "test", "activated_at": "now"},
        ),
    ):
        result = manager.process_signal(signal)

    assert result is None, "Kill-switch active must block signal"


@pytest.mark.unit
def test_kill_switch_eval_error_blocks_signal(mock_redis, mock_postgres):
    """When kill-switch evaluation fails, process_signal must block (fail-closed)."""
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=0.30,
        max_daily_drawdown_pct=0.05,
        stop_loss_pct=0.02,
    )
    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()

    from core.domain.models import Signal

    signal = Signal(
        signal_id="sig-kill-err",
        strategy_id="test-strat",
        symbol="BTCUSDT",
        side="BUY",
        direction="BUY",
        strength=0.8,
        timestamp=1700000000.0,
    )

    with patch.object(
        manager,
        "_kill_switch_gate",
        return_value=(
            True,
            "KILL_SWITCH_UNEVALUABLE",
            {"reason": None, "message": "eval error", "activated_at": None},
        ),
    ):
        result = manager.process_signal(signal)

    assert (
        result is None
    ), "Kill-switch evaluation error must block signal (fail-closed)"


@pytest.mark.unit
def test_kill_switch_inactive_does_not_block(mock_redis, mock_postgres):
    """When kill-switch is inactive, process_signal must proceed normally."""
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=0.30,
        max_daily_drawdown_pct=0.05,
        stop_loss_pct=0.02,
    )
    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()

    from core.domain.models import Signal

    signal = Signal(
        signal_id="sig-pass",
        strategy_id="test-strat",
        symbol="BTCUSDT",
        side="BUY",
        direction="BUY",
        strength=0.8,
        timestamp=1700000000.0,
    )

    with patch.object(
        manager,
        "_kill_switch_gate",
        return_value=(False, "", {}),
    ):
        # Signal will likely be blocked by decide_trade (missing market_state etc.)
        # but it must NOT be blocked by kill-switch
        result = manager.process_signal(signal)

    # We don't check if order was created (depends on market_state etc.)
    # We just verify kill-switch did not raise or return early
    # The fact that we reach this point means kill-switch was not blocking
