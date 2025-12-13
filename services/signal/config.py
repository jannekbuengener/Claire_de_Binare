"""
Signal Engine - Configuration
Lädt und validiert Umgebungsvariablen
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class SignalConfig:
    """Signal-Engine Konfiguration"""

    # Runtime
    env: str = os.getenv("ENV", "development")
    port: int = int(os.getenv("SIGNAL_PORT", "8001"))

    # Redis
    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: Optional[str] = os.getenv("REDIS_PASSWORD")
    redis_db: int = int(os.getenv("REDIS_DB", "0"))

    # Signal-Parameter
    threshold_pct: float = float(os.getenv("SIGNAL_THRESHOLD_PCT", "3.0"))
    lookback_minutes: int = int(os.getenv("SIGNAL_LOOKBACK_MIN", "15"))
    min_volume: float = float(os.getenv("SIGNAL_MIN_VOLUME", "100000"))

    # Topics
    input_topic: str = "market_data"
    output_topic: str = "signals"

    def validate(self) -> bool:
        """Validiert Konfiguration"""
        if self.threshold_pct <= 0:
            raise ValueError("SIGNAL_THRESHOLD_PCT muss > 0 sein")
        if self.lookback_minutes <= 0:
            raise ValueError("SIGNAL_LOOKBACK_MIN muss > 0 sein")
        return True


# Globale Config-Instanz
config = SignalConfig()
