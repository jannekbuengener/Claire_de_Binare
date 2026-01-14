"""
Unit-Tests für Risk Manager Service.

Governance: CDB_AGENT_POLICY.md, CDB_RL_SAFETY_POLICY.md
"""

import pytest
import sys
import importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock
from core.domain.models import Signal

# Load risk service module dynamically to avoid sys.path conflicts
services_risk_path = Path(__file__).parent.parent.parent.parent / "services" / "risk"
service_file = services_risk_path / "service.py"
config_file = services_risk_path / "config.py"

# Import service module
spec_service = importlib.util.spec_from_file_location("risk_service_module", service_file)
risk_service = importlib.util.module_from_spec(spec_service)
spec_service.loader.exec_module(risk_service)

# Import config module
spec_config = importlib.util.spec_from_file_location("risk_config_module", config_file)
risk_config = importlib.util.module_from_spec(spec_config)
spec_config.loader.exec_module(risk_config)

# Create aliases
RiskManager = risk_service.RiskManager
RiskConfig = risk_config.RiskConfig
AllocationState = risk_service.AllocationState


@pytest.mark.unit
def test_service_initialization(mock_redis, mock_postgres):
    """
    Test: Risk Manager kann initialisiert werden.
    """
    # Mock config directly
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=0.30,
        max_daily_drawdown_pct=0.05,
        stop_loss_pct=0.02
    )

    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()

        assert manager is not None
        assert manager.config.max_position_pct == 0.10
        assert manager.config.max_total_exposure_pct == 0.30
        assert manager.config.max_daily_drawdown_pct == 0.05
        assert manager.running is False
        assert manager.allocation_state == {}


@pytest.mark.unit
def test_config_validation():
    """
    Test: Config wird korrekt validiert (Hard Limits).
    """
    # Valid config
    valid_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=0.30
    )
    assert valid_config.validate() is True

    # Invalid: max_position_pct <= 0
    invalid_config_1 = RiskConfig(
        max_position_pct=0.0,
        max_total_exposure_pct=0.30
    )
    with pytest.raises(ValueError, match="MAX_POSITION_PCT muss zwischen 0 und 1 liegen"):
        invalid_config_1.validate()

    # Invalid: max_position_pct > 1
    invalid_config_2 = RiskConfig(
        max_position_pct=1.5,
        max_total_exposure_pct=0.30
    )
    with pytest.raises(ValueError, match="MAX_POSITION_PCT muss zwischen 0 und 1 liegen"):
        invalid_config_2.validate()

    # Invalid: max_total_exposure_pct <= 0
    invalid_config_3 = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=0.0
    )
    with pytest.raises(ValueError, match="MAX_TOTAL_EXPOSURE_PCT muss zwischen 0 und 1 liegen"):
        invalid_config_3.validate()

    # Invalid: max_total_exposure_pct > 1
    invalid_config_4 = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=1.2
    )
    with pytest.raises(ValueError, match="MAX_TOTAL_EXPOSURE_PCT muss zwischen 0 und 1 liegen"):
        invalid_config_4.validate()


@pytest.mark.unit
def test_allocation_allowed():
    """
    Test: Allocation Cooldown blockiert zu häufige Trades.

    Governance: CDB_RL_SAFETY_POLICY.md (Deterministic Guardrails)
    """
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=0.30
    )

    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()
        import time

        # Test 1: No allocation set (allocation_pct = 0) blocks
        allowed, reason = manager._allocation_allowed("strategy_001")
        assert allowed is False
        assert "keine allokation" in reason.lower()

        # Test 2: Valid allocation allowed (no cooldown)
        manager.allocation_state["strategy_001"] = AllocationState(
            allocation_pct=0.5,
            cooldown_until=None
        )
        allowed, reason = manager._allocation_allowed("strategy_001")
        assert allowed is True
        assert "allokation ok" in reason.lower()

        # Test 3: Active cooldown blocks
        future_timestamp = int(time.time()) + 3600  # 1 hour from now
        manager.allocation_state["strategy_001"] = AllocationState(
            allocation_pct=0.5,
            cooldown_until=future_timestamp
        )

        allowed, reason = manager._allocation_allowed("strategy_001")
        assert allowed is False
        assert "cooldown" in reason.lower()

        # Test 4: Cooldown expired (past timestamp) allows
        past_timestamp = int(time.time()) - 3600  # 1 hour ago
        manager.allocation_state["strategy_001"] = AllocationState(
            allocation_pct=0.5,
            cooldown_until=past_timestamp
        )

        allowed, reason = manager._allocation_allowed("strategy_001")
        assert allowed is True
        assert "allokation ok" in reason.lower()


@pytest.mark.unit
def test_exposure_limit_bypassed_for_reduce_only_sell(mock_redis, mock_postgres):
    """
    Test: Reduce-only SELL wird nicht durch Max-Exposure geblockt.
    """
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=0.01,
        max_daily_drawdown_pct=0.05,
        stop_loss_pct=0.02,
        test_balance=100.0,
    )

    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()
        manager.allocation_state["paper"] = AllocationState(
            allocation_pct=0.5,
            cooldown_until=None,
        )

        original_positions = risk_service.risk_state.positions.copy()
        original_last_prices = risk_service.risk_state.last_prices.copy()
        original_total_exposure = risk_service.risk_state.total_exposure
        original_risk_off = risk_service.risk_off_active

        try:
            risk_service.risk_state.positions = {"BTCUSDT": 1.0}
            risk_service.risk_state.last_prices = {"BTCUSDT": 50000.0}
            risk_service.risk_state.total_exposure = 100000.0
            risk_service.risk_off_active = False
            manager.check_drawdown_limit = MagicMock(return_value=(True, "Drawdown OK"))
            manager.check_position_limit = MagicMock(return_value=(True, "Position OK"))
            manager.calculate_position_size = MagicMock(return_value=(0.1, None))

            signal = Signal(
                strategy_id="paper",
                symbol="BTCUSDT",
                side="SELL",
                price=50000.0,
                timestamp=1,
            )

            manager.check_exposure_limit = MagicMock(
                return_value=(False, "Max Exposure erreicht")
            )

            order = manager.process_signal(signal)
            assert order is not None
            assert order.side == "SELL"
            manager.check_exposure_limit.assert_not_called()
        finally:
            risk_service.risk_state.positions = original_positions
            risk_service.risk_state.last_prices = original_last_prices
            risk_service.risk_state.total_exposure = original_total_exposure
            risk_service.risk_off_active = original_risk_off
