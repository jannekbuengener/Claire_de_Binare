"""Normalization helper: stream.candles_1m payload → DB-insert-ready dict.

Part of ARVP candles persistence layer (Issue #1855).

The candle stream entries emitted by ``cdb_candles`` (``services/candles/``)
carry all numeric values as strings (Redis ``decode_responses=True``) and
use ``ts`` in **seconds** (not milliseconds). This module normalises those
entries into the dict shape required for an idempotent ``candles_1m`` insert.

Candle stream payload shape (from ``CandleWindow.to_candle_payload()`` plus
service additions)::

    {
        "ts":             "1700000000",   # start of window, seconds, string
        "symbol":         "BTCUSDT",
        "timeframe":      "60s",
        "open":           "42000.00000000",
        "high":           "42100.00000000",
        "low":            "41900.00000000",
        "close":          "42050.00000000",
        "volume":         "12.34000000",
        "trades":         "87",
        "schema_version": "1",
        "source_version": "1",
    }

``regime_id`` is **not** emitted by the candle stream; it is written
separately to ``market_state:{symbol}`` in Redis. The normaliser always
returns ``regime_id=None`` regardless of payload content, reserving the
column for future enrichment.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS: frozenset[str] = frozenset({"ts", "symbol", "open", "high", "low", "close"})


def normalize_candle_stream_entry(payload: dict) -> dict | None:
    """Convert a ``stream.candles_1m`` Redis Stream entry to a DB-insert-ready dict.

    Returns a dict with keys::

        symbol, ts_ms, open, high, low, close, volume, trade_count, regime_id

    All numeric values are ``Decimal``; ``regime_id`` is always ``None`` in
    this phase (not present in the candle stream).

    Returns ``None`` without raising if the payload is invalid or missing
    required fields.  This is the canonical fail-closed path: the caller logs
    and skips, the service does not crash.

    Validation rules
    ----------------
    Required fields (missing → ``None``):
        ``ts``, ``symbol``, ``open``, ``high``, ``low``, ``close``

    Type / value rules:
        - ``ts``: integer-parseable string; ``ts_ms = int(ts) * 1000 > 0``
        - ``symbol``: non-empty string
        - ``open``, ``high``, ``low``, ``close``: ``Decimal``-parseable; each ``> 0``
        - ``high >= low`` (basic OHLCV invariant)
        - ``volume``: ``Decimal``-parseable if present; missing → ``Decimal("0")``;
          present-but-invalid → ``None``
        - ``trades``: integer-parseable if present; missing → ``0``;
          present-but-invalid → ``None``
    """
    # --- Required field presence ---
    missing = _REQUIRED_FIELDS - payload.keys()
    if missing:
        logger.warning("candle_normalizer: missing required fields %s", sorted(missing))
        return None

    # --- ts → ts_ms ---
    try:
        ts_ms = int(payload["ts"]) * 1000
    except (ValueError, TypeError):
        logger.warning("candle_normalizer: unparseable ts=%r", payload.get("ts"))
        return None
    if ts_ms <= 0:
        logger.warning("candle_normalizer: ts_ms must be > 0, got %d", ts_ms)
        return None

    # --- symbol ---
    symbol = payload["symbol"]
    if not symbol or not isinstance(symbol, str):
        logger.warning("candle_normalizer: invalid symbol=%r", symbol)
        return None

    # --- OHLC Decimal fields (required, must be > 0 and finite) ---
    ohlc: dict[str, Decimal] = {}
    for field in ("open", "high", "low", "close"):
        raw = payload[field]
        try:
            val = Decimal(str(raw))
        except (InvalidOperation, TypeError):
            logger.warning("candle_normalizer: invalid %s=%r", field, raw)
            return None
        if not val.is_finite():
            # Decimal('NaN') / Decimal('Infinity') — is_finite() guards the <= 0 check
            # below which would raise InvalidOperation on NaN.
            logger.warning("candle_normalizer: non-finite %s=%r", field, raw)
            return None
        if val <= 0:
            logger.warning("candle_normalizer: %s must be > 0, got %s", field, val)
            return None
        ohlc[field] = val

    # --- OHLCV invariant ---
    if ohlc["high"] < ohlc["low"]:
        logger.warning(
            "candle_normalizer: high (%s) < low (%s) — invalid candle",
            ohlc["high"],
            ohlc["low"],
        )
        return None

    # --- volume: optional; missing → Decimal("0"); present-but-invalid → None ---
    volume_raw = payload.get("volume")
    if volume_raw is None:
        volume = Decimal("0")
    else:
        try:
            volume = Decimal(str(volume_raw))
        except (InvalidOperation, TypeError):
            logger.warning("candle_normalizer: invalid volume=%r", volume_raw)
            return None
        if not volume.is_finite():
            logger.warning("candle_normalizer: non-finite volume=%r", volume_raw)
            return None
        if volume < 0:
            logger.warning("candle_normalizer: volume must be >= 0, got %s", volume)
            return None

    # --- trade_count from "trades": optional; missing → 0; present-but-invalid → None ---
    trades_raw = payload.get("trades")
    if trades_raw is None:
        trade_count = 0
    else:
        try:
            trade_count = int(trades_raw)
        except (ValueError, TypeError):
            logger.warning("candle_normalizer: invalid trades=%r", trades_raw)
            return None
        if trade_count < 0:
            logger.warning("candle_normalizer: trade_count must be >= 0, got %d", trade_count)
            return None

    return {
        "symbol": symbol,
        "ts_ms": ts_ms,
        "open": ohlc["open"],
        "high": ohlc["high"],
        "low": ohlc["low"],
        "close": ohlc["close"],
        "volume": volume,
        "trade_count": trade_count,
        "regime_id": None,  # not in candle stream; reserved for future enrichment
    }
