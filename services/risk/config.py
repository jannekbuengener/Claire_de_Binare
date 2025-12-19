"""
Risk Manager - Configuration
Enhanced with comprehensive safety controls (Issue #177)
"""

import os
import json
from dataclasses import dataclass, field
from typing import Optional, Dict
from core.domain.secrets import get_secret


@dataclass
class RiskConfig:
    """Risk-Manager Konfiguration mit erweiterten Safety Controls"""

    # Runtime
    env: str = os.getenv("ENV", "development")
    port: int = int(os.getenv("RISK_PORT", "8002"))

    # Redis
    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: Optional[str] = get_secret("redis_password", "REDIS_PASSWORD")
    redis_db: int = int(os.getenv("REDIS_DB", "0"))

    # Emergency Controls
    emergency_stop_key: str = "trading:emergency_stop"  # Redis key for kill switch
    check_emergency_stop: bool = os.getenv("ENABLE_EMERGENCY_STOP", "true").lower() == "true"

    # Position Limits - Percentage-based
    max_position_pct: float = float(os.getenv("MAX_POSITION_PCT", "0.10"))  # 10% per position
    max_total_exposure_pct: float = float(
        os.getenv("MAX_TOTAL_EXPOSURE_PCT") or os.getenv("MAX_EXPOSURE_PCT", "0.30")
    )  # 30% total exposure
    max_daily_drawdown_pct: float = float(os.getenv("MAX_DAILY_DRAWDOWN_PCT", "0.05"))  # 5% max daily loss
    stop_loss_pct: float = float(os.getenv("STOP_LOSS_PCT", "0.02"))  # 2% stop loss

    # Position Limits - Count-based
    max_open_positions: int = int(os.getenv("MAX_OPEN_POSITIONS", "5"))  # Max 5 simultaneous positions
    max_positions_per_symbol: int = int(os.getenv("MAX_POSITIONS_PER_SYMBOL", "1"))  # 1 position per symbol

    # Per-Symbol Absolute Limits (optional, loaded from JSON env var)
    # Example: {"BTCUSDT": 0.5, "ETHUSDT": 10.0, "SOLUSDT": 100.0}
    per_symbol_limits: Dict[str, float] = field(default_factory=dict)

    # Circuit Breaker Settings
    circuit_breaker_cooldown_minutes: int = int(os.getenv("CIRCUIT_BREAKER_COOLDOWN", "60"))  # 60 min cooldown
    circuit_breaker_auto_reset: bool = os.getenv("CIRCUIT_BREAKER_AUTO_RESET", "false").lower() == "true"

    # Topics
    input_topic: str = "signals"
    input_topic_order_results: str = "order_results"
    output_topic_orders: str = "orders"
    output_topic_alerts: str = "alerts"

    # Fake Balance für Testing (später von Exchange holen)
    test_balance: float = float(os.getenv("TEST_BALANCE", "10000"))

    def __post_init__(self):
        """Load per-symbol limits from environment"""
        limits_json = os.getenv("PER_SYMBOL_LIMITS", "{}")
        try:
            self.per_symbol_limits = json.loads(limits_json)
        except json.JSONDecodeError:
            self.per_symbol_limits = {}

    def get_symbol_limit(self, symbol: str) -> Optional[float]:
        """Get absolute position limit for symbol (if configured)"""
        return self.per_symbol_limits.get(symbol)

    def validate(self) -> bool:
        """Validiert Konfiguration"""
        # Percentage limits
        if self.max_position_pct <= 0 or self.max_position_pct > 1:
            raise ValueError("MAX_POSITION_PCT muss zwischen 0 und 1 liegen")
        if self.max_total_exposure_pct <= 0 or self.max_total_exposure_pct > 1:
            raise ValueError("MAX_TOTAL_EXPOSURE_PCT muss zwischen 0 und 1 liegen")
        if self.max_daily_drawdown_pct <= 0 or self.max_daily_drawdown_pct > 1:
            raise ValueError("MAX_DAILY_DRAWDOWN_PCT muss zwischen 0 und 1 liegen")

        # Count limits
        if self.max_open_positions < 1:
            raise ValueError("MAX_OPEN_POSITIONS muss mindestens 1 sein")
        if self.max_positions_per_symbol < 1:
            raise ValueError("MAX_POSITIONS_PER_SYMBOL muss mindestens 1 sein")

        # Circuit breaker
        if self.circuit_breaker_cooldown_minutes < 0:
            raise ValueError("CIRCUIT_BREAKER_COOLDOWN muss >= 0 sein")

        return True


config = RiskConfig()
