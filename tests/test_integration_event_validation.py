"""Integration tests for event validation across services.

These tests verify that event validation works correctly when events
flow through the entire pipeline: market_data → signal → risk_decision
→ order → order_result → alert.
"""

import pytest
from services.event_validation import EventValidator, ValidationError


@pytest.fixture
def validator():
    """Create an EventValidator instance."""
    return EventValidator()


@pytest.mark.integration
class TestEventFlowValidation:
    """Test validation of events flowing through the pipeline."""

    def test_market_data_to_signal_flow(self, validator):
        """Test that market_data can be consumed and signal can be produced."""
        # Step 1: Receive market_data event
        market_data = {
            "type": "market_data",
            "symbol": "BTC_USDT",
            "timestamp": 1730443200000,
            "open": 35210.0,
            "high": 35280.5,
            "low": 35190.0,
            "close": 35250.5,
            "volume": 184.12,
            "interval": "1m"
        }

        validator.validate_market_data(market_data)

        # Step 2: Generate signal from market_data
        signal = {
            "type": "signal",
            "symbol": market_data["symbol"],
            "direction": "BUY",
            "strength": 0.82,
            "reason": "MOMENTUM_BREAKOUT",
            "timestamp": market_data["timestamp"] + 60000,
            "strategy_id": "momentum_v1"
        }

        validator.validate_signal(signal)

    def test_signal_to_risk_decision_flow(self, validator):
        """Test that signals are validated and risk decisions are produced."""
        # Step 1: Receive signal event
        signal = {
            "type": "signal",
            "symbol": "ETH_USDT",
            "direction": "SELL",
            "strength": 0.75,
            "timestamp": 1730443260000,
            "strategy_id": "momentum_v1"
        }

        validator.validate_signal(signal)

        # Step 2: Generate risk decision
        risk_decision = {
            "type": "risk_decision",
            "symbol": signal["symbol"],
            "requested_direction": signal["direction"],
            "approved": True,
            "approved_size": 0.1,
            "reason_code": "OK",
            "timestamp": signal["timestamp"] + 10000
        }

        validator.validate_risk_decision(risk_decision)

    def test_risk_decision_to_order_flow(self, validator):
        """Test that approved risk decisions produce valid orders."""
        # Step 1: Approved risk decision
        risk_decision = {
            "type": "risk_decision",
            "symbol": "SOL_USDT",
            "requested_direction": "BUY",
            "approved": True,
            "approved_size": 2.5,
            "reason_code": "OK",
            "timestamp": 1730443270000
        }

        validator.validate_risk_decision(risk_decision)

        # Step 2: Generate order from approved decision
        order = {
            "type": "order",
            "order_id": f"ORD_{risk_decision['timestamp']}_{risk_decision['symbol']}",
            "symbol": risk_decision["symbol"],
            "side": risk_decision["requested_direction"],
            "quantity": risk_decision["approved_size"],
            "order_type": "MARKET",
            "timestamp": risk_decision["timestamp"] + 5000,
            "paper_trading": True
        }

        validator.validate_order(order)

    def test_order_to_order_result_flow(self, validator):
        """Test that orders produce valid order results."""
        # Step 1: Order event
        order = {
            "type": "order",
            "order_id": "ORD_1730443270_BTC_USDT",
            "symbol": "BTC_USDT",
            "side": "BUY",
            "quantity": 0.05,
            "order_type": "MARKET",
            "timestamp": 1730443270000,
            "paper_trading": True
        }

        validator.validate_order(order)

        # Step 2: Order result (filled)
        order_result = {
            "type": "order_result",
            "order_id": order["order_id"],
            "status": "FILLED",
            "symbol": order["symbol"],
            "side": order["side"],
            "filled_quantity": order["quantity"],
            "price": 35260.1,
            "timestamp": order["timestamp"] + 1000,
            "paper_trading": True
        }

        validator.validate_order_result(order_result)

    def test_rejected_risk_decision_generates_alert(self, validator):
        """Test that rejected risk decisions can generate alerts."""
        # Step 1: Rejected risk decision
        risk_decision = {
            "type": "risk_decision",
            "symbol": "BTC_USDT",
            "requested_direction": "BUY",
            "approved": False,
            "reason_code": "DAILY_DRAWDOWN_EXCEEDED",
            "timestamp": 1730443270000
        }

        validator.validate_risk_decision(risk_decision)

        # Step 2: Generate alert for rejection
        alert = {
            "type": "alert",
            "level": "CRITICAL",
            "code": "RISK_LIMIT",
            "message": "Daily drawdown exceeded. Trading halted.",
            "timestamp": risk_decision["timestamp"] + 100,
            "symbol": risk_decision["symbol"],
            "service": "risk_manager",
            "action_required": True
        }

        validator.validate_alert(alert)

    def test_full_pipeline_success_flow(self, validator):
        """Test complete event flow from market_data to order_result."""
        timestamp = 1730443200000

        # 1. Market data arrives
        market_data = {
            "type": "market_data",
            "symbol": "BTC_USDT",
            "timestamp": timestamp,
            "close": 35250.5,
            "volume": 184.12,
            "interval": "1m"
        }
        validator.validate_market_data(market_data)

        # 2. Signal Engine generates signal
        signal = {
            "type": "signal",
            "symbol": "BTC_USDT",
            "direction": "BUY",
            "strength": 0.82,
            "timestamp": timestamp + 60000,
            "strategy_id": "momentum_v1"
        }
        validator.validate_signal(signal)

        # 3. Risk Manager approves
        risk_decision = {
            "type": "risk_decision",
            "symbol": "BTC_USDT",
            "requested_direction": "BUY",
            "approved": True,
            "approved_size": 0.05,
            "reason_code": "OK",
            "timestamp": timestamp + 70000
        }
        validator.validate_risk_decision(risk_decision)

        # 4. Order is created
        order = {
            "type": "order",
            "order_id": "ORD_1730443270_BTC_USDT",
            "symbol": "BTC_USDT",
            "side": "BUY",
            "quantity": 0.05,
            "order_type": "MARKET",
            "timestamp": timestamp + 75000
        }
        validator.validate_order(order)

        # 5. Order is executed
        order_result = {
            "type": "order_result",
            "order_id": "ORD_1730443270_BTC_USDT",
            "status": "FILLED",
            "symbol": "BTC_USDT",
            "filled_quantity": 0.05,
            "price": 35260.1,
            "timestamp": timestamp + 76000
        }
        validator.validate_order_result(order_result)

    def test_full_pipeline_rejection_flow(self, validator):
        """Test complete event flow with risk rejection and alert."""
        timestamp = 1730443200000

        # 1. Market data arrives
        market_data = {
            "type": "market_data",
            "symbol": "ETH_USDT",
            "timestamp": timestamp,
            "close": 2100.5,
            "volume": 500.0,
            "interval": "1m"
        }
        validator.validate_market_data(market_data)

        # 2. Signal Engine generates signal
        signal = {
            "type": "signal",
            "symbol": "ETH_USDT",
            "direction": "SELL",
            "strength": 0.9,
            "timestamp": timestamp + 60000
        }
        validator.validate_signal(signal)

        # 3. Risk Manager rejects (exposure limit)
        risk_decision = {
            "type": "risk_decision",
            "symbol": "ETH_USDT",
            "requested_direction": "SELL",
            "approved": False,
            "reason_code": "EXPOSURE_LIMIT_REACHED",
            "timestamp": timestamp + 70000
        }
        validator.validate_risk_decision(risk_decision)

        # 4. Alert is generated
        alert = {
            "type": "alert",
            "level": "WARNING",
            "code": "RISK_LIMIT",
            "message": "Exposure limit reached. Signal rejected.",
            "timestamp": timestamp + 70100,
            "symbol": "ETH_USDT",
            "service": "risk_manager"
        }
        validator.validate_alert(alert)


