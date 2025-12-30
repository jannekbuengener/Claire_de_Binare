"""
Redis Payload Sanitization Utility - Issue #349

Zentralisierte Payload-Sanitization für Redis Pub/Sub und Streams.
Verhindert NoneType Publishing Errors und enforced Contract-Konformität.
"""

from typing import Any, Dict


def sanitize_payload(payload: Dict[str, Any], *, strict: bool = False) -> Dict[str, Any]:
    """
    Sanitizes payload for Redis publishing (XADD, PUBLISH).

    Removes None values and normalizes types to prevent Redis errors.

    Args:
        payload: Raw payload dictionary
        strict: If True, raises ValueError on invalid types (default: False, coerces instead)

    Returns:
        Sanitized payload safe for Redis operations

    Example:
        >>> raw = {"symbol": "BTCUSDT", "price": "50000", "qty": None, "side": "buy"}
        >>> sanitize_payload(raw)
        {"symbol": "BTCUSDT", "price": "50000", "side": "buy"}

    Notes:
        - None values are filtered out (Redis XADD doesn't accept None)
        - Empty strings are preserved (valid Redis value)
        - Bytes are decoded to UTF-8 strings
        - Lists/dicts are JSON-serialized if strict=False
    """
    if not isinstance(payload, dict):
        raise TypeError(f"Payload must be dict, got {type(payload).__name__}")

    sanitized = {}

    for key, value in payload.items():
        # 1. Filter None values (Redis XADD rejects None)
        if value is None:
            continue

        # 2. Normalize types
        if isinstance(value, bytes):
            # Bytes → UTF-8 string
            try:
                value = value.decode("utf-8")
            except UnicodeDecodeError as e:
                if strict:
                    raise ValueError(f"Failed to decode bytes for key '{key}': {e}") from e
                # Fallback: repr() for debugging
                value = repr(value)

        elif isinstance(value, (list, dict, tuple)):
            # Complex types → JSON string (for Redis compatibility)
            if strict:
                raise ValueError(
                    f"Unsupported type {type(value).__name__} for key '{key}' (strict mode). "
                    "Use JSON serialization before calling sanitize_payload()."
                )
            # Non-strict: auto-serialize
            import json

            value = json.dumps(value)

        elif not isinstance(value, (str, int, float, bool)):
            # Unknown types → coerce to string (non-strict) or raise (strict)
            if strict:
                raise ValueError(
                    f"Unsupported type {type(value).__name__} for key '{key}'. "
                    "Allowed: str, int, float, bool, bytes."
                )
            value = str(value)

        # 3. Add to sanitized payload
        sanitized[key] = value

    return sanitized


def sanitize_market_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitizes market_data payload according to contract v1.0.

    Enforces:
    - Required fields: schema_version, source, symbol, ts_ms, price, trade_qty, side
    - Type constraints: ts_ms (int), price/trade_qty (str)
    - None-filtering

    Args:
        payload: Raw market_data payload

    Returns:
        Sanitized market_data payload

    Raises:
        ValueError: If required fields are missing or invalid types

    Example:
        >>> raw = {"source": "mexc", "symbol": "BTCUSDT", "ts_ms": 1735574400000,
        ...        "price": "50000.50", "trade_qty": "1.5", "side": "buy", "volume": None}
        >>> sanitize_market_data(raw)
        {"schema_version": "v1.0", "source": "mexc", "symbol": "BTCUSDT",
         "ts_ms": 1735574400000, "price": "50000.50", "trade_qty": "1.5", "side": "buy"}

    Notes:
        - Auto-adds schema_version="v1.0" if missing
        - Filters None values (e.g., volume=None)
        - Validates required fields exist
    """
    # 1. Basic sanitization (None-filtering)
    sanitized = sanitize_payload(payload, strict=False)

    # 2. Add schema_version if missing
    if "schema_version" not in sanitized:
        sanitized["schema_version"] = "v1.0"

    # 3. Validate required fields
    required = ["source", "symbol", "ts_ms", "price", "trade_qty", "side"]
    missing = [f for f in required if f not in sanitized]
    if missing:
        raise ValueError(f"Missing required fields for market_data: {missing}")

    # 4. Type enforcement
    if not isinstance(sanitized["ts_ms"], int):
        raise ValueError(f"ts_ms must be int, got {type(sanitized['ts_ms']).__name__}")

    if not isinstance(sanitized["price"], str):
        raise ValueError(f"price must be str (precision), got {type(sanitized['price']).__name__}")

    if not isinstance(sanitized["trade_qty"], str):
        raise ValueError(
            f"trade_qty must be str (precision), got {type(sanitized['trade_qty']).__name__}"
        )

    return sanitized


def sanitize_signal(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitizes signal payload according to contract v1.0.

    Enforces:
    - Required fields: schema_version, signal_id, strategy_id, symbol, side, timestamp
    - Type constraints: timestamp (int), strength/confidence (float 0.0-1.0)
    - None-filtering

    Args:
        payload: Raw signal payload

    Returns:
        Sanitized signal payload

    Raises:
        ValueError: If required fields are missing or invalid types/ranges

    Example:
        >>> raw = {"signal_id": "sig-001", "strategy_id": "momentum-v2", "symbol": "BTCUSDT",
        ...        "side": "BUY", "timestamp": 1735574400, "confidence": None, "reason": None}
        >>> sanitize_signal(raw)
        {"schema_version": "v1.0", "signal_id": "sig-001", "strategy_id": "momentum-v2",
         "symbol": "BTCUSDT", "side": "BUY", "timestamp": 1735574400, "type": "signal"}

    Notes:
        - Auto-adds schema_version="v1.0" if missing
        - Auto-adds type="signal" if missing
        - Filters None values (confidence, reason, etc.)
        - Validates strength/confidence ranges (0.0-1.0)
    """
    # 1. Basic sanitization (None-filtering)
    sanitized = sanitize_payload(payload, strict=False)

    # 2. Add defaults
    if "schema_version" not in sanitized:
        sanitized["schema_version"] = "v1.0"
    if "type" not in sanitized:
        sanitized["type"] = "signal"

    # 3. Validate required fields
    required = ["signal_id", "strategy_id", "symbol", "side", "timestamp"]
    missing = [f for f in required if f not in sanitized]
    if missing:
        raise ValueError(f"Missing required fields for signal: {missing}")

    # 4. Type enforcement
    if not isinstance(sanitized["timestamp"], int):
        # Auto-coerce float → int (common migration case)
        if isinstance(sanitized["timestamp"], float):
            sanitized["timestamp"] = int(sanitized["timestamp"])
        else:
            raise ValueError(
                f"timestamp must be int, got {type(sanitized['timestamp']).__name__}"
            )

    # 5. Range validation (if optional fields present)
    for field in ["strength", "confidence"]:
        if field in sanitized:
            val = sanitized[field]
            if not isinstance(val, (int, float)):
                raise ValueError(f"{field} must be numeric, got {type(val).__name__}")
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"{field} must be in range [0.0, 1.0], got {val}")

    return sanitized
