"""
Risk Manager - Configuration
"""

import os
from dataclasses import dataclass
from typing import Optional
from core.domain.secrets import get_secret


@dataclass
class RiskConfig:
    """Risk-Manager Konfiguration"""

    # Runtime
    env: str = os.getenv("ENV", "development")
    port: int = int(os.getenv("RISK_PORT", "8002"))

    # Redis
    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: Optional[str] = get_secret("redis_password", "REDIS_PASSWORD")
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

    # REAL BALANCE - NO MORE FAKE TEST_BALANCE
    use_real_balance: bool = os.getenv("USE_REAL_BALANCE", "true").lower() == "true"
    fallback_balance: float = float(os.getenv("FALLBACK_BALANCE", "100"))  # Minimal fallback

    def validate(self) -> bool:
        """Validiert Konfiguration"""
        if self.max_position_pct <= 0 or self.max_position_pct > 1:
            raise ValueError("MAX_POSITION_PCT muss zwischen 0 und 1 liegen")
        if self.max_total_exposure_pct <= 0 or self.max_total_exposure_pct > 1:
            raise ValueError("MAX_TOTAL_EXPOSURE_PCT muss zwischen 0 und 1 liegen")
        return True


config = RiskConfig()
