"""
Allocation Service - Configuration
"""

import json
import os
from dataclasses import dataclass, field

from core.secrets import read_secret


def _required_int(name: str) -> int:
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"{name} muss gesetzt sein")
    return int(value)


def _required_json(name: str) -> dict:
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"{name} muss gesetzt sein")
    return json.loads(value)


@dataclass
class AllocationConfig:
    env: str = os.getenv("ENV", "development")
    port: int = int(os.getenv("ALLOCATION_PORT", "8005"))

    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: str | None = os.getenv("REDIS_PASSWORD")
    redis_db: int = int(os.getenv("REDIS_DB", "0"))

    regime_stream: str = os.getenv(
        "ALLOCATION_REGIME_STREAM", "stream.regime_signals"
    )
    fills_stream: str = os.getenv("ALLOCATION_FILLS_STREAM", "stream.fills")
    shutdown_stream: str = os.getenv("ALLOCATION_SHUTDOWN_STREAM", "stream.bot_shutdown")
    output_stream: str = os.getenv(
        "ALLOCATION_OUTPUT_STREAM", "stream.allocation_decisions"
    )

    rules: dict = field(default_factory=dict)
    regime_min_stable_seconds: int = _required_int(
        "ALLOCATION_REGIME_MIN_STABLE_SECONDS"
    )

    ema_alpha: float = 0.3
    lookback_trades: int = 30
    lookback_days: int = 7
    cooldown_seconds: int = 72 * 3600
    source_version: str = os.getenv("ALLOCATION_SOURCE_VERSION", "1")
    schema_version: str = "1"

    # API Authentication
    # Note: These settings are loaded centrally by core/api_auth.py
    # Documented here for service configuration visibility
    api_key: str | None = read_secret("api_key", "API_KEY")
    api_auth_enabled: bool = os.getenv("API_AUTH_ENABLED", "true").lower() in ("true", "1", "yes", "on")
    api_auth_exempt_paths: str = os.getenv("API_AUTH_EXEMPT_PATHS", "/health")

    def __post_init__(self):
        if not self.rules:
            self.rules = _required_json("ALLOCATION_RULES_JSON")

    def validate(self) -> bool:
        if self.regime_min_stable_seconds <= 0:
            raise ValueError("ALLOCATION_REGIME_MIN_STABLE_SECONDS muss > 0 sein")
        if not isinstance(self.rules, dict) or not self.rules:
            raise ValueError("ALLOCATION_RULES_JSON muss ein Objekt sein")
        return True


config = AllocationConfig()
