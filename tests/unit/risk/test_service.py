"""
Unit-Tests für Risk Manager Service.

Governance: CDB_AGENT_POLICY.md, CDB_RL_SAFETY_POLICY.md
"""

import pytest
import sys
import importlib
from pathlib import Path
from unittest.mock import patch, MagicMock
from core.domain.models import Signal

# Ensure repo root is on sys.path for package imports
repo_root = Path(__file__).resolve().parents[3]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Import risk modules as packages (needed for relative imports inside service)
risk_service = importlib.import_module("services.risk.service")
risk_config = importlib.import_module("services.risk.config")

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
        stop_loss_pct=0.02,
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
    valid_config = RiskConfig(max_position_pct=0.10, max_total_exposure_pct=0.30)
    assert valid_config.validate() is True

    # Invalid: max_position_pct <= 0
    invalid_config_1 = RiskConfig(max_position_pct=0.0, max_total_exposure_pct=0.30)
    with pytest.raises(
        ValueError, match="MAX_POSITION_PCT muss zwischen 0 und 1 liegen"
    ):
        invalid_config_1.validate()

    # Invalid: max_position_pct > 1
    invalid_config_2 = RiskConfig(max_position_pct=1.5, max_total_exposure_pct=0.30)
    with pytest.raises(
        ValueError, match="MAX_POSITION_PCT muss zwischen 0 und 1 liegen"
    ):
        invalid_config_2.validate()

    # Invalid: max_total_exposure_pct <= 0
    invalid_config_3 = RiskConfig(max_position_pct=0.10, max_total_exposure_pct=0.0)
    with pytest.raises(
        ValueError, match="MAX_TOTAL_EXPOSURE_PCT muss zwischen 0 und 1 liegen"
    ):
        invalid_config_3.validate()

    # Invalid: max_total_exposure_pct > 1
    invalid_config_4 = RiskConfig(max_position_pct=0.10, max_total_exposure_pct=1.2)
    with pytest.raises(
        ValueError, match="MAX_TOTAL_EXPOSURE_PCT muss zwischen 0 und 1 liegen"
    ):
        invalid_config_4.validate()


@pytest.mark.unit
def test_allocation_allowed():
    """
    Test: Allocation Cooldown blockiert zu häufige Trades.

    Governance: CDB_RL_SAFETY_POLICY.md (Deterministic Guardrails)
    """
    test_config = RiskConfig(max_position_pct=0.10, max_total_exposure_pct=0.30)

    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()
        import time

        # Test 1: No allocation set (allocation_pct = 0) blocks
        allowed, reason = manager._allocation_allowed("strategy_001")
        assert allowed is False
        assert "keine allokation" in reason.lower()

        # Test 2: Valid allocation allowed (no cooldown)
        manager.allocation_state["strategy_001"] = AllocationState(
            allocation_pct=0.5, cooldown_until=None
        )
        allowed, reason = manager._allocation_allowed("strategy_001")
        assert allowed is True
        assert "allokation ok" in reason.lower()

        # Test 3: Active cooldown blocks
        future_timestamp = int(time.time()) + 3600  # 1 hour from now
        manager.allocation_state["strategy_001"] = AllocationState(
            allocation_pct=0.5, cooldown_until=future_timestamp
        )

        allowed, reason = manager._allocation_allowed("strategy_001")
        assert allowed is False
        assert "cooldown" in reason.lower()

        # Test 4: Cooldown expired (past timestamp) allows
        past_timestamp = int(time.time()) - 3600  # 1 hour ago
        manager.allocation_state["strategy_001"] = AllocationState(
            allocation_pct=0.5, cooldown_until=past_timestamp
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
                signal_id="test-sig-001",
                strategy_id="paper",
                symbol="BTCUSDT",
                side="SELL",
                price=50000.0,
                timestamp=1,
            )

            manager.check_exposure_limit = MagicMock(
                return_value=(False, "Max Exposure erreicht")
            )

            with (
                patch.object(
                    risk_service,
                    "decide_trade",
                    return_value=(
                        risk_service.DECISION_ALLOW,
                        None,
                        {
                            "contract_version": risk_service.DECISION_CONTRACT_VERSION,
                            "signal_id": "test-sig-001",
                            "decision_id": "test-dec-001",
                        },
                    ),
                ),
                patch.object(manager, "_emit_risk_event", MagicMock()),
            ):
                order = manager.process_signal(signal)
            assert order is not None
            assert order.side == "SELL"
            manager.check_exposure_limit.assert_not_called()
        finally:
            risk_service.risk_state.positions = original_positions
            risk_service.risk_state.last_prices = original_last_prices
            risk_service.risk_state.total_exposure = original_total_exposure
            risk_service.risk_off_active = original_risk_off


