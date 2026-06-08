from __future__ import annotations

from decimal import Decimal

import pytest

from scripts.replay.candle_continuity import (
    CandleContinuityError,
    CandleRow,
    build_continuity_report,
    candle_rows_checksum,
    collapse_missing_timestamps,
    expected_timestamps,
    parse_binance_kline,
    parse_mexc_kline,
)


BASE_TS = 1_000_000_020_000


def test_expected_timestamps_include_warmup_and_end() -> None:
    assert expected_timestamps(
        start_ts_ms=BASE_TS,
        end_ts_ms=BASE_TS + 120_000,
        warmup_candles=2,
    ) == [
        BASE_TS - 120_000,
        BASE_TS - 60_000,
        BASE_TS,
        BASE_TS + 60_000,
        BASE_TS + 120_000,
    ]


def test_build_continuity_report_marks_ready_when_all_expected_exist() -> None:
    observed = expected_timestamps(
        start_ts_ms=BASE_TS,
        end_ts_ms=BASE_TS + 120_000,
        warmup_candles=1,
    )
    report = build_continuity_report(
        symbol="btcusdt",
        start_ts_ms=BASE_TS,
        end_ts_ms=BASE_TS + 120_000,
        warmup_candles=1,
        observed_ts_ms=observed,
    )
    assert report["symbol"] == "BTCUSDT"
    assert report["replay_ready"] is True
    assert report["missing_count"] == 0
    assert report["gaps"] == []
    assert len(report["continuity_fingerprint"]) == 64


def test_build_continuity_report_localizes_missing_gap() -> None:
    observed = [
        BASE_TS - 60_000,
        BASE_TS,
        BASE_TS + 120_000,
    ]
    report = build_continuity_report(
        symbol="BTCUSDT",
        start_ts_ms=BASE_TS,
        end_ts_ms=BASE_TS + 120_000,
        warmup_candles=1,
        observed_ts_ms=observed,
    )
    assert report["replay_ready"] is False
    assert report["missing_count"] == 1
    assert report["gaps"] == [
        {
            "start_ts_ms": BASE_TS + 60_000,
            "end_ts_ms": BASE_TS + 60_000,
            "missing_count": 1,
            "timestamps": [BASE_TS + 60_000],
        }
    ]


def test_collapse_missing_timestamps_groups_contiguous_ranges() -> None:
    assert collapse_missing_timestamps(
        [1000, 1000 + 60_000, 1000 + 180_000]
    ) == [
        {
            "start_ts_ms": 1000,
            "end_ts_ms": 61_000,
            "missing_count": 2,
            "timestamps": [1000, 61_000],
        },
        {
            "start_ts_ms": 181_000,
            "end_ts_ms": 181_000,
            "missing_count": 1,
            "timestamps": [181_000],
        },
    ]


def test_parse_binance_kline_maps_real_source_row() -> None:
    row = parse_binance_kline(
        "btcusdt",
        [
            1_000_000_020_000,
            "50000.01000000",
            "50010.02000000",
            "49990.03000000",
            "50005.04000000",
            "12.34567890",
            1_000_000_079_999,
            "617000.00",
            42,
        ],
    )
    assert row == CandleRow(
        symbol="BTCUSDT",
        ts_ms=1_000_000_020_000,
        open=Decimal("50000.01000000"),
        high=Decimal("50010.02000000"),
        low=Decimal("49990.03000000"),
        close=Decimal("50005.04000000"),
        volume=Decimal("12.34567890"),
        trade_count=42,
    )


def test_parse_binance_kline_rejects_unaligned_open_time() -> None:
    with pytest.raises(CandleContinuityError, match="1m-aligned"):
        parse_binance_kline(
            "BTCUSDT",
            [1_000_000_020_001, "1", "1", "1", "1", "1", 0, "0", 1],
        )


def test_parse_mexc_kline_maps_eight_field_response() -> None:
    row = parse_mexc_kline(
        "btcusdt",
        [
            1_000_000_020_000,
            "50000.01000000",
            "50010.02000000",
            "49990.03000000",
            "50005.04000000",
            "12.34567890",
            1_000_000_079_999,
            "617000.00",
            99,
        ],
    )
    assert row == CandleRow(
        symbol="BTCUSDT",
        ts_ms=1_000_000_020_000,
        open=Decimal("50000.01000000"),
        high=Decimal("50010.02000000"),
        low=Decimal("49990.03000000"),
        close=Decimal("50005.04000000"),
        volume=Decimal("12.34567890"),
        trade_count=0,
    )


