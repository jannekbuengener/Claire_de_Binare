"""Unit tests for dataset request vs content identity (#4151).

test_id: tc_dataset_identity_4151
test_type: Bauteil-Test
cdb_area: replay
rule_ref: request_content_fingerprint_separation
issue_ref: 4151
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.replay.dataset_identity import (
    CONTENT_IDENTITY_SCHEMA_VERSION,
    assert_content_payload_secret_safe,
    build_content_identity_payload,
    collect_forbidden_evidence_keys,
    content_fingerprint,
    content_identity_canonical_json,
    normalize_candle_for_content,
    request_fingerprint,
)
from core.replay.dataset_provider import (
    DBBackedDatasetProvider,
    FileBackedDatasetProvider,
)
from core.replay.dataset_spec import DatasetSpec

_BASE_START_MS = 1_700_000_000_000
_BASE_END_MS = _BASE_START_MS + 240_000
_ONE_MINUTE_MS = 60_000


def _file_candles(*, warmup: int = 1) -> list[dict]:
    """Exact-window candle series: warmup prefix + live bars through end_ts.

    CDB-049: first candle must be at ``start_ts_ms - warmup * 1m``; last at
    ``end_ts_ms``. Default matches ``_file_spec`` / ``_db_spec`` bounds.
    """
    first = _BASE_START_MS - int(warmup) * _ONE_MINUTE_MS
    count = ((_BASE_END_MS - first) // _ONE_MINUTE_MS) + 1
    return [
        {
            "ts_ms": first + i * _ONE_MINUTE_MS,
            "open": 50_000.0 + i,
            "high": 50_001.0 + i,
            "low": 49_999.0 + i,
            "close": 50_000.5 + i,
            "volume": 10.5 + i,
        }
        for i in range(count)
    ]


def _db_rows_matching_file(candles: list[dict]) -> list[tuple]:
    """DB rows with Decimal numerics matching file floats."""
    return [
        (
            c["ts_ms"],
            Decimal(str(c["open"])),
            Decimal(str(c["high"])),
            Decimal(str(c["low"])),
            Decimal(str(c["close"])),
            Decimal(str(c["volume"])),
            100 + idx,
            0,
        )
        for idx, c in enumerate(candles)
    ]


def _file_spec(path: str, *, warmup: int = 1) -> DatasetSpec:
    return DatasetSpec(
        symbol="BTCUSDT",
        timeframe="1m",
        start_ts_ms=_BASE_START_MS,
        end_ts_ms=_BASE_END_MS,
        warmup_candles=warmup,
        source="file",
        file_path=path,
    )


def _db_spec(*, warmup: int = 1) -> DatasetSpec:
    end = _BASE_END_MS
    return DatasetSpec(
        symbol="BTCUSDT",
        timeframe="1m",
        start_ts_ms=_BASE_START_MS,
        end_ts_ms=end,
        warmup_candles=warmup,
        source="db",
        file_path=None,
        db_dataset_window=f"{_BASE_START_MS}:{end}",
    )


@pytest.mark.unit
def test_identical_content_yields_identical_hash() -> None:
    candles = _file_candles()
    assert content_fingerprint(candles) == content_fingerprint(list(candles))


@pytest.mark.unit
def test_changed_candle_yields_different_hash() -> None:
    candles_a = _file_candles()
    candles_b = _file_candles()
    candles_b[2] = {**candles_b[2], "close": candles_b[2]["close"] + 1.0}
    assert content_fingerprint(candles_a) != content_fingerprint(candles_b)


@pytest.mark.unit
def test_different_file_paths_same_content_keep_content_hash(
    tmp_path: Path,
) -> None:
    candles = _file_candles()
    path_a = tmp_path / "a" / "data.json"
    path_b = tmp_path / "b" / "other.json"
    path_a.parent.mkdir()
    path_b.parent.mkdir()
    path_a.write_text(json.dumps(candles), encoding="utf-8")
    path_b.write_text(json.dumps(candles), encoding="utf-8")

    result_a = FileBackedDatasetProvider().load(_file_spec(str(path_a)))
    result_b = FileBackedDatasetProvider().load(_file_spec(str(path_b)))

    assert result_a.content_fingerprint == result_b.content_fingerprint
    assert result_a.request_fingerprint != result_b.request_fingerprint
    assert result_a.fingerprint == result_a.request_fingerprint
    assert result_b.fingerprint == result_b.request_fingerprint


@pytest.mark.unit
def test_file_and_db_same_content_same_content_hash(tmp_path: Path) -> None:
    # warmup=0 so File and DB load the same [start, end] series without
    # extra DB warmup rows ahead of the file content.
    candles = _file_candles(warmup=0)
    path = tmp_path / "parity.json"
    path.write_text(json.dumps(candles), encoding="utf-8")

    file_result = FileBackedDatasetProvider().load(_file_spec(str(path), warmup=0))

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = _db_rows_matching_file(candles)

    db_result = DBBackedDatasetProvider(mock_conn).load(_db_spec(warmup=0))

    assert file_result.content_fingerprint is not None
    assert db_result.content_fingerprint is not None
    assert file_result.content_fingerprint == db_result.content_fingerprint
    # Request identity still differs (file_path vs db_dataset_window / source).
    assert file_result.request_fingerprint != db_result.request_fingerprint


@pytest.mark.unit
def test_request_and_content_hashes_are_semantically_separated(
    tmp_path: Path,
) -> None:
    candles = _file_candles()
    path = tmp_path / "sep.json"
    path.write_text(json.dumps(candles), encoding="utf-8")
    spec = _file_spec(str(path))

    result = FileBackedDatasetProvider().load(spec)
    req = request_fingerprint(spec)
    content = content_fingerprint(result.candles)

    assert result.fingerprint == req
    assert result.request_fingerprint == req
    assert result.content_fingerprint == content
    assert req != content
    # Mutating loaded content changes only content identity.
    mutated = [dict(c) for c in result.candles]
    mutated[0]["high"] = float(mutated[0]["high"]) + 9.0
    assert content_fingerprint(mutated) != content
    assert request_fingerprint(spec) == req


@pytest.mark.unit
def test_canonical_serialization_is_repeatable() -> None:
    candles = _file_candles()
    first = content_identity_canonical_json(candles)
    second = content_identity_canonical_json(list(reversed(candles)))
    assert first == second
    payload = build_content_identity_payload(candles)
    assert payload["schema_version"] == CONTENT_IDENTITY_SCHEMA_VERSION
    assert content_fingerprint(candles) == content_fingerprint(list(reversed(candles)))


@pytest.mark.unit
def test_secret_and_dsn_fields_not_in_snapshot_or_hash_evidence() -> None:
    dirty = {
        "ts_ms": _BASE_START_MS,
        "open": 1.0,
        "high": 2.0,
        "low": 0.5,
        "close": 1.5,
        "volume": 3.0,
        "file_path": "/secret/local/path.json",
        "dsn": "postgresql://user:password@localhost/cdb",
        "password": "super-secret",
        "api_key": "abc",
    }
    normalized = normalize_candle_for_content(dirty)
    assert "file_path" not in normalized
    assert "dsn" not in normalized
    assert "password" not in normalized
    assert "api_key" not in normalized

    payload = build_content_identity_payload([dirty])
    assert collect_forbidden_evidence_keys(payload) == []
    assert_content_payload_secret_safe(payload)

    # Contaminated evidence envelope must be rejected.
    contaminated = {
        **payload,
        "dsn": "postgresql://user:password@localhost/cdb",
        "file_path": "/tmp/x.json",
    }
    assert collect_forbidden_evidence_keys(contaminated) == ["dsn", "file_path"]
    with pytest.raises(ValueError, match="secret/path/DSN"):
        assert_content_payload_secret_safe(contaminated)

    # Request fingerprint for DB never embeds a DSN field.
    db_fp_payload = _db_spec().to_dict()
    assert "dsn" not in db_fp_payload
    assert "password" not in db_fp_payload
    assert collect_forbidden_evidence_keys(db_fp_payload) == []


@pytest.mark.unit
def test_dataset_spec_request_fingerprint_alias() -> None:
    spec = _db_spec()
    assert spec.request_fingerprint() == spec.fingerprint()
    assert request_fingerprint(spec) == spec.fingerprint()


@pytest.mark.unit
def test_decimal_and_float_normalize_identically() -> None:
    float_row = {
        "ts_ms": _BASE_START_MS,
        "open": 50000.5,
        "high": 50001.0,
        "low": 49999.0,
        "close": 50000.25,
        "volume": 10.5,
    }
    decimal_row = {
        "ts_ms": _BASE_START_MS,
        "open": Decimal("50000.5"),
        "high": Decimal("50001.0"),
        "low": Decimal("49999.0"),
        "close": Decimal("50000.25"),
        "volume": Decimal("10.5"),
    }
    assert content_fingerprint([float_row]) == content_fingerprint([decimal_row])
