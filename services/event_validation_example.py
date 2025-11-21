"""Example integration of event validation in services.

This module demonstrates how to integrate JSON schema validation into
existing services. Use these patterns in your service implementations.
"""

from typing import Dict, Any
import logging
from services.event_validation import validate_event, is_valid_event, ValidationError

logger = logging.getLogger(__name__)


def publish_to_redis(channel: str, event: Dict[str, Any]) -> None:
    """Example: Validate event before publishing to Redis.

    Args:
        channel: Redis channel name
        event: Event dictionary to publish

    Raises:
        ValidationError: If event validation fails
    """
    # Validate event before publishing
    try:
        validate_event(event)
        logger.info(f"Publishing valid {event['type']} to {channel}")
        # redis_client.publish(channel, json.dumps(event))
    except ValidationError as e:
        logger.error(f"Event validation failed: {e}")
        raise


def process_market_data_event(event: Dict[str, Any]) -> None:
    """Example: Validate incoming market_data event.

    Args:
        event: Market data event from Redis

    Returns:
        None if validation fails (logged as warning)
    """
    if not is_valid_event(event, "market_data"):
        logger.warning(f"Received invalid market_data event: {event}")
        return

    # Process valid event
    symbol = event["symbol"]
    price = event["close"]
    logger.info(f"Processing {symbol} at {price}")


def generate_signal_with_validation(
    symbol: str,
    direction: str,
    strength: float,
    timestamp: int
) -> Dict[str, Any]:
    """Example: Generate and validate signal event before publishing.

    Args:
        symbol: Trading pair symbol
        direction: Signal direction (BUY/SELL/FLAT)
        strength: Signal strength (0.0 to 1.0)
        timestamp: Unix timestamp in milliseconds

    Returns:
        Validated signal event

    Raises:
        ValidationError: If generated event is invalid
    """
    signal = {
        "type": "signal",
        "symbol": symbol,
        "direction": direction,
        "strength": strength,
        "timestamp": timestamp,
        "strategy_id": "example_strategy"
    }

    # Validate before returning
    validate_event(signal, "signal")
    return signal


def risk_manager_example(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Example: Risk Manager validates input and output events.

    Args:
        signal: Incoming signal event

    Returns:
        Risk decision event
    """
    # Validate incoming signal
    try:
        validate_event(signal, "signal")
    except ValidationError as e:
        logger.error(f"Invalid signal received: {e}")
        # Return rejection decision
        return {
            "type": "risk_decision",
            "symbol": signal.get("symbol", "UNKNOWN"),
            "requested_direction": signal.get("direction", "UNKNOWN"),
            "approved": False,
            "reason_code": "INVALID_SIGNAL_FORMAT",
            "timestamp": signal.get("timestamp", 0)
        }

    # Process signal and create decision
    decision = {
        "type": "risk_decision",
        "symbol": signal["symbol"],
        "requested_direction": signal["direction"],
        "approved": True,
        "approved_size": 0.05,
        "reason_code": "OK",
        "timestamp": signal["timestamp"]
    }

    # Validate outgoing decision
    validate_event(decision, "risk_decision")
    return decision


def execution_service_example(order: Dict[str, Any]) -> Dict[str, Any]:
    """Example: Execution Service validates orders and results.

    Args:
        order: Incoming order event

    Returns:
        Order result event
    """
    # Validate incoming order
    validate_event(order, "order")

    # Simulate execution
    result = {
        "type": "order_result",
        "order_id": order["order_id"],
        "status": "FILLED",
        "symbol": order["symbol"],
        "filled_quantity": order["quantity"],
        "price": 35260.1,  # Simulated fill price
        "timestamp": order["timestamp"] + 1000,  # 1 second later
        "paper_trading": True
    }

    # Validate outgoing result
    validate_event(result, "order_result")
    return result


def alert_generator_example(
    level: str,
    code: str,
    message: str,
    timestamp: int,
    **kwargs
) -> Dict[str, Any]:
    """Example: Generate and validate alert events.

    Args:
        level: Alert level (CRITICAL, WARNING, INFO)
        code: Alert code
        message: Human-readable message
        timestamp: Unix timestamp in milliseconds
        **kwargs: Additional optional fields

    Returns:
        Validated alert event
    """
    alert = {
        "type": "alert",
        "level": level,
        "code": code,
        "message": message,
        "timestamp": timestamp,
        **kwargs
    }

    # Validate before returning
    validate_event(alert, "alert")
    return alert


# Integration pattern for existing services
class ValidatedEventPublisher:
    """Mixin class for services that publish events."""

    def publish_event(self, channel: str, event: Dict[str, Any]) -> None:
        """Publish event to Redis with validation.

        Args:
            channel: Redis channel
            event: Event to publish

        Raises:
            ValidationError: If validation fails
        """
        validate_event(event)
        # self.redis_client.publish(channel, json.dumps(event))
        logger.info(f"Published {event['type']} to {channel}")


class ValidatedEventConsumer:
    """Mixin class for services that consume events."""

    def consume_event(self, event: Dict[str, Any]) -> bool:
        """Consume and validate event from Redis.

        Args:
            event: Event from Redis

        Returns:
            True if event is valid, False otherwise
        """
        if not is_valid_event(event):
            logger.warning(f"Received invalid event: {event}")
            return False

        self.process_event(event)
        return True

    def process_event(self, event: Dict[str, Any]) -> None:
        """Process validated event (override in subclass)."""
        pass
