"""Projected position / exposure gates for Issue #4152 (S2)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.risk.config import RiskConfig
from core.domain.models import Signal
from services.risk.service import AllocationState, RiskManager
import services.risk.service as risk_service


def _allow_decide():
    return (
        risk_service.DECISION_ALLOW,
        None,
        {
            "contract_version": risk_service.DECISION_CONTRACT_VERSION,
            "signal_id": "sig-proj",
            "decision_id": "dec-proj",
        },
    )


@pytest.mark.unit
def test_unknown_price_blocks_position_limit(mock_redis, mock_postgres):
    manager = RiskManager()
    signal = Signal(
        signal_id="s1",
        strategy_id="paper",
        symbol="BTCUSDT",
        side="BUY",
        price=0.0,
        timestamp=1,
    )
    risk_service.risk_state.last_prices.pop("BTCUSDT", None)
    ok, reason = manager.check_position_limit(signal)
    assert ok is False
    assert "PRICE" in reason.upper() or "Preis" in reason or "price" in reason.lower()


@pytest.mark.unit
def test_invalid_quantity_blocks_projected_position_gate(mock_redis, mock_postgres):
    manager = RiskManager()
    ok, reason = manager.check_projected_position_limit(
        symbol="BTCUSDT",
        side="BUY",
        quantity=-1.0,
        price=50000.0,
    )
    assert ok is False
    assert "QUANTITY" in reason.upper() or "quantity" in reason.lower()


@pytest.mark.unit
def test_projected_symbol_position_just_below_at_and_above_cap(mock_redis, mock_postgres):
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=1.0,
        max_daily_drawdown_pct=0.05,
        test_balance=10_000.0,
    )
    # Cap = 1000 USDT
    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()
        manager.config = test_config
        risk_service.risk_state.positions = {"BTCUSDT": 0.0}
        risk_service.risk_state.pending_position_qty = {}
        risk_service.risk_state.last_prices = {"BTCUSDT": 1000.0}

        # just below: 0.999 BTC * 1000 = 999 < 1000
        ok_below, _ = manager.check_projected_position_limit(
            symbol="BTCUSDT", side="BUY", quantity=0.999, price=1000.0
        )
        assert ok_below is True

        # exactly at: 1.0 * 1000 = 1000 -> block (>=)
        ok_at, reason_at = manager.check_projected_position_limit(
            symbol="BTCUSDT", side="BUY", quantity=1.0, price=1000.0
        )
        assert ok_at is False
        assert "PROJECTED" in reason_at.upper() or "projected" in reason_at.lower()

        # just above
        ok_above, _ = manager.check_projected_position_limit(
            symbol="BTCUSDT", side="BUY", quantity=1.001, price=1000.0
        )
        assert ok_above is False


@pytest.mark.unit
def test_projected_position_includes_pending_and_order(mock_redis, mock_postgres):
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=1.0,
        test_balance=10_000.0,
    )
    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()
        manager.config = test_config
        risk_service.risk_state.positions = {"BTCUSDT": 0.5}  # 500 USDT
        risk_service.risk_state.pending_position_qty = {"BTCUSDT": 0.4}  # +400
        risk_service.risk_state.last_prices = {"BTCUSDT": 1000.0}

        # +0.2 => projected qty 1.1 => 1100 > 1000 cap
        ok, reason = manager.check_projected_position_limit(
            symbol="BTCUSDT", side="BUY", quantity=0.2, price=1000.0
        )
        assert ok is False
        assert "1100" in reason or "projected" in reason.lower()


@pytest.mark.unit
def test_increasing_order_size_cannot_reduce_projected_exposure(mock_redis, mock_postgres):
    manager = RiskManager()
    risk_service.risk_state.total_exposure = 100.0
    risk_service.risk_state.pending_exposure_usdt = 50.0

    small = manager.compute_projected_exposure_usdt(quantity=1.0, price=10.0)
    large = manager.compute_projected_exposure_usdt(quantity=2.0, price=10.0)
    assert large >= small
    assert large == 100.0 + 50.0 + 20.0


@pytest.mark.unit
def test_process_signal_blocks_when_projected_symbol_over_cap(mock_redis, mock_postgres):
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=1.0,
        max_daily_drawdown_pct=0.50,
        stop_loss_pct=0.02,
        test_balance=10_000.0,
        paper_auto_unwind=False,
    )
    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()
        manager.config = test_config
        manager.allocation_state["paper"] = AllocationState(allocation_pct=1.0)

        original_positions = risk_service.risk_state.positions.copy()
        original_prices = risk_service.risk_state.last_prices.copy()
        original_exposure = risk_service.risk_state.total_exposure
        original_pending = risk_service.risk_state.pending_exposure_usdt
        original_pending_qty = dict(
            getattr(risk_service.risk_state, "pending_position_qty", {})
        )

        try:
            # Existing 900 USDT position; sizing will try to add more past 1000 cap
            risk_service.risk_state.positions = {"BTCUSDT": 0.9}
            risk_service.risk_state.last_prices = {"BTCUSDT": 1000.0}
            risk_service.risk_state.total_exposure = 900.0
            risk_service.risk_state.pending_exposure_usdt = 0.0
            risk_service.risk_state.pending_position_qty = {}
            risk_service.risk_off_active = False

            manager.check_drawdown_limit = MagicMock(return_value=(True, "Drawdown OK"))
            manager.check_exposure_limit = MagicMock(return_value=(True, "Exposure OK"))
            manager.calculate_position_size = MagicMock(return_value=(0.2, None))
            manager._kill_switch_gate = MagicMock(return_value=(False, "", {}))
            manager._ensure_decision_contract_for_order = MagicMock()

            signal = Signal(
                signal_id="sig-over",
                strategy_id="paper",
                symbol="BTCUSDT",
                side="BUY",
                price=1000.0,
                timestamp=1,
            )
            with (
                patch.object(risk_service, "decide_trade", return_value=_allow_decide()),
                patch.object(manager, "_emit_risk_event", MagicMock()),
            ):
                order = manager.process_signal(signal)
            assert order is None
        finally:
            risk_service.risk_state.positions = original_positions
            risk_service.risk_state.last_prices = original_prices
            risk_service.risk_state.total_exposure = original_exposure
            risk_service.risk_state.pending_exposure_usdt = original_pending
            risk_service.risk_state.pending_position_qty = original_pending_qty
