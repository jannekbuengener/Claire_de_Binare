"""
E2E helpers for the paper trading suite.
"""

import os
import logging

logger = logging.getLogger(__name__)


def reset_circuit_breaker(redis_client) -> None:
    """Remove trapped circuit-breaker state before each E2E run."""
    stream = os.getenv("RISK_BOT_SHUTDOWN_STREAM", "stream.bot_shutdown")
    try:
        if redis_client.delete(stream):
            logger.info("Deleted residual circuit-breaker stream %s", stream)
        else:
            logger.info("Circuit-breaker stream %s not present", stream)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to delete %s: %s", stream, exc)

    try:
        redis_client.unlink(stream)
    except Exception:
        pass
