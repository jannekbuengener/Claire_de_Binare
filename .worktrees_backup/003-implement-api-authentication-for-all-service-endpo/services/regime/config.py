"""
Market Regime Service - Configuration
"""

import os
from dataclasses import dataclass

from core.secrets import read_secret


def _required_int(name: str) -> int:
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"{name} muss gesetzt sein")
    return int(value)


def _required_float(name: str) -> float:
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"{name} muss gesetzt sein")
    return float(value)


@dataclass
class RegimeConfig:
    env: str = os.getenv("ENV", "development")
    port: int = int(os.getenv("REGIME_PORT", "8004"))

    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: str | None = os.getenv("REDIS_PASSWORD")
    redis_db: int = int(os.getenv("REDIS_DB", "0"))

    input_stream: str = os.getenv("REGIME_INPUT_STREAM", "stream.market_data")
    output_stream: str = os.getenv("REGIME_OUTPUT_STREAM", "stream.regime_signals")

    adx_period: int = _required_int("REGIME_ADX_PERIOD")
    atr_period: int = _required_int("REGIME_ATR_PERIOD")
    adx_trend_threshold: float = _required_float("REGIME_ADX_TREND_THRESHOLD")
    adx_range_threshold: float = _required_float("REGIME_ADX_RANGE_THRESHOLD")
    atr_high_vol_threshold: float = _required_float("REGIME_ATR_HIGH_VOL_THRESHOLD")
    confirmation_bars: int = _required_int("REGIME_CONFIRMATION_BARS")

    source_version: str = os.getenv("REGIME_SOURCE_VERSION", "1")
    schema_version: str = "1"

    # API Authentication
    # Note: These settings are loaded centrally by core/api_auth.py
    # Documented here for service configuration visibility
    api_key: str | None = read_secret("api_key", "API_KEY")
    api_auth_enabled: bool = os.getenv("API_AUTH_ENABLED", "true").lower() in ("true", "1", "yes", "on")
    api_auth_exempt_paths: str = os.getenv("API_AUTH_EXEMPT_PATHS", "/health")

    def validate(self) -> bool:
        if self.adx_period <= 0:
            raise ValueError("REGIME_ADX_PERIOD muss > 0 sein")
        if self.atr_period <= 0:
            raise ValueError("REGIME_ATR_PERIOD muss > 0 sein")
        if self.adx_trend_threshold <= self.adx_range_threshold:
            raise ValueError("ADX Trend Threshold muss > Range Threshold sein")
        if self.confirmation_bars <= 0:
            raise ValueError("REGIME_CONFIRMATION_BARS muss > 0 sein")
        return True


config = RegimeConfig()
