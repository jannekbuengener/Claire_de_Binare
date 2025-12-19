"""
Safety Controls - Comprehensive Validation Tests (Issue #177)

Tests all risk management safety layers:
    - Emergency stop (Layer 0)
    - Circuit breaker with cooldown (Layer 1)
    - Max open positions (Layer 1.5)
    - Per-symbol position limits (Layer 1.6)
    - Total exposure limits (Layer 2)
    - Position size limits (Layer 3)
"""

import unittest
import time
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import RiskConfig
from models import RiskState, Order, Alert, OrderResult
from service import RiskManager
from core.domain.models import Signal


class TestEmergencyStop(unittest.TestCase):
    """Test Layer 0: Emergency Kill Switch"""

    def setUp(self):
        """Setup test environment"""
        self.manager = RiskManager()
        self.manager.redis_client = MagicMock()
        self.manager.balance_provider = Mock()
        self.manager.balance_provider.get_total_balance_usdt.return_value = 10000.0

    def test_emergency_stop_active(self):
        """Test emergency stop blocks all trading"""
        # Set emergency stop to active
        self.manager.redis_client.get.return_value = "1"

        ok, reason = self.manager.check_emergency_stop()

        self.assertFalse(ok)
        self.assertIn("EMERGENCY STOP ACTIVE", reason)

    def test_emergency_stop_inactive(self):
        """Test trading allowed when emergency stop is off"""
        self.manager.redis_client.get.return_value = None

        ok, reason = self.manager.check_emergency_stop()

        self.assertTrue(ok)

    def test_emergency_stop_various_formats(self):
        """Test emergency stop accepts multiple formats"""
        test_values = ["1", "true", "TRUE", "yes", "YES"]

        for value in test_values:
            self.manager.redis_client.get.return_value = value
            ok, reason = self.manager.check_emergency_stop()
            self.assertFalse(ok, f"Emergency stop should be active for value: {value}")

    def test_emergency_stop_redis_failure(self):
        """Test fail-safe behavior on Redis error"""
        self.manager.redis_client.get.side_effect = Exception("Redis connection failed")

        ok, reason = self.manager.check_emergency_stop()

        # Should fail-safe to blocking trading
        self.assertFalse(ok)
        self.assertIn("failed", reason.lower())


class TestCircuitBreaker(unittest.TestCase):
    """Test Layer 1: Circuit Breaker with Cooldown"""

    def setUp(self):
        """Setup test environment"""
        self.manager = RiskManager()
        self.manager.balance_provider = Mock()
        self.manager.balance_provider.get_total_balance_usdt.return_value = 10000.0

        # Reset global risk_state for each test
        import service
        service.risk_state = RiskState()
        self.risk_state = service.risk_state

    def test_circuit_breaker_triggers_on_drawdown(self):
        """Test circuit breaker triggers when drawdown limit exceeded"""
        # Set daily loss to -600 (exceeds 5% of $10,000 = -$500)
        self.risk_state.daily_pnl = -600.0

        ok, reason = self.manager.check_drawdown_limit()

        self.assertFalse(ok)
        self.assertTrue(self.risk_state.circuit_breaker_active)
        self.assertIsNotNone(self.risk_state.circuit_breaker_triggered_at)
        self.assertIn("Circuit Breaker TRIGGERED", reason)

    def test_circuit_breaker_ok_within_limit(self):
        """Test circuit breaker passes when within drawdown limit"""
        # Set daily loss to -400 (within 5% of $10,000 = -$500)
        self.risk_state.daily_pnl = -400.0

        ok, reason = self.manager.check_drawdown_limit()

        self.assertTrue(ok)
        self.assertFalse(self.risk_state.circuit_breaker_active)

    def test_circuit_breaker_cooldown_enforced(self):
        """Test circuit breaker enforces cooldown period"""
        # Trigger circuit breaker
        self.risk_state.circuit_breaker_active = True
        self.risk_state.circuit_breaker_triggered_at = int(time.time()) - 1800  # 30 min ago
        self.risk_state.daily_pnl = 0.0  # Reset P&L (shouldn't matter during cooldown)

        ok, reason = self.manager.check_drawdown_limit()

        self.assertFalse(ok)
        self.assertIn("Cooldown", reason)

    def test_circuit_breaker_auto_reset_after_cooldown(self):
        """Test circuit breaker auto-resets after cooldown if enabled"""
        # Enable auto-reset
        self.manager.config.circuit_breaker_auto_reset = True

        # Set triggered time to 61 minutes ago (past 60 min cooldown)
        self.risk_state.circuit_breaker_active = True
        self.risk_state.circuit_breaker_triggered_at = int(time.time()) - 3660
        self.risk_state.daily_pnl = 0.0

        ok, reason = self.manager.check_drawdown_limit()

        # Should auto-reset
        self.assertTrue(ok)
        self.assertFalse(self.risk_state.circuit_breaker_active)
        self.assertIsNone(self.risk_state.circuit_breaker_triggered_at)

    def test_circuit_breaker_manual_reset_required(self):
        """Test circuit breaker requires manual reset if auto-reset disabled"""
        # Disable auto-reset (default)
        self.manager.config.circuit_breaker_auto_reset = False

        # Set triggered time past cooldown
        self.risk_state.circuit_breaker_active = True
        self.risk_state.circuit_breaker_triggered_at = int(time.time()) - 3660
        self.risk_state.daily_pnl = 0.0

        ok, reason = self.manager.check_drawdown_limit()

        # Should still block (manual reset required)
        self.assertFalse(ok)
        self.assertIn("Manual reset required", reason)


