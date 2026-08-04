"""CDB-049 inclusive boundary / timezone-agnostic epoch contract."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.replay.dataset_provider import (
    DatasetLoadError,
    enforce_exact_window,
    warmup_start_ms,
)
from core.replay.dataset_spec import DatasetSpec

pytestmark = pytest.mark.unit


def test_cdb049_boundaries_are_inclusive_utc_epoch_ms() -> None:
    """Start/end are inclusive candle open times in UTC epoch ms (no TZ shift)."""
    start = int(datetime(2024, 1, 1, 0, 0, tzinfo=UTC).timestamp() * 1000)
    end = start + 2 * 60_000
    warmup = 1
    spec = DatasetSpec(
        symbol="BTCUSDT",
        timeframe="1m",
        start_ts_ms=start,
        end_ts_ms=end,
        warmup_candles=warmup,
        source="file",
        file_path="unused.json",
    )
    first = warmup_start_ms(spec)
    assert first == start - 60_000
    candles = [
        {"ts_ms": first, "high": 1, "low": 1, "close": 1},
        {"ts_ms": start, "high": 1, "low": 1, "close": 1},
        {"ts_ms": start + 60_000, "high": 1, "low": 1, "close": 1},
        {"ts_ms": end, "high": 1, "low": 1, "close": 1},
    ]
    enforce_exact_window(candles, spec, "file:test")

    # Off-by-one end (exclusive misinterpretation) must fail.
    short = candles[:-1]
    with pytest.raises(DatasetLoadError, match="exact-window"):
        enforce_exact_window(short, spec, "file:test")
