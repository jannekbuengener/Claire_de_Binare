"""
E2E helpers for the paper trading suite.
"""

import logging
import os

logger = logging.getLogger(__name__)

_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def _normalize_env(name: str) -> str:
    return os.getenv(name, "").strip().lower()


def _truthy_env(name: str) -> bool:
    return _normalize_env(name) in _TRUTHY_VALUES


def get_risk_namespace() -> str:
    namespace = os.getenv("RISK_NAMESPACE", "").strip()
    if namespace:
        return namespace
    run_id = os.getenv("E2E_RUN_ID", "").strip()
    if run_id:
        return f"e2e.{run_id}"
    return ""


def apply_namespace(namespace: str, value: str) -> str:
    if not namespace:
        return value
    prefix = f"{namespace}."
    if value.startswith(prefix):
        return value
    return f"{prefix}{value}"


def resolve_stream_name(env_names: tuple[str, ...], default: str) -> str:
    namespace = get_risk_namespace()
    for name in env_names:
        value = os.getenv(name)
        if value:
            return apply_namespace(namespace, value)
    return apply_namespace(namespace, default)


def resolve_base_stream_name(env_names: tuple[str, ...], default: str) -> str:
    for name in env_names:
        value = os.getenv(name)
        if value:
            return value
    return default


def resolve_stream_candidates(env_names: tuple[str, ...], default: str) -> list[str]:
    base = resolve_base_stream_name(env_names, default)
    namespace = get_risk_namespace()
    if not namespace:
        return [base]
    namespaced = apply_namespace(namespace, base)
    if namespaced == base:
        return [base]
    return [namespaced, base]


def resolve_key_name(env_name: str, default: str) -> str:
    namespace = get_risk_namespace()
    value = os.getenv(env_name, default)
    return apply_namespace(namespace, value)


def resolve_key_candidates(env_name: str, default: str) -> list[str]:
    base = os.getenv(env_name, default)
    namespace = get_risk_namespace()
    if not namespace:
        return [base]
    namespaced = apply_namespace(namespace, base)
    if namespaced == base:
        return [base]
    return [namespaced, base]


def circuit_breaker_disabled() -> bool:
    return _truthy_env("E2E_DISABLE_CIRCUIT_BREAKER")


def _delete_key(redis_client, key: str) -> None:
    try:
        deleted = redis_client.delete(key)
        if deleted:
            logger.info("Deleted %s", key)
        else:
            logger.info("%s not present", key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to delete %s: %s", key, exc)
    try:
        redis_client.unlink(key)
    except Exception:
        pass


def reset_circuit_breaker(redis_client) -> None:
    """
    Remove circuit-breaker state and verify E2E flag is set.

    IMPORTANT: This only resets Redis state. In-memory flags in services
    (bot_shutdown_active, blocked_strategy_ids, etc.) are NOT reset.
    Services must respect E2E_DISABLE_CIRCUIT_BREAKER=1 to ignore shutdown events.
    """
    namespace = get_risk_namespace()
    if namespace:
        logger.info("E2E namespace: %s", namespace)
    else:
        logger.warning(
            "No RISK_NAMESPACE or E2E_RUN_ID set; streams may contain previous events."
        )

    stream_candidates = resolve_stream_candidates(
        ("RISK_BOT_SHUTDOWN_STREAM", "STREAM_BOT_SHUTDOWN"),
        "stream.bot_shutdown",
    )
    reset_candidates = resolve_stream_candidates(
        ("RISK_RESET_STREAM",), "stream.risk_reset"
    )
    orders_candidates = resolve_stream_candidates(
        ("RISK_ORDERS_STREAM",), "stream.orders"
    )
    results_candidates = resolve_stream_candidates(
        ("STREAM_ORDER_RESULTS",), "order_results"
    )
    allocation_candidates = resolve_stream_candidates(
        ("RISK_ALLOCATION_STREAM",), "stream.allocation_decisions"
    )
    risk_state_candidates = resolve_key_candidates("RISK_STATE_KEY", "risk_state")

    for key in sorted(
        {
            *stream_candidates,
            *reset_candidates,
            *orders_candidates,
            *results_candidates,
            *allocation_candidates,
            *risk_state_candidates,
        }
    ):
        _delete_key(redis_client, key)

    # Publish reset event for running services
    try:
        for reset_stream in reset_candidates:
            redis_client.xadd(reset_stream, {"reset_type": "all"}, maxlen=10000)
            logger.info("Published risk reset event to %s", reset_stream)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to publish risk reset events to %s: %s",
            ",".join(reset_candidates),
            exc,
        )

    # Verify E2E flag is set
    raw_flag = _normalize_env("E2E_DISABLE_CIRCUIT_BREAKER")
    if raw_flag == "":
        logger.warning(
            "E2E_DISABLE_CIRCUIT_BREAKER not set; circuit breaker enabled by default."
        )
    elif circuit_breaker_disabled():
        logger.info("E2E_DISABLE_CIRCUIT_BREAKER=1: Services will ignore shutdown events")
    else:
        logger.info(
            "E2E_DISABLE_CIRCUIT_BREAKER=%s: Circuit breaker enabled",
            raw_flag,
        )
