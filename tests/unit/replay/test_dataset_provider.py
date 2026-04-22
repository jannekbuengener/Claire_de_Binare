"""Unit tests for ARVP DatasetSpec and DatasetProvider.

Tests validate:
- DatasetSpec invariants (all fail-closed rules)
- DatasetSpec fingerprint determinism and serialization
- FileBackedDatasetProvider: JSON array and JSONL loading, all error paths
- DBBackedDatasetProvider: full DB-backed loading, all fail-closed paths

Part of ARVP §4.2 — Historical Data Access layer.
Tracked in GitHub Issue #1841.
"""

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from core.replay.dataset_provider import (
    DBBackedDatasetProvider,
    DatasetLoadError,
    DatasetResult,
    FileBackedDatasetProvider,
)
from core.replay.dataset_spec import DatasetSpec, DatasetSpecError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_START_MS = 1_700_000_000_000


def _make_spec(
    *,
    symbol: str = "BTCUSDT",
    timeframe: str = "1m",
    start_ts_ms: int = _BASE_START_MS,
    end_ts_ms: int = _BASE_START_MS + 600_000,
    warmup_candles: int = 3,
    source: str = "file",
    file_path: str | None = "/tmp/data.json",
    db_dataset_id: str | None = None,
) -> DatasetSpec:
    return DatasetSpec(
        symbol=symbol,
        timeframe=timeframe,
        start_ts_ms=start_ts_ms,
        end_ts_ms=end_ts_ms,
        warmup_candles=warmup_candles,
        source=source,
        file_path=file_path,
        db_dataset_id=db_dataset_id,
    )


def _make_candles(count: int, start_ts_ms: int = _BASE_START_MS) -> list[dict]:
    return [
        {
            "ts_ms": start_ts_ms + i * 60_000,
            "high": 50_000.0 + i,
            "low": 49_000.0 + i,
            "close": 49_500.0 + i,
        }
        for i in range(count)
    ]


