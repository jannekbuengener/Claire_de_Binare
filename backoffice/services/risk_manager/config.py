"""
Risk Manager - Configuration
"""

import os
from dataclasses import dataclass
from typing import Optional


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
    max_exposure_pct: float = float(os.getenv("MAX_EXPOSURE_PCT", "0.50"))
    max_daily_drawdown_pct: float = float(os.getenv("MAX_DAILY_DRAWDOWN_PCT", "0.05"))
    stop_loss_pct: float = float(os.getenv("STOP_LOSS_PCT", "0.02"))

    # Topics
    input_topic: str = "signals"
    input_topic_order_results: str = "order_results"
    output_topic_orders: str = "orders"
    output_topic_alerts: str = "alerts"

    # Postgres (Source of Truth fuer Risk/Exposure)
    postgres_host: str = os.getenv("POSTGRES_HOST", "cdb_postgres")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "claire_de_binare")
    postgres_user: str = os.getenv("POSTGRES_USER", "claire_user")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")

    # Fake Balance für Testing (später von Exchange holen)
    test_balance: float = float(os.getenv("TEST_BALANCE", "10000"))

    def validate(self) -> bool:
        """Validiert Konfiguration"""
        if self.max_position_pct <= 0 or self.max_position_pct > 1:
            raise ValueError("MAX_POSITION_PCT muss zwischen 0 und 1 liegen")
        if self.max_exposure_pct <= 0 or self.max_exposure_pct > 1:
            raise ValueError("MAX_EXPOSURE_PCT muss zwischen 0 und 1 liegen")
        return True


config = RiskConfig()
