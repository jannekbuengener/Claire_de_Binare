"""
E2E helpers for the paper trading suite.
"""

import os
import logging

logger = logging.getLogger(__name__)


def reset_circuit_breaker(redis_client) -> None:
    """
    Remove circuit-breaker state and verify E2E flag is set.

    IMPORTANT: This only resets Redis state. In-memory flags in services
    (bot_shutdown_active, blocked_strategy_ids, etc.) are NOT reset.
    Services must respect E2E_DISABLE_CIRCUIT_BREAKER=1 to ignore shutdown events.
    """
    stream = os.getenv("RISK_BOT_SHUTDOWN_STREAM", "stream.bot_shutdown")

    # Delete Redis stream
    try:
        deleted = redis_client.delete(stream)
        if deleted:
            logger.info("Deleted circuit-breaker stream %s", stream)
        else:
            logger.info("Circuit-breaker stream %s not present", stream)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to delete %s: %s", stream, exc)

    # Also unlink for completeness
    try:
        redis_client.unlink(stream)
    except Exception:
        pass

    # Verify E2E flag is set
    e2e_disable = os.getenv("E2E_DISABLE_CIRCUIT_BREAKER", "0")
    if e2e_disable.lower() not in {"1", "true", "yes"}:
        logger.warning(
            "⚠️ E2E_DISABLE_CIRCUIT_BREAKER is not set! "
            "Services may still honor shutdown events from previous runs."
        )
    else:
        logger.info("✅ E2E_DISABLE_CIRCUIT_BREAKER=1: Services will ignore shutdown events")