@pytest.mark.unit
def test_proactive_unwind_triggers_on_blocked_buy(mock_redis, mock_postgres):
    """
    Test: Proactive auto-unwind generiert SELL wenn BUY blockiert wird (über Limit).

    Scenario:
    - Exposure > max_exposure
    - Open LONG position exists
    - BUY signal arrives → blocked by exposure limit
    - Proactive unwind should generate SELL order
    """
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=0.01,  # Very low limit (1 USD)
        max_daily_drawdown_pct=0.05,
        stop_loss_pct=0.02,
        test_balance=100.0,
        paper_auto_unwind=True,  # Enable auto-unwind
    )

    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()
        manager.allocation_state["paper"] = AllocationState(
            allocation_pct=0.5,
            cooldown_until=None,
        )

        # Save original state
        original_positions = risk_service.risk_state.positions.copy()
        original_last_prices = risk_service.risk_state.last_prices.copy()
        original_total_exposure = risk_service.risk_state.total_exposure
        original_risk_off = risk_service.risk_off_active
        original_stats = risk_service.stats.copy()

        try:
            # Setup: Open LONG position, exposure over limit
            risk_service.risk_state.positions = {"BTCUSDT": 0.001}  # 0.001 BTC
            risk_service.risk_state.last_prices = {"BTCUSDT": 50000.0}
            risk_service.risk_state.total_exposure = 50.0  # 50 USD (over 1 USD limit)
            risk_service.risk_off_active = False
            risk_service.stats["proactive_unwind_triggered"] = 0

            # Mock other checks to pass
            manager.check_drawdown_limit = MagicMock(return_value=(True, "Drawdown OK"))
            manager.check_position_limit = MagicMock(return_value=(True, "Position OK"))
            manager.calculate_position_size = MagicMock(return_value=(0.001, None))

            # Mock send_order to capture the unwind SELL
            sent_orders = []

            def mock_send_order(order):
                sent_orders.append(order)

            manager.send_order = MagicMock(side_effect=mock_send_order)

            # Incoming BUY signal (should be blocked)
            signal = Signal(
                signal_id="test-sig-002",
                strategy_id="paper",
                symbol="BTCUSDT",
                side="BUY",
                price=50000.0,
                timestamp=1,
            )

            # Process signal - should be blocked but trigger proactive unwind
            with (
                patch.object(
                    risk_service,
                    "decide_trade",
                    return_value=(
                        risk_service.DECISION_ALLOW,
                        None,
                        {
                            "contract_version": risk_service.DECISION_CONTRACT_VERSION,
                            "signal_id": "test-sig-002",
                            "decision_id": "test-dec-002",
                        },
                    ),
                ),
                patch.object(manager, "_emit_risk_event", MagicMock()),
            ):
                order = manager.process_signal(signal)

            # Verify: BUY signal was blocked
            assert order is None

            # Verify: Proactive unwind SELL was generated
            assert len(sent_orders) == 1
            unwind_order = sent_orders[0]
            assert unwind_order.side == "SELL"
            assert unwind_order.symbol == "BTCUSDT"
            assert unwind_order.quantity == 0.001  # Matches position size
            assert "proactive_unwind" in unwind_order.reason

            # Verify: Stats counter incremented
            assert risk_service.stats["proactive_unwind_triggered"] == 1

        finally:
            # Restore original state
            risk_service.risk_state.positions = original_positions
            risk_service.risk_state.last_prices = original_last_prices
            risk_service.risk_state.total_exposure = original_total_exposure
            risk_service.risk_off_active = original_risk_off
            risk_service.stats = original_stats