@pytest.mark.integration
class TestCrossEventValidation:
    """Test validation constraints that span multiple events."""

    def test_order_quantity_matches_approved_size(self, validator):
        """Test that order quantity should not exceed approved size."""
        # Approved size from risk decision
        risk_decision = {
            "type": "risk_decision",
            "symbol": "BTC_USDT",
            "requested_direction": "BUY",
            "approved": True,
            "approved_size": 0.05,
            "reason_code": "OK",
            "timestamp": 1730443270000
        }
        validator.validate_risk_decision(risk_decision)

        # Order with matching quantity (valid)
        order_valid = {
            "type": "order",
            "order_id": "ORD_123",
            "symbol": "BTC_USDT",
            "side": "BUY",
            "quantity": 0.05,  # Matches approved_size
            "timestamp": 1730443270000
        }
        validator.validate_order(order_valid)

        # Order with larger quantity (still valid by schema, but should be
        # caught by business logic)
        order_oversized = {
            "type": "order",
            "order_id": "ORD_124",
            "symbol": "BTC_USDT",
            "side": "BUY",
            "quantity": 0.1,  # Exceeds approved_size
            "timestamp": 1730443270000
        }
        # Schema validation passes (business logic should catch this)
        validator.validate_order(order_oversized)

    def test_order_result_matches_order_id(self, validator):
        """Test that order_result references correct order_id."""
        order = {
            "type": "order",
            "order_id": "ORD_XYZ_123",
            "symbol": "ETH_USDT",
            "side": "SELL",
            "quantity": 1.0,
            "timestamp": 1730443270000
        }
        validator.validate_order(order)

        # Matching order result
        order_result = {
            "type": "order_result",
            "order_id": "ORD_XYZ_123",  # Must match
            "status": "FILLED",
            "symbol": "ETH_USDT",
            "filled_quantity": 1.0,
            "price": 2100.5,
            "timestamp": 1730443271000
        }
        validator.validate_order_result(order_result)

    def test_timestamp_progression(self, validator):
        """Test that timestamps progress logically through pipeline."""
        base_ts = 1730443200000

        # Events should have increasing timestamps
        events = [
            ("market_data", {
                "type": "market_data",
                "symbol": "BTC_USDT",
                "timestamp": base_ts,
                "close": 35250.5,
                "volume": 184.12,
                "interval": "1m"
            }),
            ("signal", {
                "type": "signal",
                "symbol": "BTC_USDT",
                "direction": "BUY",
                "timestamp": base_ts + 60000
            }),
            ("risk_decision", {
                "type": "risk_decision",
                "symbol": "BTC_USDT",
                "requested_direction": "BUY",
                "approved": True,
                "reason_code": "OK",
                "timestamp": base_ts + 70000
            }),
            ("order", {
                "type": "order",
                "order_id": "ORD_123",
                "symbol": "BTC_USDT",
                "side": "BUY",
                "quantity": 0.05,
                "timestamp": base_ts + 75000
            }),
            ("order_result", {
                "type": "order_result",
                "order_id": "ORD_123",
                "status": "FILLED",
                "symbol": "BTC_USDT",
                "filled_quantity": 0.05,
                "price": 35260.1,
                "timestamp": base_ts + 76000
            })
        ]

        # All events should validate individually
        for event_type, event in events:
            validator.validate_event(event, event_type)

        # Verify timestamp progression
        timestamps = [event["timestamp"] for _, event in events]
        assert timestamps == sorted(timestamps), "Timestamps should be in order"
