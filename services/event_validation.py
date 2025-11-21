"""Event validation using JSON schemas.

This module provides validation utilities for all event types in the Claire de
Binare trading system. Events are validated against JSON schemas before being
published to ensure data integrity across the event-driven architecture.

Usage:
    from services.event_validation import EventValidator, ValidationError

    validator = EventValidator()

    # Validate a market data event
    event = {
        "type": "market_data",
        "symbol": "BTC_USDT",
        "timestamp": 1730443200000,
        "close": 35250.5,
        "volume": 184.12,
        "interval": "1m"
    }

    try:
        validator.validate_event(event)
        print("Event is valid")
    except ValidationError as e:
        print(f"Validation error: {e}")
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import jsonschema
from jsonschema import Draft7Validator, ValidationError as JSONSchemaValidationError

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when an event fails schema validation."""

    def __init__(self, message: str, event_type: str, errors: list):
        super().__init__(message)
        self.event_type = event_type
        self.errors = errors


class EventValidator:
    """Validates events against JSON schemas.

    Attributes:
        schemas: Dictionary mapping event types to their JSON schemas.
        validators: Dictionary mapping event types to validator instances.
        strict_mode: If True, raises errors for unknown event types.
    """

    def __init__(
        self,
        schema_dir: Optional[Path] = None,
        strict_mode: bool = True
    ):
        """Initialize the event validator.

        Args:
            schema_dir: Path to directory containing JSON schemas.
                Defaults to project_root/schemas.
            strict_mode: If True, raises errors for unknown event types.
                If False, logs warnings instead.
        """
        if schema_dir is None:
            # Default: schemas directory in project root
            schema_dir = Path(__file__).parent.parent / "schemas"

        self.schema_dir = Path(schema_dir)
        self.strict_mode = strict_mode
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self.validators: Dict[str, Draft7Validator] = {}

        self._load_schemas()

    def _load_schemas(self) -> None:
        """Load all JSON schemas from the schema directory."""
        if not self.schema_dir.exists():
            logger.warning(f"Schema directory not found: {self.schema_dir}")
            return

        schema_files = {
            "market_data": "market_data.schema.json",
            "signal": "signal.schema.json",
            "risk_decision": "risk_decision.schema.json",
            "order": "order.schema.json",
            "order_result": "order_result.schema.json",
            "alert": "alert.schema.json",
        }

        for event_type, filename in schema_files.items():
            schema_path = self.schema_dir / filename
            if schema_path.exists():
                try:
                    with open(schema_path, 'r') as f:
                        schema = json.load(f)
                    self.schemas[event_type] = schema
                    self.validators[event_type] = Draft7Validator(schema)
                    logger.debug(f"Loaded schema for {event_type}")
                except Exception as e:
                    logger.error(f"Failed to load schema {filename}: {e}")
            else:
                logger.warning(f"Schema file not found: {schema_path}")

        logger.info(f"Loaded {len(self.schemas)} event schemas")

    def validate_event(
        self,
        event: Dict[str, Any],
        event_type: Optional[str] = None
    ) -> None:
        """Validate an event against its JSON schema.

        Args:
            event: The event dictionary to validate.
            event_type: Optional event type override. If not provided,
                extracted from event['type'].

        Raises:
            ValidationError: If the event fails validation.
            ValueError: If event_type cannot be determined.
        """
        # Determine event type
        if event_type is None:
            event_type = event.get("type")

        if not event_type:
            raise ValueError("Cannot determine event type (missing 'type' field)")

        # Check if we have a schema for this event type
        if event_type not in self.validators:
            msg = f"No schema found for event type: {event_type}"
            if self.strict_mode:
                raise ValidationError(msg, event_type, [])
            else:
                logger.warning(msg)
                return

        # Validate against schema
        validator = self.validators[event_type]
        errors = list(validator.iter_errors(event))

        if errors:
            error_messages = [
                f"{error.path or 'root'}: {error.message}"
                for error in errors
            ]
            msg = f"Event validation failed for {event_type}: {'; '.join(error_messages)}"
            logger.warning(msg)
            raise ValidationError(msg, event_type, error_messages)

        logger.debug(f"Event {event_type} validated successfully")

    def validate_market_data(self, event: Dict[str, Any]) -> None:
        """Validate a market_data event."""
        self.validate_event(event, "market_data")

    def validate_signal(self, event: Dict[str, Any]) -> None:
        """Validate a signal event."""
        self.validate_event(event, "signal")

    def validate_risk_decision(self, event: Dict[str, Any]) -> None:
        """Validate a risk_decision event."""
        self.validate_event(event, "risk_decision")

    def validate_order(self, event: Dict[str, Any]) -> None:
        """Validate an order event."""
        self.validate_event(event, "order")

    def validate_order_result(self, event: Dict[str, Any]) -> None:
        """Validate an order_result event."""
        self.validate_event(event, "order_result")

    def validate_alert(self, event: Dict[str, Any]) -> None:
        """Validate an alert event."""
        self.validate_event(event, "alert")

    def is_valid(
        self,
        event: Dict[str, Any],
        event_type: Optional[str] = None
    ) -> bool:
        """Check if an event is valid without raising an exception.

        Args:
            event: The event dictionary to validate.
            event_type: Optional event type override.

        Returns:
            True if the event is valid, False otherwise.
        """
        try:
            self.validate_event(event, event_type)
            return True
        except (ValidationError, ValueError):
            return False


# Global validator instance (singleton pattern)
_global_validator: Optional[EventValidator] = None


def get_validator() -> EventValidator:
    """Get the global EventValidator instance.

    Returns:
        The global EventValidator instance (creates it if needed).
    """
    global _global_validator
    if _global_validator is None:
        _global_validator = EventValidator()
    return _global_validator


def validate_event(event: Dict[str, Any], event_type: Optional[str] = None) -> None:
    """Convenience function to validate an event using the global validator.

    Args:
        event: The event dictionary to validate.
        event_type: Optional event type override.

    Raises:
        ValidationError: If the event fails validation.
    """
    validator = get_validator()
    validator.validate_event(event, event_type)


def is_valid_event(event: Dict[str, Any], event_type: Optional[str] = None) -> bool:
    """Convenience function to check if an event is valid.

    Args:
        event: The event dictionary to validate.
        event_type: Optional event type override.

    Returns:
        True if the event is valid, False otherwise.
    """
    validator = get_validator()
    return validator.is_valid(event, event_type)
