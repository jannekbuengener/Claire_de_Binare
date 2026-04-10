"""Core Replay Utilities - Deterministic serialization and envelope types.

LR-021 Slice 1: Offline replay of Decision/Order/Fill envelopes
with stable canonical hashing. No runtime wiring, no Redis dependency.

relations:
  role: package_initializer
  domain: replay
  upstream: []
  downstream:
    - scripts/replay/lr021_replay.py
    - tests/unit/replay/
"""

from .historical_bridge import (
    HistoricalBridgeError,
    PrimaryBreakoutBridgeConfig,
    build_primary_breakout_historical_bridge,
)

__all__ = [
    "HistoricalBridgeError",
    "PrimaryBreakoutBridgeConfig",
    "build_primary_breakout_historical_bridge",
]
