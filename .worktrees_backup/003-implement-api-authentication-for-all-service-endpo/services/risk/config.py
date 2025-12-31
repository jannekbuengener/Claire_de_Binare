"""
Risk Manager - Configuration
"""

import os
from dataclasses import dataclass
from typing import Optional
from core.secrets import read_secret


@dataclass
class RiskConfig:
    """Risk-Manager Konfiguration"""

    # Runtime
    env: str = os.getenv("ENV", "development")
    port: int = int(os.getenv("RISK_PORT", "8002"))

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

    # Balance Configuration
    use_live_balance: bool = os.getenv("USE_LIVE_BALANCE", "false").lower() == "true"
    test_balance: float = float(os.getenv("TEST_BALANCE", "10000"))

    # MEXC API (for live balance fetching) - Docker secrets with fallback
    mexc_api_key: Optional[str] = read_secret("mexc_api_key", "MEXC_API_KEY") or None
    mexc_api_secret: Optional[str] = read_secret("mexc_api_secret", "MEXC_API_SECRET") or None
    mexc_testnet: bool = os.getenv("MEXC_TESTNET", "true").lower() == "true"

    # API Authentication
    # Note: These settings are loaded centrally by core/api_auth.py
    # Documented here for service configuration visibility
    api_key: Optional[str] = read_secret("api_key", "API_KEY")
    api_auth_enabled: bool = os.getenv("API_AUTH_ENABLED", "true").lower() in ("true", "1", "yes", "on")
    api_auth_exempt_paths: str = os.getenv("API_AUTH_EXEMPT_PATHS", "/health")

    def validate(self) -> bool:
        """Validiert Konfiguration"""
        if self.max_position_pct <= 0 or self.max_position_pct > 1:
            raise ValueError("MAX_POSITION_PCT muss zwischen 0 und 1 liegen")
        if self.max_total_exposure_pct <= 0 or self.max_total_exposure_pct > 1:
            raise ValueError("MAX_TOTAL_EXPOSURE_PCT muss zwischen 0 und 1 liegen")
        return True


config = RiskConfig()
