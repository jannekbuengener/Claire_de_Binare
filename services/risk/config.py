"""
Risk Manager - Configuration
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


def _read_secret(secret_name: str, fallback_env: str = None) -> str:
    """Read secret from Docker secrets or fallback to environment variable"""
    secret_path = Path(f"/run/secrets/{secret_name}")
    if secret_path.exists():
        return secret_path.read_text().strip()
    if fallback_env:
        return os.getenv(fallback_env, "")
    return ""


def _apply_namespace(namespace: str, value: str) -> str:
    if not namespace:
        return value
    prefix = f"{namespace}."
    if value.startswith(prefix):
        return value
    return f"{prefix}{value}"


def _resolve_namespace() -> str:
    namespace = os.getenv("RISK_NAMESPACE", "").strip()
    if namespace:
        return namespace
    run_id = os.getenv("E2E_RUN_ID", "").strip()
    if run_id:
        return f"e2e.{run_id}"
    return ""


@dataclass
class RiskConfig:
    """Risk-Manager Konfiguration"""

    # Runtime
    env: str = os.getenv("ENV", "development")
    port: int = int(os.getenv("RISK_PORT", "8002"))
    risk_namespace: str = _resolve_namespace()

    # Redis
    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: Optional[str] = os.getenv("REDIS_PASSWORD")
    redis_db: int = int(os.getenv("REDIS_DB", "0"))

    # Risk-Limits (aus .env)
    max_position_pct: float = float(os.getenv("MAX_POSITION_PCT", "0.10"))
    max_total_exposure_pct: float = float(
        os.getenv("MAX_TOTAL_EXPOSURE_PCT") or os.getenv("MAX_EXPOSURE_PCT", "0.30")
    )
    max_daily_drawdown_pct: float = float(os.getenv("MAX_DAILY_DRAWDOWN_PCT", "0.05"))
    stop_loss_pct: float = float(os.getenv("STOP_LOSS_PCT", "0.02"))
    max_bot_exposure_pct: float = float(os.getenv("MAX_BOT_EXPOSURE_PCT", "0"))
    max_symbol_exposure_pct: float = float(os.getenv("MAX_SYMBOL_EXPOSURE_PCT", "0"))

    # Topics
    input_topic: str = "signals"
    input_topic_order_results: str = "order_results"
    output_topic_orders: str = "orders"
    output_topic_alerts: str = "alerts"
    orders_stream: str = os.getenv("RISK_ORDERS_STREAM", "stream.orders")
    regime_stream: str = os.getenv("RISK_REGIME_STREAM", "stream.regime_signals")
    allocation_stream: str = os.getenv(
        "RISK_ALLOCATION_STREAM", "stream.allocation_decisions"
    )
    bot_shutdown_stream: str = os.getenv(
        "RISK_BOT_SHUTDOWN_STREAM", "stream.bot_shutdown"
    )
    risk_reset_stream: str = os.getenv("RISK_RESET_STREAM", "stream.risk_reset")

    # Balance Configuration
    use_live_balance: bool = os.getenv("USE_LIVE_BALANCE", "false").lower() == "true"
    test_balance: float = float(os.getenv("TEST_BALANCE", "10000"))

    # MEXC API (for live balance fetching) - Docker secrets with fallback
    mexc_api_key: Optional[str] = _read_secret("mexc_api_key", "MEXC_API_KEY") or None
    mexc_api_secret: Optional[str] = _read_secret("mexc_api_secret", "MEXC_API_SECRET") or None
    mexc_testnet: bool = os.getenv("MEXC_TESTNET", "true").lower() == "true"

    # Circuit Breaker (for E2E)
    e2e_disable_circuit_breaker: bool = os.getenv(
        "E2E_DISABLE_CIRCUIT_BREAKER", "false"
    ).strip().lower() in {"1", "true", "yes", "on"}
    circuit_breaker_max_consecutive_failures: int = int(
        os.getenv("CIRCUIT_MAX_CONSECUTIVE_FAILURES", "3")
    )
    circuit_breaker_max_failures: int = int(
        os.getenv("CIRCUIT_MAX_FAILURES_PER_WINDOW", "5")
    )
    circuit_breaker_failure_window_sec: int = int(
        os.getenv("CIRCUIT_FAILURE_WINDOW_SEC", "3600")
    )
    circuit_breaker_cooldown_sec: int = int(
        os.getenv("CIRCUIT_COOLDOWN_SEC", "0")
    )
    risk_state_key: str = os.getenv("RISK_STATE_KEY", "risk_state")

    def __post_init__(self) -> None:
        if self.max_bot_exposure_pct <= 0:
            self.max_bot_exposure_pct = self.max_total_exposure_pct
        if self.max_symbol_exposure_pct <= 0:
            self.max_symbol_exposure_pct = self.max_position_pct
        if self.risk_namespace:
            self.risk_state_key = _apply_namespace(
                self.risk_namespace, self.risk_state_key
            )
            self.bot_shutdown_stream = _apply_namespace(
                self.risk_namespace, self.bot_shutdown_stream
            )
            self.risk_reset_stream = _apply_namespace(
                self.risk_namespace, self.risk_reset_stream
            )
            self.orders_stream = _apply_namespace(
                self.risk_namespace, self.orders_stream
            )
            self.allocation_stream = _apply_namespace(
                self.risk_namespace, self.allocation_stream
            )
            self.regime_stream = _apply_namespace(
                self.risk_namespace, self.regime_stream
            )

    def validate(self) -> bool:
        """Validiert Konfiguration"""
        if self.max_position_pct <= 0 or self.max_position_pct > 1:
            raise ValueError("MAX_POSITION_PCT muss zwischen 0 und 1 liegen")
        if self.max_total_exposure_pct <= 0 or self.max_total_exposure_pct > 1:
            raise ValueError("MAX_TOTAL_EXPOSURE_PCT muss zwischen 0 und 1 liegen")
        if self.max_bot_exposure_pct <= 0 or self.max_bot_exposure_pct > 1:
            raise ValueError("MAX_BOT_EXPOSURE_PCT muss zwischen 0 und 1 liegen")
        if self.max_symbol_exposure_pct <= 0 or self.max_symbol_exposure_pct > 1:
            raise ValueError("MAX_SYMBOL_EXPOSURE_PCT muss zwischen 0 und 1 liegen")
        return True


config = RiskConfig()
