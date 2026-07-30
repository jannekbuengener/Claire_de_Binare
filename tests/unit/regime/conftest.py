"""Regime unit-test environment — required before regime.config import."""

from __future__ import annotations

import os

_REGIME_ENV = {
    "REGIME_ADX_PERIOD": "14",
    "REGIME_ATR_PERIOD": "14",
    "REGIME_ADX_TREND_THRESHOLD": "25.0",
    "REGIME_ADX_RANGE_THRESHOLD": "20.0",
    "REGIME_ATR_HIGH_VOL_THRESHOLD": "0.001",
    "REGIME_CONFIRMATION_BARS": "1",
    "REGIME_HEARTBEAT_INTERVAL_S": "60",
}

for _key, _value in _REGIME_ENV.items():
    os.environ.setdefault(_key, _value)