@pytest.mark.unit
def test_proactive_unwind_no_trigger_when_auto_unwind_disabled(
    mock_redis, mock_postgres
):
    """
    Test: Proactive unwind wird NICHT ausgelöst wenn PAPER_AUTO_UNWIND=false.
    """
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=0.01,
        max_daily_drawdown_pct=0.05,
        stop_loss_pct=0.02,
        test_balance=100.0,
        paper_auto_unwind=False,  # Disabled
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
            risk_service.risk_state.positions = {"BTCUSDT": 0.001}
            risk_service.risk_state.last_prices = {"BTCUSDT": 50000.0}
            risk_service.risk_state.total_exposure = 50.0
            risk_service.risk_off_active = False

            manager.check_drawdown_limit = MagicMock(return_value=(True, "Drawdown OK"))
            manager.check_position_limit = MagicMock(return_value=(True, "Position OK"))
            manager.calculate_position_size = MagicMock(return_value=(0.001, None))
            manager.send_order = MagicMock()

            signal = Signal(
                signal_id="test-sig-003",
                strategy_id="paper",
                symbol="BTCUSDT",
                side="BUY",
                price=50000.0,
                timestamp=1,
            )

            with (
                patch.object(
                    risk_service,
                    "decide_trade",
                    return_value=(
                        risk_service.DECISION_ALLOW,
                        None,
                        {
                            "contract_version": risk_service.DECISION_CONTRACT_VERSION,
                            "signal_id": "test-sig-003",
                            "decision_id": "test-dec-003",
                        },
                    ),
                ),
                patch.object(manager, "_emit_risk_event", MagicMock()),
            ):
                order = manager.process_signal(signal)

            # Verify: BUY blocked
            assert order is None

            # Verify: No unwind order sent (auto-unwind disabled)
            manager.send_order.assert_not_called()

        finally:
            risk_service.risk_state.positions = original_positions
            risk_service.risk_state.last_prices = original_last_prices
            risk_service.risk_state.total_exposure = original_total_exposure
            risk_service.risk_off_active = original_risk_off


@pytest.mark.unit
def test_proactive_unwind_no_trigger_when_no_open_positions(mock_redis, mock_postgres):
    """
    Test: Proactive unwind wird NICHT ausgelöst wenn keine offenen Positionen existieren.
    """
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=0.01,
        max_daily_drawdown_pct=0.05,
        stop_loss_pct=0.02,
        test_balance=100.0,
        paper_auto_unwind=True,
    )

    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()
        manager.allocation_state["paper"] = AllocationState(
            allocation_pct=0.5,
            cooldown_until=None,
        )

        original_positions = risk_service.risk_state.positions.copy()
        original_total_exposure = risk_service.risk_state.total_exposure
        original_risk_off = risk_service.risk_off_active

        try:
            # No open positions
            risk_service.risk_state.positions = {}
            risk_service.risk_state.total_exposure = 0.0
            risk_service.risk_off_active = False

            manager.check_drawdown_limit = MagicMock(return_value=(True, "Drawdown OK"))
            manager.check_position_limit = MagicMock(return_value=(True, "Position OK"))
            manager.calculate_position_size = MagicMock(return_value=(0.001, None))
            manager.send_order = MagicMock()

            signal = Signal(
                signal_id="test-sig-004",
                strategy_id="paper",
                symbol="BTCUSDT",
                side="BUY",
                price=50000.0,
                timestamp=1,
            )

            with (
                patch.object(
                    risk_service,
                    "decide_trade",
                    return_value=(
                        risk_service.DECISION_ALLOW,
                        None,
                        {
                            "contract_version": risk_service.DECISION_CONTRACT_VERSION,
                            "signal_id": "test-sig-004",
                            "decision_id": "test-dec-004",
                        },
                    ),
                ),
                patch.object(manager, "_emit_risk_event", MagicMock()),
            ):
                manager.process_signal(signal)

            # Verify: BUY might be blocked by other checks, but no unwind triggered
            manager.send_order.assert_not_called()

        finally:
            risk_service.risk_state.positions = original_positions
            risk_service.risk_state.total_exposure = original_total_exposure
            risk_service.risk_off_active = original_risk_off


@pytest.mark.unit
def test_check_position_limit_enforcement(mock_redis, mock_postgres):
    """
    Test: check_position_limit blockiert wenn Symbol bereits am Limit ist.
    """
    test_config = RiskConfig(
        max_position_pct=0.10,  # 10%
        test_balance=1000.0,  # Max 100 USD pro Position
    )

    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()

        # Setup: Symbol am Limit
        risk_service.risk_state.positions = {
            "BTCUSDT": 0.002
        }  # 0.002 * 50000 = 100 USD
        risk_service.risk_state.last_prices = {"BTCUSDT": 50000.0}

        signal = Signal(symbol="BTCUSDT", side="BUY", price=50000.0, timestamp=1)

        # Check: Sollte blockieren
        ok, reason = manager.check_position_limit(signal)
        assert ok is False
        assert "am Limit" in reason

        # Setup: Anderes Symbol nicht am Limit
        signal_2 = Signal(symbol="ETHUSDT", side="BUY", price=3000.0, timestamp=1)
        ok, reason = manager.check_position_limit(signal_2)
        assert ok is True


