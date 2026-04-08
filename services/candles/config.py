"""
Candle Aggregator Service - Configuration
"""

import os
from dataclasses import dataclass


def _required_int(name: str) -> int:
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"{name} muss gesetzt sein")
    return int(value)


@dataclass
class CandleConfig:
    env: str = os.getenv("ENV", "development")
    port: int = int(os.getenv("CANDLE_PORT", "8007"))

    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: str | None = os.getenv("REDIS_PASSWORD")
    redis_db: int = int(os.getenv("REDIS_DB", "0"))

    # Input: PubSub channel for raw trades
    input_channel: str = os.getenv("CANDLE_INPUT_CHANNEL", "market_data")

    # Output: Stream for aggregated candles
    output_stream: str = os.getenv("CANDLE_OUTPUT_STREAM", "stream.candles_1m")

    # Aggregation interval in seconds (default: 60s = 1m)
    interval_seconds: int = _required_int("CANDLE_INTERVAL_SECONDS")

    # Market State V1: Redis key prefix + TTL for return calculations
    market_state_key_prefix: str = os.getenv(
        "CANDLE_MARKET_STATE_KEY_PREFIX", "market_state"
    )
    market_state_ttl_seconds: int = int(
        os.getenv("CANDLE_MARKET_STATE_TTL_SECONDS", "120")
    )  # 2 minutes TTL

    # Kill-switch: set CANDLE_WRITE_MARKET_STATE=false to disable the write.
    # Default true (fail-safe: garbage values keep the write enabled).
    # Cutover step: set to "false" once cdb_market owns the contract.
    write_market_state: bool = (
        os.getenv("CANDLE_WRITE_MARKET_STATE", "true").lower() != "false"
    )

    # Regime V1: Stream source + staleness threshold
    regime_stream: str = os.getenv("CANDLE_REGIME_STREAM", "stream.regime_signals")
    regime_staleness_seconds: int = int(
        os.getenv("CANDLE_REGIME_STALENESS_SECONDS", "300")
    )  # 5 minutes max age

    source_version: str = os.getenv("CANDLE_SOURCE_VERSION", "1")
    schema_version: str = "1"

    def validate(self) -> bool:
        if self.interval_seconds <= 0:
            raise ValueError("CANDLE_INTERVAL_SECONDS muss > 0 sein")
        return True


config = CandleConfig()
