"""#4149: Replay must not coerce missing regime_id to TREND (0)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from core.replay.dataset_provider import DBBackedDatasetProvider
from core.replay.dataset_spec import DatasetSpec

pytestmark = [pytest.mark.unit, pytest.mark.contract]

_BASE_START_MS = 1_700_000_000_000
_DB_WARMUP = 3
_DB_END_MS = _BASE_START_MS + 600_000
_DB_WARMUP_START_MS = _BASE_START_MS - _DB_WARMUP * 60_000


def _rows_with_null_regime(count: int, start_ts_ms: int) -> list[tuple]:
    return [
        (
            start_ts_ms + i * 60_000,
            Decimal("50000"),
            Decimal("50001"),
            Decimal("49999"),
            Decimal("50000.5"),
            Decimal("10.5"),
            100 + i,
            None,
        )
        for i in range(count)
    ]


def test_db_backed_null_regime_id_not_coerced_to_trend() -> None:
    rows = _rows_with_null_regime(14, _DB_WARMUP_START_MS)
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    conn = MagicMock()
    conn.cursor.return_value = cursor
    spec = DatasetSpec(
        source="db",
        symbol="BTCUSDT",
        timeframe="1m",
        start_ts_ms=_BASE_START_MS,
        end_ts_ms=_DB_END_MS,
        warmup_candles=_DB_WARMUP,
        file_path=None,
        db_dataset_window=f"{_BASE_START_MS}:{_DB_END_MS}",
    )
    result = DBBackedDatasetProvider(conn).load(spec)
    assert all(c.get("regime_id") is None for c in result.candles)
    assert not any(c.get("regime_id") == 0 for c in result.candles)

    sql = cursor.execute.call_args[0][0]
    assert "COALESCE" not in sql.upper()
