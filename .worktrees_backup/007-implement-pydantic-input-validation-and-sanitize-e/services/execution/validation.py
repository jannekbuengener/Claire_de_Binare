"""
Pydantic Validation Models for Execution Service
Claire de Binare Trading Bot

Provides comprehensive input validation for order payloads to address
penetration test finding M-01 (CVSS 5.3): Order payloads from Redis pub/sub
lack comprehensive validation.
"""

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from services.execution.models import Order


# Regex pattern for valid trading symbols (uppercase alphanumeric)
# Examples: BTCUSDT, ETHBTC, SOLUSDT
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]+$")


class OrderRequest(BaseModel):
    """
    Pydantic model for validating incoming order requests.

    Implements comprehensive validation for order payloads:
    - Positive quantity validation (> 0)
    - Valid symbol format (alphanumeric uppercase)
    - Valid side (BUY/SELL only)
    - Optional stop_loss_pct in valid range (0-100)
    """

    symbol: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Trading pair symbol (e.g., BTCUSDT)"
    )
    side: Literal["BUY", "SELL"] = Field(
        ...,
        description="Order side: BUY or SELL"
    )
    quantity: float = Field(
        ...,
        gt=0,
        description="Order quantity (must be positive)"
    )
    stop_loss_pct: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Optional stop loss percentage (0-100)"
    )
    strategy_id: Optional[str] = Field(
        default=None,
        description="Strategy identifier"
    )
    bot_id: Optional[str] = Field(
        default=None,
        description="Bot identifier"
    )
    client_id: Optional[str] = Field(
        default=None,
        description="Client identifier"
    )
    timestamp: Optional[int | float | str] = Field(
        default=None,
        description="Order timestamp"
    )
    type: Literal["order", None] = Field(
        default="order",
        description="Event type (must be 'order' or None)"
    )

    @field_validator("symbol")
    @classmethod
    def validate_symbol_format(cls, v: str) -> str:
        """
        Validate symbol is uppercase alphanumeric.

        Args:
            v: The symbol value to validate

        Returns:
            The validated symbol (uppercased)

        Raises:
            ValueError: If symbol contains invalid characters
        """
        # Normalize to uppercase
        v_upper = v.upper()

        if not SYMBOL_PATTERN.match(v_upper):
            raise ValueError(
                f"Symbol must be alphanumeric uppercase (e.g., BTCUSDT), got: {v}"
            )

        return v_upper

    @field_validator("side", mode="before")
    @classmethod
    def normalize_side(cls, v: str) -> str:
        """
        Normalize side to uppercase and validate.

        Args:
            v: The side value to validate

        Returns:
            The validated side (uppercased)

        Raises:
            ValueError: If side is not BUY or SELL
        """
        if not isinstance(v, str):
            raise ValueError(f"Side must be a string, got: {type(v).__name__}")

        v_upper = v.upper()

        # Handle LONG/SHORT aliases
        if v_upper == "LONG":
            return "BUY"
        if v_upper == "SHORT":
            return "SELL"

        if v_upper not in ("BUY", "SELL"):
            raise ValueError(
                f"Side must be BUY or SELL, got: {v}"
            )

        return v_upper

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, v) -> float:
        """
        Validate quantity is a positive number.

        Args:
            v: The quantity value to validate

        Returns:
            The validated quantity as float

        Raises:
            ValueError: If quantity is not positive
        """
        try:
            quantity = float(v)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Quantity must be a number, got: {v}") from e

        if quantity <= 0:
            raise ValueError(
                f"Quantity must be positive (> 0), got: {quantity}"
            )

        return quantity

    @field_validator("stop_loss_pct", mode="before")
    @classmethod
    def validate_stop_loss_pct(cls, v) -> Optional[float]:
        """
        Validate stop_loss_pct is in valid range (0-100).

        Args:
            v: The stop_loss_pct value to validate

        Returns:
            The validated stop_loss_pct as float or None

        Raises:
            ValueError: If stop_loss_pct is out of range
        """
        if v is None:
            return None

        try:
            pct = float(v)
        except (ValueError, TypeError) as e:
            raise ValueError(f"stop_loss_pct must be a number, got: {v}") from e

        if pct < 0 or pct > 100:
            raise ValueError(
                f"stop_loss_pct must be between 0 and 100, got: {pct}"
            )

        return pct

    @model_validator(mode="before")
    @classmethod
    def check_required_fields(cls, values: dict) -> dict:
        """
        Check that all required fields are present.

        Args:
            values: The input dictionary

        Returns:
            The validated dictionary

        Raises:
            ValueError: If required fields are missing
        """
        if not isinstance(values, dict):
            raise ValueError("Input must be a dictionary")

        required = ["symbol", "side", "quantity"]
        missing = [f for f in required if f not in values or values[f] is None]

        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        return values

    class Config:
        """Pydantic configuration"""
        # Allow extra fields to be ignored (forward compatibility)
        extra = "ignore"
        # Enable strict validation
        validate_assignment = True