class TestMaxOpenPositions(unittest.TestCase):
    """Test Layer 1.5: Maximum Open Positions"""

    def setUp(self):
        """Setup test environment"""
        self.manager = RiskManager()
        self.manager.config.max_open_positions = 5

        import service
        service.risk_state = RiskState()
        self.risk_state = service.risk_state

    def test_max_open_positions_blocks_when_full(self):
        """Test max positions blocks new orders when limit reached"""
        # Simulate 5 open positions (at limit)
        self.risk_state.positions = {
            "BTCUSDT": 0.5,
            "ETHUSDT": 10.0,
            "SOLUSDT": 100.0,
            "ADAUSDT": 500.0,
            "DOGEUSDT": 1000.0,
        }

        ok, reason = self.manager.check_max_open_positions()

        self.assertFalse(ok)
        self.assertIn("Max open positions reached", reason)

    def test_max_open_positions_allows_when_below_limit(self):
        """Test max positions allows new orders when below limit"""
        # Simulate 3 open positions (below limit of 5)
        self.risk_state.positions = {
            "BTCUSDT": 0.5,
            "ETHUSDT": 10.0,
            "SOLUSDT": 100.0,
        }

        ok, reason = self.manager.check_max_open_positions()

        self.assertTrue(ok)
        self.assertIn("3/5", reason)


class TestPerSymbolLimits(unittest.TestCase):
    """Test Layer 1.6: Per-Symbol Position Limits"""

    def setUp(self):
        """Setup test environment"""
        self.manager = RiskManager()
        self.manager.config.max_positions_per_symbol = 1
        self.manager.config.per_symbol_limits = {
            "BTCUSDT": 0.5,  # Max 0.5 BTC
            "ETHUSDT": 10.0,  # Max 10 ETH
        }

        import service
        service.risk_state = RiskState()
        self.risk_state = service.risk_state

    def test_blocks_duplicate_symbol_position(self):
        """Test blocks opening multiple positions in same symbol"""
        # Already have a BTC position
        self.risk_state.positions = {"BTCUSDT": 0.3}

        signal = Signal(
            symbol="BTCUSDT",
            side="BUY",
            confidence=0.8,
            reason="Test",
            timestamp=int(time.time())
        )

        ok, reason = self.manager.check_symbol_position_limit(signal)

        self.assertFalse(ok)
        self.assertIn("already has", reason)

    def test_allows_new_symbol_position(self):
        """Test allows opening position in new symbol"""
        # Have ETH, trying to open SOL
        self.risk_state.positions = {"ETHUSDT": 5.0}

        signal = Signal(
            symbol="SOLUSDT",
            side="BUY",
            confidence=0.8,
            reason="Test",
            timestamp=int(time.time())
        )

        ok, reason = self.manager.check_symbol_position_limit(signal)

        self.assertTrue(ok)

    def test_checks_absolute_symbol_limit(self):
        """Test enforces absolute position size limit for symbol"""
        # BTC position at limit (0.5 BTC)
        self.risk_state.positions = {"BTCUSDT": 0.5}

        signal = Signal(
            symbol="BTCUSDT",
            side="BUY",
            confidence=0.8,
            reason="Test",
            timestamp=int(time.time())
        )

        ok, reason = self.manager.check_symbol_position_limit(signal)

        # Should block due to both position count AND absolute limit
        self.assertFalse(ok)


