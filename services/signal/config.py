"""
Signal Engine - Configuration
Lädt und validiert Umgebungsvariablen
"""

import os
from dataclasses import dataclass
from typing import Optional

from core.contracts import (
    PRIMARY_BREAKOUT_V1_DEFAULT_CONFIG,
    PRIMARY_BREAKOUT_V1_STRATEGY_ID,
    PRIMARY_BREAKOUT_V1_SYMBOL,
)


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

    # Postgres (Phase 8C: correlation_ledger writes)
    postgres_host: str = os.getenv("POSTGRES_HOST", "cdb_postgres")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "claire_de_binare")
    postgres_user: str = os.getenv("POSTGRES_USER", "claire_user")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")

    # Signal-Parameter
    threshold_pct: float = float(os.getenv("SIGNAL_THRESHOLD_PCT", "3.0"))
    lookback_minutes: int = int(os.getenv("SIGNAL_LOOKBACK_MIN", "15"))
    min_volume: float = float(os.getenv("SIGNAL_MIN_VOLUME", "100000"))
    strategy_id: str = os.getenv(
        "SIGNAL_STRATEGY_ID", PRIMARY_BREAKOUT_V1_STRATEGY_ID
    )
    symbol: str = os.getenv("SIGNAL_SYMBOL", PRIMARY_BREAKOUT_V1_SYMBOL).upper()
    bot_id: Optional[str] = os.getenv("SIGNAL_BOT_ID")
    entry_lookback_minutes: int = int(
        os.getenv(
            "SIGNAL_ENTRY_LOOKBACK_MIN",
            str(PRIMARY_BREAKOUT_V1_DEFAULT_CONFIG.entry_lookback_minutes),
        )
    )
    exit_lookback_minutes: int = int(
        os.getenv(
            "SIGNAL_EXIT_LOOKBACK_MIN",
            str(PRIMARY_BREAKOUT_V1_DEFAULT_CONFIG.exit_lookback_minutes),
        )
    )
    breakout_buffer: float = float(
        os.getenv(
            "SIGNAL_BREAKOUT_BUFFER",
            str(PRIMARY_BREAKOUT_V1_DEFAULT_CONFIG.breakout_buffer),
        )
    )
    min_minutes_between_entries: int = int(
        os.getenv(
            "SIGNAL_MIN_MINUTES_BETWEEN_ENTRIES",
            str(PRIMARY_BREAKOUT_V1_DEFAULT_CONFIG.min_minutes_between_entries),
        )
    )
    trade_side_mode: str = os.getenv(
        "SIGNAL_TRADE_SIDE_MODE", PRIMARY_BREAKOUT_V1_DEFAULT_CONFIG.trade_side_mode
    )
    market_state_key_prefix: str = os.getenv(
        "SIGNAL_MARKET_STATE_KEY_PREFIX", "market_state"
    )
    market_state_staleness_s: int = int(
        os.getenv("SIGNAL_MARKET_STATE_STALENESS_S", "30")
    )

    # Topics
    input_topic: str = "market_data"
    output_topic: str = "signals"
    output_stream: str = os.getenv("SIGNAL_OUTPUT_STREAM", "stream.signals")

    def validate(self) -> bool:
        """Validiert Konfiguration"""
        if self.threshold_pct <= 0:
            raise ValueError("SIGNAL_THRESHOLD_PCT muss > 0 sein")
        if self.lookback_minutes <= 0:
            raise ValueError("SIGNAL_LOOKBACK_MIN muss > 0 sein")
        if not self.strategy_id:
            raise ValueError("SIGNAL_STRATEGY_ID muss gesetzt sein")
        if self.market_state_staleness_s <= 0:
            raise ValueError("SIGNAL_MARKET_STATE_STALENESS_S muss > 0 sein")
        if self.strategy_id == PRIMARY_BREAKOUT_V1_STRATEGY_ID:
            if self.symbol != PRIMARY_BREAKOUT_V1_SYMBOL:
                raise ValueError("SIGNAL_SYMBOL muss fuer primary_breakout_v1 BTCUSDT sein")
            if self.entry_lookback_minutes <= 0:
                raise ValueError("SIGNAL_ENTRY_LOOKBACK_MIN muss > 0 sein")
            if self.exit_lookback_minutes <= 0:
                raise ValueError("SIGNAL_EXIT_LOOKBACK_MIN muss > 0 sein")
            if self.breakout_buffer < 0:
                raise ValueError("SIGNAL_BREAKOUT_BUFFER muss >= 0 sein")
            if self.min_minutes_between_entries < 0:
                raise ValueError("SIGNAL_MIN_MINUTES_BETWEEN_ENTRIES muss >= 0 sein")
            if self.trade_side_mode != PRIMARY_BREAKOUT_V1_DEFAULT_CONFIG.trade_side_mode:
                raise ValueError(
                    "SIGNAL_TRADE_SIDE_MODE muss fuer primary_breakout_v1 long_only sein"
                )
        return True


# Globale Config-Instanz
config = SignalConfig()