class OrderValidationError(Exception):
    """
    Custom exception for order validation errors.

    Provides safe, sanitized error messages that do not expose
    internal implementation details.
    """

    def __init__(self, message: str, details: Optional[list[str]] = None):
        """
        Initialize validation error.

        Args:
            message: Safe, user-facing error message
            details: Optional list of specific validation errors
        """
        self.message = message
        self.details = details or []
        super().__init__(message)

    def to_dict(self) -> dict:
        """
        Convert to dictionary for API response.

        Returns:
            Dictionary with error message and details
        """
        result = {"error": self.message}
        if self.details:
            result["details"] = self.details
        return result


def validate_order_payload(payload: dict) -> Order:
    """
    Validate an order payload and convert to the Order dataclass.

    This function wraps Pydantic validation to provide:
    - Comprehensive input validation (quantity > 0, valid symbol, etc.)
    - Safe error messages that don't expose internal details
    - Compatibility with the existing Order dataclass

    Args:
        payload: Dictionary containing order data from Redis pub/sub
                 Expected keys: symbol, side, quantity, and optional
                 stop_loss_pct, strategy_id, bot_id, client_id, timestamp

    Returns:
        Order: Validated Order dataclass instance

    Raises:
        OrderValidationError: If validation fails, with safe error messages

    Example:
        >>> payload = {
        ...     "symbol": "BTCUSDT",
        ...     "side": "BUY",
        ...     "quantity": 1.5,
        ...     "stop_loss_pct": 5.0
        ... }
        >>> order = validate_order_payload(payload)
        >>> order.symbol
        'BTCUSDT'
    """
    if not isinstance(payload, dict):
        raise OrderValidationError(
            "Invalid order payload: expected a dictionary",
            details=["Payload must be a JSON object"]
        )

    try:
        # Validate using Pydantic model
        validated = OrderRequest.model_validate(payload)

        # Convert to Order dataclass
        return Order(
            symbol=validated.symbol,
            side=validated.side,
            quantity=validated.quantity,
            stop_loss_pct=validated.stop_loss_pct,
            strategy_id=validated.strategy_id,
            bot_id=validated.bot_id,
            client_id=validated.client_id,
            timestamp=validated.timestamp,
            type=validated.type or "order",
        )

    except ValidationError as e:
        # Extract safe error messages from Pydantic ValidationError
        safe_details = _extract_safe_validation_errors(e)
        raise OrderValidationError(
            "Order validation failed",
            details=safe_details
        ) from None  # Don't chain exception to hide internals


def _extract_safe_validation_errors(error: ValidationError) -> list[str]:
    """
    Extract safe, user-facing error messages from Pydantic ValidationError.

    This function sanitizes validation errors to prevent information disclosure
    while still providing useful feedback about what went wrong.

    Args:
        error: Pydantic ValidationError instance

    Returns:
        List of safe error message strings
    """
    safe_messages = []

    for err in error.errors():
        field_name = ".".join(str(loc) for loc in err.get("loc", []))
        error_type = err.get("type", "")
        msg = err.get("msg", "Invalid value")

        # Sanitize specific error types to prevent info disclosure
        if error_type == "missing":
            safe_messages.append(f"Missing required field: {field_name}")
        elif error_type in ("value_error", "type_error"):
            # Use the Pydantic message but ensure it doesn't expose internals
            # Our custom validators already return safe messages
            safe_messages.append(f"{field_name}: {msg}")
        elif error_type == "literal_error":
            safe_messages.append(f"{field_name}: Invalid value")
        elif "greater_than" in error_type:
            safe_messages.append(f"{field_name}: Value must be positive")
        elif "less_than" in error_type or "greater_than" in error_type:
            safe_messages.append(f"{field_name}: Value out of valid range")
        else:
            # Generic safe message for unknown error types
            safe_messages.append(f"{field_name}: {msg}")

    return safe_messages if safe_messages else ["Invalid order data"]


# Re-export ValidationError for convenience
__all__ = [
    "OrderRequest",
    "OrderValidationError",
    "ValidationError",
    "validate_order_payload",
    "SYMBOL_PATTERN",
]