@pytest.mark.unit
def test_process_signal_attaches_compact_order_metadata(mock_redis, mock_postgres):
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=0.30,
        max_daily_drawdown_pct=0.05,
        stop_loss_pct=0.02,
        test_balance=1000.0,
    )

    with patch.object(risk_service, "config", test_config):
        manager = RiskManager()
        manager.allocation_state["paper"] = AllocationState(
            allocation_pct=0.5,
            cooldown_until=None,
        )
        manager.check_drawdown_limit = MagicMock(return_value=(True, "Drawdown OK"))
        manager.check_position_limit = MagicMock(return_value=(True, "Position OK"))
        manager.calculate_position_size = MagicMock(return_value=(0.001, None))
        manager._ensure_decision_contract_for_order = MagicMock(return_value={})

        original_last_prices = risk_service.risk_state.last_prices.copy()
        original_positions = risk_service.risk_state.positions.copy()
        original_total_exposure = risk_service.risk_state.total_exposure
        original_pending_exposure = risk_service.risk_state.pending_exposure_usdt
        original_pending_orders = risk_service.risk_state.pending_orders
        original_pending_reservations = (
            risk_service.risk_state.pending_reservations.copy()
        )
        original_risk_off = risk_service.risk_off_active

        try:
            risk_service.risk_state.last_prices = {"BTCUSDT": 50000.0}
            risk_service.risk_state.positions = {}
            risk_service.risk_state.total_exposure = 0.0
            risk_service.risk_state.pending_exposure_usdt = 0.0
            risk_service.risk_state.pending_orders = 0
            risk_service.risk_state.pending_reservations = {}
            risk_service.risk_off_active = False

            signal = Signal(
                signal_id="sig-1488",
                strategy_id="paper",
                bot_id="bot-1488",
                symbol="BTCUSDT",
                side="BUY",
                price=50000.0,
                timestamp=1700000000,
                ts_ms=1700000000123,
                reason="Momentum breakout",
            )

            evidence = {
                "contract_version": risk_service.DECISION_CONTRACT_VERSION,
                "signal_id": "sig-1488",
                "decision_id": "dec-1488",
                "trace_id": "trace-1488",
                "regime_id": 0,
                "return_1m": 1.0,
                "return_5m": 2.0,
                "price_change_5m": 2.0,
                "daily_drawdown_pct": 1.5,
                "total_exposure_pct": 12.0,
                "slippage_pct": 0.1,
                "staleness_s": 1.2,
                "data_silence_s": 0.8,
                "thresholds": {"return_1m_min": -2.0},
                "decision_context": {"inputs": {"regime_id": 0}},
                "policy_id": "policy-1",
                "policy_hash": "policy-hash",
                "input_hash": "input-hash",
                "output_hash": "output-hash",
                "timestamps_ms": {
                    "now_ms": 1700000000999,
                    "signal_ts_ms": 1700000000123,
                    "market_state_ts_ms": 1700000000000,
                },
            }

            with (
                patch.object(
                    risk_service,
                    "decide_trade",
                    return_value=(risk_service.DECISION_ALLOW, None, evidence),
                ),
                patch.object(manager, "_emit_risk_event", MagicMock()),
            ):
                order = manager.process_signal(signal)

            assert order is not None
            assert order.metadata == {
                "signal_id": "sig-1488",
                "strategy_id": "paper",
                "decision_id": "dec-1488",
                "trace_id": "trace-1488",
                "decision": "ALLOW",
                "decision_context": {"inputs": {"regime_id": 0}},
                "thresholds": {"return_1m_min": -2.0},
                "policy_id": "policy-1",
                "policy_hash": "policy-hash",
                "input_hash": "input-hash",
                "output_hash": "output-hash",
                "market_context": {
                    "regime_id": 0,
                    "return_1m": 1.0,
                    "return_5m": 2.0,
                    "price_change_5m": 2.0,
                },
                "freshness": {
                    "staleness_s": 1.2,
                    "data_silence_s": 0.8,
                    "timestamps_ms": {
                        "now_ms": 1700000000999,
                        "signal_ts_ms": 1700000000123,
                        "market_state_ts_ms": 1700000000000,
                    },
                },
            }
        finally:
            risk_service.risk_state.last_prices = original_last_prices
            risk_service.risk_state.positions = original_positions
            risk_service.risk_state.total_exposure = original_total_exposure
            risk_service.risk_state.pending_exposure_usdt = original_pending_exposure
            risk_service.risk_state.pending_orders = original_pending_orders
            risk_service.risk_state.pending_reservations = original_pending_reservations
            risk_service.risk_off_active = original_risk_off