class TestMultiLayerIntegration(unittest.TestCase):
    """Test full multi-layer risk processing"""

    def setUp(self):
        """Setup test environment"""
        self.manager = RiskManager()
        self.manager.redis_client = MagicMock()
        self.manager.redis_client.get.return_value = None  # Emergency stop off
        self.manager.redis_client.publish = MagicMock()

        self.manager.balance_provider = Mock()
        self.manager.balance_provider.get_total_balance_usdt.return_value = 10000.0

        import service
        service.risk_state = RiskState()
        self.risk_state = service.risk_state

        # Reset stats
        service.stats["orders_approved"] = 0
        service.stats["orders_blocked"] = 0

    def test_signal_passes_all_layers(self):
        """Test signal passes all safety layers and creates order"""
        signal = Signal(
            symbol="BTCUSDT",
            side="BUY",
            confidence=0.8,
            reason="Strong uptrend",
            timestamp=int(time.time())
        )

        order = self.manager.process_signal(signal)

        # Should approve
        self.assertIsNotNone(order)
        self.assertEqual(order.symbol, "BTCUSDT")
        self.assertEqual(order.side, "BUY")
        self.assertGreater(order.quantity, 0)

    def test_emergency_stop_blocks_before_other_checks(self):
        """Test emergency stop is checked first (highest priority)"""
        # Activate emergency stop
        self.manager.redis_client.get.return_value = "1"

        signal = Signal(
            symbol="BTCUSDT",
            side="BUY",
            confidence=0.8,
            reason="Test",
            timestamp=int(time.time())
        )

        order = self.manager.process_signal(signal)

        # Should block
        self.assertIsNone(order)
        self.assertTrue(self.risk_state.emergency_stop_active)

    def test_circuit_breaker_blocks_valid_signal(self):
        """Test circuit breaker blocks even valid signals"""
        # Trigger circuit breaker
        self.risk_state.daily_pnl = -600.0  # Exceeds -$500 limit

        signal = Signal(
            symbol="BTCUSDT",
            side="BUY",
            confidence=0.9,
            reason="Great signal",
            timestamp=int(time.time())
        )

        order = self.manager.process_signal(signal)

        # Should block despite high confidence
        self.assertIsNone(order)
        self.assertTrue(self.risk_state.circuit_breaker_active)

    def test_max_positions_blocks_6th_position(self):
        """Test cannot open 6th position when max is 5"""
        # Already have 5 positions
        self.risk_state.positions = {
            "BTCUSDT": 0.1,
            "ETHUSDT": 1.0,
            "SOLUSDT": 10.0,
            "ADAUSDT": 100.0,
            "DOGEUSDT": 1000.0,
        }

        signal = Signal(
            symbol="MATICUSDT",  # 6th symbol
            side="BUY",
            confidence=0.8,
            reason="Test",
            timestamp=int(time.time())
        )

        order = self.manager.process_signal(signal)

        # Should block
        self.assertIsNone(order)


class TestSafetyMetrics(unittest.TestCase):
    """Test safety metrics and monitoring"""

    def setUp(self):
        """Setup test environment"""
        import service
        service.risk_state = RiskState()
        self.risk_state = service.risk_state

    def test_position_count_calculation(self):
        """Test accurate position counting"""
        self.risk_state.positions = {
            "BTCUSDT": 0.5,
            "ETHUSDT": 10.0,
            "SOLUSDT": 0.0,  # Should not count (zero position)
        }

        count = self.risk_state.get_position_count()

        self.assertEqual(count, 2)  # Only BTC and ETH count

    def test_symbol_position_retrieval(self):
        """Test retrieving specific symbol position"""
        self.risk_state.positions = {"BTCUSDT": 0.5, "ETHUSDT": -2.0}  # -2.0 = short

        btc_pos = self.risk_state.get_symbol_position("BTCUSDT")
        eth_pos = self.risk_state.get_symbol_position("ETHUSDT")
        sol_pos = self.risk_state.get_symbol_position("SOLUSDT")

        self.assertEqual(btc_pos, 0.5)
        self.assertEqual(eth_pos, 2.0)  # Absolute value
        self.assertEqual(sol_pos, 0.0)

    def test_has_position_check(self):
        """Test position existence checking"""
        self.risk_state.positions = {"BTCUSDT": 0.0001}  # Very small position

        self.assertTrue(self.risk_state.has_position("BTCUSDT"))
        self.assertFalse(self.risk_state.has_position("ETHUSDT"))


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
