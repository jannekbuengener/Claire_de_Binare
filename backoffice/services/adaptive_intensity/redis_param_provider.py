"""
Redis Parameter Provider

Utility für Services (Signal Engine, Risk Manager) um dynamische Parameter
aus Redis zu holen statt aus statischen ENV-Variablen.

Usage in Signal Engine:
    from adaptive_intensity.redis_param_provider import get_dynamic_params

    params = get_dynamic_params(redis_client)
    threshold = params.get("signal_threshold_pct", DEFAULT_THRESHOLD)
"""

import json
import logging
from typing import Optional, Dict

import redis

logger = logging.getLogger(__name__)


def get_dynamic_params(
    redis_client: redis.Redis,
    fallback_to_env: bool = True
) -> Dict[str, float]:
    """
    Holt aktuelle dynamische Parameter aus Redis

    Args:
        redis_client: Redis Connection
        fallback_to_env: Fallback zu ENV wenn Redis leer (default: True)

    Returns:
        Dict mit aktuellen Parametern oder Empty Dict bei Fehler
    """
    try:
        # Hole aus Redis
        params_json = redis_client.get("adaptive_intensity:current_params")

        if not params_json:
            if fallback_to_env:
                logger.warning(
                    "No dynamic parameters in Redis - using ENV fallback"
                )
                return {}
            else:
                logger.error("No dynamic parameters available")
                return {}

        # Parse JSON
        params = json.loads(params_json)

        logger.debug(
            f"📥 Fetched dynamic params: "
            f"Score={params.get('performance_score', 0)*100:.1f}%, "
            f"Threshold={params.get('signal_threshold_pct', 0):.2f}%"
        )

        return params

    except Exception as e:
        logger.error(f"Failed to fetch dynamic parameters: {e}")
        return {}


def subscribe_to_param_updates(
    redis_client: redis.Redis,
    callback
):
    """
    Subscribet zu Parameter-Updates und ruft Callback bei Änderungen auf

    Args:
        redis_client: Redis Connection
        callback: Function(params_dict) die bei Updates aufgerufen wird

    Example:
        def on_params_updated(params):
            logger.info(f"New threshold: {params['signal_threshold_pct']}")

        subscribe_to_param_updates(redis_client, on_params_updated)
    """
    pubsub = redis_client.pubsub()
    pubsub.subscribe("adaptive_intensity:updates")

    logger.info("📡 Subscribed to adaptive_intensity:updates")

    for message in pubsub.listen():
        if message["type"] == "message":
            try:
                params = json.loads(message["data"])
                callback(params)
            except Exception as e:
                logger.error(f"Error processing parameter update: {e}")


# === Helper Functions für Services ===


def get_signal_engine_params(
    redis_client: redis.Redis,
    env_fallback: dict = None
) -> dict:
    """
    Holt Signal Engine Parameter (threshold, RSI, volume)

    Args:
        redis_client: Redis Connection
        env_fallback: ENV-Werte als Fallback

    Returns:
        Dict mit threshold_pct, rsi_threshold, volume_multiplier
    """
    dynamic = get_dynamic_params(redis_client)

    if not dynamic and env_fallback:
        return env_fallback

    return {
        "threshold_pct": dynamic.get("signal_threshold_pct", env_fallback.get("threshold_pct", 2.0)),
        "rsi_threshold": dynamic.get("rsi_threshold", env_fallback.get("rsi_threshold", 50.0)),
        "volume_multiplier": dynamic.get("volume_multiplier", env_fallback.get("volume_multiplier", 1.0)),
    }


def get_risk_manager_params(
    redis_client: redis.Redis,
    env_fallback: dict = None
) -> dict:
    """
    Holt Risk Manager Parameter (position, exposure)

    Args:
        redis_client: Redis Connection
        env_fallback: ENV-Werte als Fallback

    Returns:
        Dict mit max_position_pct, max_exposure_pct
    """
    dynamic = get_dynamic_params(redis_client)

    if not dynamic and env_fallback:
        return env_fallback

    return {
        "max_position_pct": dynamic.get("max_position_pct", env_fallback.get("max_position_pct", 0.10)),
        "max_exposure_pct": dynamic.get("max_exposure_pct", env_fallback.get("max_exposure_pct", 0.50)),
    }