def test_parse_mexc_kline_accepts_seven_fields() -> None:
    row = parse_mexc_kline(
        "BTCUSDT",
        [
            1_000_000_020_000,
            "50000.0",
            "50100.0",
            "49900.0",
            "50050.0",
            "10.0",
            1_000_000_079_999,
        ],
    )
    assert row.symbol == "BTCUSDT"
    assert row.trade_count == 0
    assert row.open == Decimal("50000.0")


def test_parse_mexc_kline_rejects_too_few_fields() -> None:
    with pytest.raises(CandleContinuityError, match="fewer than 7 fields"):
        parse_mexc_kline(
            "BTCUSDT",
            [1_000_000_020_000, "50000.0", "50100.0", "49900.0", "50050.0", "10.0"],
        )


def test_parse_mexc_kline_rejects_unaligned_open_time() -> None:
    with pytest.raises(CandleContinuityError, match="1m-aligned"):
        parse_mexc_kline(
            "BTCUSDT",
            [1_000_000_020_001, "50000.0", "50100.0", "49900.0", "50050.0", "10.0", 1_000_000_079_999, "600000.0"],
        )


def test_parse_mexc_kline_rejects_non_positive_ohlc() -> None:
    with pytest.raises(CandleContinuityError, match="non-positive OHLC"):
        parse_mexc_kline(
            "BTCUSDT",
            [1_000_000_020_000, "0.0", "50100.0", "49900.0", "50050.0", "10.0", 1_000_000_079_999, "600000.0"],
        )


def test_parse_mexc_kline_rejects_high_below_low() -> None:
    with pytest.raises(CandleContinuityError, match="high is below low"):
        parse_mexc_kline(
            "BTCUSDT",
            [1_000_000_020_000, "50000.0", "49900.0", "50100.0", "50050.0", "10.0", 1_000_000_079_999, "600000.0"],
        )


def test_parse_mexc_kline_rejects_negative_volume() -> None:
    with pytest.raises(CandleContinuityError, match="negative volume"):
        parse_mexc_kline(
            "BTCUSDT",
            [1_000_000_020_000, "50000.0", "50100.0", "49900.0", "50050.0", "-10.0", 1_000_000_079_999, "600000.0"],
        )


def test_candle_rows_checksum_is_stable_and_order_independent() -> None:
    a = CandleRow(
        symbol="BTCUSDT",
        ts_ms=1_000_000_020_000,
        open=Decimal("1.0"),
        high=Decimal("2.0"),
        low=Decimal("1.0"),
        close=Decimal("1.5"),
        volume=Decimal("3.0"),
        trade_count=4,
    )
    b = CandleRow(
        symbol="BTCUSDT",
        ts_ms=1_000_000_080_000,
        open=Decimal("1.5"),
        high=Decimal("2.5"),
        low=Decimal("1.4"),
        close=Decimal("2.0"),
        volume=Decimal("5.0"),
        trade_count=6,
    )
    assert candle_rows_checksum([a, b]) == candle_rows_checksum([b, a])


def test_build_backfill_manifest_without_apply_produces_zero_inserts() -> None:
    from scripts.replay.candle_continuity import build_backfill_manifest

    rows = [
        CandleRow(
            symbol="BTCUSDT",
            ts_ms=1_000_000_020_000,
            open=Decimal("50000.0"),
            high=Decimal("50100.0"),
            low=Decimal("49900.0"),
            close=Decimal("50050.0"),
            volume=Decimal("10.0"),
            trade_count=42,
        ),
        CandleRow(
            symbol="BTCUSDT",
            ts_ms=1_000_000_080_000,
            open=Decimal("50050.0"),
            high=Decimal("50200.0"),
            low=Decimal("50000.0"),
            close=Decimal("50100.0"),
            volume=Decimal("15.0"),
            trade_count=55,
        ),
    ]
    manifest = build_backfill_manifest(
        source="binance_spot_api_v3_klines",
        source_urls=["https://api.binance.com/api/v3/klines?test=1"],
        import_command="test --no-apply",
        symbol="BTCUSDT",
        start_ts_ms=1_000_000_020_000,
        end_ts_ms=1_000_000_080_000,
        rows=rows,
        inserted_count=0,
        skipped_existing_count=0,
    )
    assert manifest["contract_version"] == "cdb_candle_backfill_import.v1"
    assert manifest["source"] == "binance_spot_api_v3_klines"
    assert manifest["inserted_count"] == 0
    assert manifest["skipped_existing_count"] == 0
    assert manifest["row_count"] == 2
    assert len(manifest["rows"]) == 2
    assert manifest["rows"][0]["ts_ms"] == 1_000_000_020_000
    assert manifest["rows"][1]["ts_ms"] == 1_000_000_080_000
    assert "import_id" in manifest
    assert "checksum_sha256" in manifest
    assert manifest["checksum_sha256"] == candle_rows_checksum(rows)