def _make_db_rows(count: int, start_ts_ms: int = _BASE_START_MS) -> list[tuple]:
    """Generate mock psycopg2 rows for candles_1m with valid 1-minute cadence.

    Column order matches SELECT in DBBackedDatasetProvider:
    ts_ms (int), open (Decimal), high (Decimal), low (Decimal),
    close (Decimal), volume (Decimal), trade_count (int).
    """
    return [
        (
            start_ts_ms + i * 60_000,
            Decimal("50000.00000001"),
            Decimal("50001.00000001"),
            Decimal("49999.00000001"),
            Decimal("50000.50000001"),
            Decimal("10.50000001"),
            100 + i,
        )
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# DatasetSpec — validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_valid_file_spec_validates_without_error() -> None:
    spec = _make_spec()
    spec.validate()


@pytest.mark.unit
def test_valid_db_spec_validates_without_error() -> None:
    spec = _make_spec(source="db", file_path=None, db_dataset_id="ds-001")
    spec.validate()


@pytest.mark.unit
def test_invalid_symbol_rejected() -> None:
    spec = _make_spec(symbol="ETHUSDT")
    with pytest.raises(DatasetSpecError, match="Invalid symbol"):
        spec.validate()


@pytest.mark.unit
def test_invalid_timeframe_rejected() -> None:
    spec = _make_spec(timeframe="5m")
    with pytest.raises(DatasetSpecError, match="Invalid timeframe"):
        spec.validate()


@pytest.mark.unit
def test_start_greater_than_end_rejected() -> None:
    spec = _make_spec(start_ts_ms=_BASE_START_MS + 120_000, end_ts_ms=_BASE_START_MS)
    with pytest.raises(DatasetSpecError, match="start_ts_ms"):
        spec.validate()


@pytest.mark.unit
def test_start_equals_end_accepted() -> None:
    spec = _make_spec(start_ts_ms=_BASE_START_MS, end_ts_ms=_BASE_START_MS, warmup_candles=0)
    spec.validate()


@pytest.mark.unit
def test_negative_warmup_rejected() -> None:
    spec = _make_spec(warmup_candles=-1)
    with pytest.raises(DatasetSpecError, match="warmup_candles"):
        spec.validate()


@pytest.mark.unit
def test_zero_warmup_accepted() -> None:
    spec = _make_spec(warmup_candles=0)
    spec.validate()


@pytest.mark.unit
def test_file_source_missing_file_path_rejected() -> None:
    spec = _make_spec(source="file", file_path=None)
    with pytest.raises(DatasetSpecError, match="file_path"):
        spec.validate()


@pytest.mark.unit
def test_file_source_with_db_dataset_id_rejected() -> None:
    spec = _make_spec(source="file", file_path="/tmp/f.json", db_dataset_id="ds-001")
    with pytest.raises(DatasetSpecError, match="mutually exclusive"):
        spec.validate()


@pytest.mark.unit
def test_db_source_missing_db_dataset_id_rejected() -> None:
    spec = _make_spec(source="db", file_path=None, db_dataset_id=None)
    with pytest.raises(DatasetSpecError, match="db_dataset_id"):
        spec.validate()


@pytest.mark.unit
def test_db_source_with_file_path_rejected() -> None:
    spec = _make_spec(source="db", file_path="/tmp/f.json", db_dataset_id="ds-001")
    with pytest.raises(DatasetSpecError, match="mutually exclusive"):
        spec.validate()


# ---------------------------------------------------------------------------
# DatasetSpec — to_dict and fingerprint
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_to_dict_omits_none_optional_fields() -> None:
    spec = _make_spec(source="file", file_path="/tmp/f.json", db_dataset_id=None)
    d = spec.to_dict()
    assert "db_dataset_id" not in d
    assert d["file_path"] == "/tmp/f.json"


@pytest.mark.unit
def test_to_dict_includes_db_dataset_id_when_set() -> None:
    spec = _make_spec(source="db", file_path=None, db_dataset_id="ds-abc")
    d = spec.to_dict()
    assert "file_path" not in d
    assert d["db_dataset_id"] == "ds-abc"


@pytest.mark.unit
def test_fingerprint_is_deterministic() -> None:
    spec_a = _make_spec()
    spec_b = _make_spec()
    assert spec_a.fingerprint() == spec_b.fingerprint()


@pytest.mark.unit
def test_different_specs_produce_different_fingerprints() -> None:
    spec_a = _make_spec(start_ts_ms=_BASE_START_MS)
    spec_b = _make_spec(start_ts_ms=_BASE_START_MS + 60_000)
    assert spec_a.fingerprint() != spec_b.fingerprint()


@pytest.mark.unit
def test_fingerprint_is_64_char_lowercase_hex() -> None:
    fp = _make_spec().fingerprint()
    assert len(fp) == 64
    assert all(c in "0123456789abcdef" for c in fp)


# ---------------------------------------------------------------------------
# FileBackedDatasetProvider — happy paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_file_backed_loads_json_array(tmp_path: object) -> None:
    candles = _make_candles(10)
    f = tmp_path / "data.json"
    f.write_text(json.dumps(candles), encoding="utf-8")

    spec = _make_spec(file_path=str(f), warmup_candles=3)
    result = FileBackedDatasetProvider().load(spec)

    assert isinstance(result, DatasetResult)
    assert len(result.candles) == 10
    assert result.warmup_count == 3
    assert result.effective_candle_count == 7
    assert result.fingerprint == spec.fingerprint()
    assert result.spec is spec


@pytest.mark.unit
def test_file_backed_loads_jsonl(tmp_path: object) -> None:
    candles = _make_candles(5)
    f = tmp_path / "data.jsonl"
    f.write_text("\n".join(json.dumps(c) for c in candles), encoding="utf-8")

    spec = _make_spec(file_path=str(f), warmup_candles=2)
    result = FileBackedDatasetProvider().load(spec)

    assert len(result.candles) == 5
    assert result.effective_candle_count == 3


@pytest.mark.unit
def test_file_backed_jsonl_with_blank_lines_ignored(tmp_path: object) -> None:
    candles = _make_candles(4)
    lines = [json.dumps(c) for c in candles]
    content = "\n\n".join(lines) + "\n"
    f = tmp_path / "data.jsonl"
    f.write_text(content, encoding="utf-8")

    spec = _make_spec(file_path=str(f), warmup_candles=1)
    result = FileBackedDatasetProvider().load(spec)
    assert len(result.candles) == 4


@pytest.mark.unit
def test_file_backed_result_is_deterministic(tmp_path: object) -> None:
    candles = _make_candles(5)
    f = tmp_path / "data.json"
    f.write_text(json.dumps(candles), encoding="utf-8")
    spec = _make_spec(file_path=str(f), warmup_candles=1)

    provider = FileBackedDatasetProvider()
    r1 = provider.load(spec)
    r2 = provider.load(spec)
    assert r1.candles == r2.candles
    assert r1.fingerprint == r2.fingerprint
    assert r1.effective_candle_count == r2.effective_candle_count


@pytest.mark.unit
def test_file_backed_zero_warmup_accepted(tmp_path: object) -> None:
    candles = _make_candles(3)
    f = tmp_path / "data.json"
    f.write_text(json.dumps(candles), encoding="utf-8")
    spec = _make_spec(file_path=str(f), warmup_candles=0)
    result = FileBackedDatasetProvider().load(spec)
    assert result.warmup_count == 0
    assert result.effective_candle_count == 3


# ---------------------------------------------------------------------------
# FileBackedDatasetProvider — error paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_file_backed_missing_file_raises(tmp_path: object) -> None:
    spec = _make_spec(file_path=str(tmp_path / "missing.json"))
    with pytest.raises(DatasetLoadError, match="not found"):
        FileBackedDatasetProvider().load(spec)


@pytest.mark.unit
def test_file_backed_empty_file_raises(tmp_path: object) -> None:
    f = tmp_path / "empty.json"
    f.write_text("", encoding="utf-8")
    spec = _make_spec(file_path=str(f), warmup_candles=0)
    with pytest.raises(DatasetLoadError):
        FileBackedDatasetProvider().load(spec)


@pytest.mark.unit
def test_file_backed_malformed_json_array_raises(tmp_path: object) -> None:
    f = tmp_path / "bad.json"
    f.write_text("[{not valid", encoding="utf-8")
    spec = _make_spec(file_path=str(f))
    with pytest.raises(DatasetLoadError, match="JSON"):
        FileBackedDatasetProvider().load(spec)


@pytest.mark.unit
def test_file_backed_malformed_jsonl_line_raises(tmp_path: object) -> None:
    candles = _make_candles(3)
    lines = [json.dumps(c) for c in candles]
    lines[1] = "{bad json"
    f = tmp_path / "data.jsonl"
    f.write_text("\n".join(lines), encoding="utf-8")
    spec = _make_spec(file_path=str(f))
    with pytest.raises(DatasetLoadError, match="JSON"):
        FileBackedDatasetProvider().load(spec)


@pytest.mark.unit
def test_file_backed_missing_close_field_raises(tmp_path: object) -> None:
    candles = _make_candles(5)
    del candles[2]["close"]
    f = tmp_path / "data.json"
    f.write_text(json.dumps(candles), encoding="utf-8")
    spec = _make_spec(file_path=str(f))
    with pytest.raises(DatasetLoadError, match="close"):
        FileBackedDatasetProvider().load(spec)


@pytest.mark.unit
def test_file_backed_missing_ts_ms_field_raises(tmp_path: object) -> None:
    candles = _make_candles(3)
    del candles[0]["ts_ms"]
    f = tmp_path / "data.json"
    f.write_text(json.dumps(candles), encoding="utf-8")
    spec = _make_spec(file_path=str(f))
    with pytest.raises(DatasetLoadError, match="ts_ms"):
        FileBackedDatasetProvider().load(spec)


@pytest.mark.unit
def test_file_backed_duplicate_ts_ms_raises(tmp_path: object) -> None:
    """Duplicate ts_ms values violate strictly-increasing invariant."""
    candles = _make_candles(5)
    candles[3]["ts_ms"] = candles[2]["ts_ms"]  # make [3] == [2], not strictly increasing
    f = tmp_path / "data.json"
    f.write_text(json.dumps(candles), encoding="utf-8")
    spec = _make_spec(file_path=str(f))
    with pytest.raises(DatasetLoadError, match="strictly increasing"):
        FileBackedDatasetProvider().load(spec)


@pytest.mark.unit
def test_file_backed_non_1m_cadence_raises(tmp_path: object) -> None:
    candles = _make_candles(5)
    candles[1]["ts_ms"] += 30_000  # 90 000 ms gap from candle[0] → 1m cadence violation
    f = tmp_path / "data.json"
    f.write_text(json.dumps(candles), encoding="utf-8")
    spec = _make_spec(file_path=str(f))
    with pytest.raises(DatasetLoadError, match="1m cadence"):
        FileBackedDatasetProvider().load(spec)


@pytest.mark.unit
def test_file_backed_warmup_equals_candle_count_raises(tmp_path: object) -> None:
    """len(candles) must be strictly greater than warmup_candles."""
    candles = _make_candles(3)
    f = tmp_path / "data.json"
    f.write_text(json.dumps(candles), encoding="utf-8")
    spec = _make_spec(file_path=str(f), warmup_candles=3)  # equal, not strictly greater
    with pytest.raises(DatasetLoadError, match="Insufficient candles"):
        FileBackedDatasetProvider().load(spec)


@pytest.mark.unit
def test_file_backed_warmup_exceeds_candle_count_raises(tmp_path: object) -> None:
    candles = _make_candles(2)
    f = tmp_path / "data.json"
    f.write_text(json.dumps(candles), encoding="utf-8")
    spec = _make_spec(file_path=str(f), warmup_candles=5)
    with pytest.raises(DatasetLoadError, match="Insufficient candles"):
        FileBackedDatasetProvider().load(spec)


@pytest.mark.unit
def test_file_backed_source_mismatch_raises() -> None:
    """FileBackedDatasetProvider refuses a db-source spec."""
    spec = _make_spec(source="db", file_path=None, db_dataset_id="ds-001")
    with pytest.raises(DatasetLoadError, match="source='file'"):
        FileBackedDatasetProvider().load(spec)


@pytest.mark.unit
def test_file_backed_null_required_field_raises(tmp_path: object) -> None:
    """JSON null on a required field triggers DatasetLoadError (None-value guard)."""
    candles = _make_candles(5)
    candles[2]["close"] = None  # JSON null — parses as Python None
    f = tmp_path / "data.json"
    f.write_text(json.dumps(candles), encoding="utf-8")
    spec = _make_spec(file_path=str(f))
    with pytest.raises(DatasetLoadError, match="None value"):
        FileBackedDatasetProvider().load(spec)


@pytest.mark.unit
def test_file_backed_array_element_not_dict_raises(tmp_path: object) -> None:
    """JSON array containing a non-object element → DatasetLoadError (fail-closed)."""
    data = [{"ts_ms": _BASE_START_MS, "high": 50000.0, "low": 49000.0, "close": 49500.0}, 42]
    f = tmp_path / "data.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    spec = _make_spec(file_path=str(f))
    with pytest.raises(DatasetLoadError, match="Expected JSON object at index"):
        FileBackedDatasetProvider().load(spec)


# ---------------------------------------------------------------------------
# DBBackedDatasetProvider
# ---------------------------------------------------------------------------

# Spec constants for DB tests.
# default spec: warmup=3, start=_BASE_START_MS, end=_BASE_START_MS+600_000
# warmup_start_ms = _BASE_START_MS - 3 * 60_000 = _BASE_START_MS - 180_000
# Full window: warmup_start_ms..end → 14 rows @ 60s cadence
_DB_WARMUP = 3
_DB_END_MS = _BASE_START_MS + 600_000
_DB_WARMUP_START_MS = _BASE_START_MS - _DB_WARMUP * 60_000  # 3 warmup rows


def _make_db_spec(**overrides) -> DatasetSpec:
    defaults = dict(
        source="db",
        file_path=None,
        db_dataset_id="ds-001",
        warmup_candles=_DB_WARMUP,
        end_ts_ms=_DB_END_MS,
    )
    defaults.update(overrides)
    return _make_spec(**defaults)


def _make_mock_conn(rows: list[tuple]) -> MagicMock:
    """Build a minimal psycopg2-mock connection returning ``rows``."""
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn


@pytest.mark.unit
def test_db_backed_valid_rows_returns_dataset_result() -> None:
    """Happy path: valid DB rows → correct DatasetResult with proper counts."""
    rows = _make_db_rows(14, _DB_WARMUP_START_MS)  # 3 warmup + 11 effective
    conn = _make_mock_conn(rows)
    spec = _make_db_spec()
    result = DBBackedDatasetProvider(conn).load(spec)
    assert isinstance(result, DatasetResult)
    assert result.warmup_count == _DB_WARMUP
    assert result.effective_candle_count == 14 - _DB_WARMUP
    assert len(result.candles) == 14


@pytest.mark.unit
def test_db_backed_warmup_rows_correctly_separated() -> None:
    """Warmup rows appear at the start of result.candles; effective rows follow."""
    rows = _make_db_rows(14, _DB_WARMUP_START_MS)
    conn = _make_mock_conn(rows)
    spec = _make_db_spec()
    result = DBBackedDatasetProvider(conn).load(spec)
    assert result.candles[0]["ts_ms"] == _DB_WARMUP_START_MS
    assert result.candles[_DB_WARMUP]["ts_ms"] == _BASE_START_MS


@pytest.mark.unit
def test_db_backed_zero_warmup_starts_at_start_ts_ms() -> None:
    """warmup_candles=0: no pre-period rows; first candle is start_ts_ms."""
    rows = _make_db_rows(11, _BASE_START_MS)  # 0 warmup + 11 effective
    conn = _make_mock_conn(rows)
    spec = _make_db_spec(warmup_candles=0)
    result = DBBackedDatasetProvider(conn).load(spec)
    assert result.warmup_count == 0
    assert result.candles[0]["ts_ms"] == _BASE_START_MS
    assert result.effective_candle_count == 11


@pytest.mark.unit
def test_db_backed_empty_result_raises() -> None:
    """Empty DB result → DatasetLoadError (no candles in window)."""
    conn = _make_mock_conn([])
    spec = _make_db_spec()
    with pytest.raises(DatasetLoadError, match="No candles found"):
        DBBackedDatasetProvider(conn).load(spec)


@pytest.mark.unit
def test_db_backed_source_file_raises() -> None:
    """source='file' spec → DatasetLoadError before any DB query."""
    conn = _make_mock_conn([])
    spec = _make_spec(file_path="/some/path.json")  # source='file'
    with pytest.raises(DatasetLoadError, match="source='db'"):
        DBBackedDatasetProvider(conn).load(spec)


@pytest.mark.unit
def test_db_backed_cadence_violation_raises() -> None:
    """Rows with non-60s gap trigger DatasetLoadError (cadence check)."""
    rows = _make_db_rows(14, _DB_WARMUP_START_MS)
    # Shift one row's ts_ms to break cadence
    broken = list(rows[5])
    broken[0] += 30_000  # 90 000 ms gap instead of 60 000
    rows = rows[:5] + [tuple(broken)] + rows[6:]
    conn = _make_mock_conn(rows)
    spec = _make_db_spec()
    with pytest.raises(DatasetLoadError, match="1m cadence"):
        DBBackedDatasetProvider(conn).load(spec)


@pytest.mark.unit
def test_db_backed_missing_required_field_raises() -> None:
    """Row missing a required key → DatasetLoadError (field guard in validator)."""
    rows = _make_db_rows(14, _DB_WARMUP_START_MS)
    # Drop 'close' (index 4) from row 5 by returning only 6 columns
    bad_row = rows[5][:4] + rows[5][5:]  # skip index 4 (close)
    rows = rows[:5] + [bad_row] + rows[6:]
    conn = _make_mock_conn(rows)
    spec = _make_db_spec()
    # The mapping in load() uses positional indices, so missing column causes IndexError
    # which is caught by the try/except around cursor.execute/fetchall —
    # actually the mapping is manual so we test the validator path via None field.
    # Use None value path instead (canonical path for missing data from DB).
    rows2 = list(_make_db_rows(14, _DB_WARMUP_START_MS))
    rows2[5] = rows2[5][:4] + (None,) + rows2[5][5:]  # close = None at index 4
    conn2 = _make_mock_conn(rows2)
    with pytest.raises(DatasetLoadError, match="None value"):
        DBBackedDatasetProvider(conn2).load(spec)


@pytest.mark.unit
def test_db_backed_missing_warmup_start_raises() -> None:
    """First row ts_ms != warmup_start_ms → DatasetLoadError (exact-window check)."""
    # Shift all rows by one candle: warmup start is wrong
    rows = _make_db_rows(14, _DB_WARMUP_START_MS + 60_000)
    conn = _make_mock_conn(rows)
    spec = _make_db_spec()
    with pytest.raises(DatasetLoadError, match="warmup data"):
        DBBackedDatasetProvider(conn).load(spec)


@pytest.mark.unit
def test_db_backed_ts_ms_is_int() -> None:
    """ts_ms values in result.candles are Python int (BIGINT → int mapping)."""
    rows = _make_db_rows(14, _DB_WARMUP_START_MS)
    conn = _make_mock_conn(rows)
    spec = _make_db_spec()
    result = DBBackedDatasetProvider(conn).load(spec)
    for candle in result.candles:
        assert isinstance(candle["ts_ms"], int), f"Expected int, got {type(candle['ts_ms'])}"


@pytest.mark.unit
def test_db_backed_price_fields_are_decimal() -> None:
    """Numeric fields from DECIMAL(18,8) columns remain Decimal — no float conversion."""
    rows = _make_db_rows(14, _DB_WARMUP_START_MS)
    conn = _make_mock_conn(rows)
    spec = _make_db_spec()
    result = DBBackedDatasetProvider(conn).load(spec)
    for candle in result.candles:
        for field in ("open", "high", "low", "close", "volume"):
            assert isinstance(candle[field], Decimal), (
                f"Field {field!r} expected Decimal, got {type(candle[field])}"
            )


@pytest.mark.unit
def test_db_backed_deterministic_output() -> None:
    """Identical DB rows produce identical DatasetResult and fingerprint."""
    rows = _make_db_rows(14, _DB_WARMUP_START_MS)
    spec = _make_db_spec()
    result1 = DBBackedDatasetProvider(_make_mock_conn(rows)).load(spec)
    result2 = DBBackedDatasetProvider(_make_mock_conn(rows)).load(spec)
    assert result1.fingerprint == result2.fingerprint
    assert result1.candles == result2.candles


@pytest.mark.unit
def test_db_backed_invalid_spec_fails_before_db_query() -> None:
    """Invalid spec (missing db_dataset_id) raises DatasetSpecError before any query."""
    conn = _make_mock_conn([])
    spec = _make_spec(source="db", file_path=None, db_dataset_id=None)
    with pytest.raises(DatasetSpecError, match="db_dataset_id"):
        DBBackedDatasetProvider(conn).load(spec)
    conn.cursor.assert_not_called()


@pytest.mark.unit
def test_db_backed_db_exception_raises_dataset_load_error() -> None:
    """DB error during execute/fetchall → DatasetLoadError (not raw exception)."""
    cursor = MagicMock()
    cursor.execute.side_effect = Exception("connection lost")
    conn = MagicMock()
    conn.cursor.return_value = cursor
    spec = _make_db_spec()
    with pytest.raises(DatasetLoadError, match="DB query failed"):
        DBBackedDatasetProvider(conn).load(spec)

