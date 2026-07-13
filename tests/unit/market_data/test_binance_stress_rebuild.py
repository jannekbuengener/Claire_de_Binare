from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.market_data import binance_window_bank as wb
from tools.market_data.historical_common import ONE_MINUTE_MS, HistoricalProbeError


def _candle(ts_ms: int, *, regime: int = 1) -> dict:
    return {
        "ts_ms": ts_ms,
        "open": "1",
        "high": "1",
        "low": "1",
        "close": str(1 + (ts_ms % 1000) / 100000),
        "volume": "1",
        "regime_id": regime,
    }


def _contiguous_block(start_ms: int, count: int) -> list[dict]:
    return [_candle(start_ms + i * ONE_MINUTE_MS) for i in range(count)]


@pytest.mark.unit
def test_contiguous_islands_splits_on_gap() -> None:
    block_a = _contiguous_block(0, 5)
    block_b = _contiguous_block(10 * ONE_MINUTE_MS, 4)
    islands = wb._contiguous_islands(block_a + block_b)
    assert len(islands) == 2
    assert len(islands[0]) == 5
    assert len(islands[1]) == 4


@pytest.mark.unit
def test_validate_stress_window_rejects_gap_and_duplicates() -> None:
    candles = _contiguous_block(0, 10)
    candles[5] = dict(candles[5])
    candles[5]["ts_ms"] = candles[4]["ts_ms"]
    with pytest.raises(HistoricalProbeError, match="duplicate"):
        wb._validate_stress_window_candles(candles, window_minutes=10)

    gappy = _contiguous_block(0, 5) + [_candle(10 * ONE_MINUTE_MS)]
    with pytest.raises(HistoricalProbeError, match="cadence gap"):
        wb._validate_stress_window_candles(gappy, window_minutes=6)


@pytest.mark.unit
def test_rank_stress_candidates_skips_gappy_windows() -> None:
    window_minutes = 4
    island = _contiguous_block(0, 10)
    ranked = wb._rank_stress_candidates(
        [island],
        metric_key="max_drawdown",
        window_minutes=window_minutes,
        step=1,
    )
    assert len(ranked) == 7
    for _, _, _, chunk in ranked:
        assert wb._is_contiguous_cadence(chunk)
        assert len(chunk) == window_minutes


@pytest.mark.unit
def test_select_stress_chunk_rejects_then_picks_next_deterministically() -> None:
    window_minutes = 3
    island = _contiguous_block(0, 6)
    ranked = wb._rank_stress_candidates(
        [island],
        metric_key="max_vol",
        window_minutes=window_minutes,
        step=1,
    )
    first = wb._select_stress_chunk(ranked, window_minutes=window_minutes)
    assert first is not None
    chunk1, meta1 = first
    second = wb._select_stress_chunk(
        ranked,
        window_minutes=window_minutes,
        reject_start_ts_ms=meta1["start_ts_ms"],
    )
    assert second is not None
    _, meta2 = second
    assert meta2["start_ts_ms"] > meta1["start_ts_ms"]


@pytest.mark.unit
def test_build_stress_windows_single_month_no_gap(tmp_path: Path) -> None:
    month = "2020-01"
    enriched = tmp_path / "artifacts" / "market_data" / "enriched" / "binance" / "spot" / "BTCUSDT" / "1m" / month
    enriched.mkdir(parents=True)
    candles = _contiguous_block(1_578_441_600_000, 20_000)
    (enriched / "candles.jsonl").write_text(
        "\n".join(json.dumps(c) for c in candles),
        encoding="utf-8",
    )
    manifest = {
        "months": [{"month": month, "quality_verdict": "STRICT_COMPLETE"}],
    }
    manifest_path = tmp_path / "artifacts" / "market_data" / "manifests" / "binance_btcusdt_1m_full_import.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with patch.object(wb, "IMPORT_REPO", tmp_path):
        windows = wb.build_stress_windows([month], tmp_path, window_minutes=100)
    assert windows
    for spec in windows:
        assert len(spec.source_months) == 1
        assert spec.candle_count == 100


@pytest.mark.unit
def test_extract_stress_window_candles_no_interpolation(tmp_path: Path) -> None:
    month = "2020-01"
    enriched = tmp_path / "artifacts" / "market_data" / "enriched" / "binance" / "spot" / "BTCUSDT" / "1m" / month
    enriched.mkdir(parents=True)
    candles = _contiguous_block(0, 20)
    (enriched / "candles.jsonl").write_text(
        "\n".join(json.dumps(c) for c in candles),
        encoding="utf-8",
    )
    with patch.object(wb, "IMPORT_REPO", tmp_path):
        chunk = wb._extract_stress_window_candles(
            tmp_path,
            (month,),
            start_ts_ms=0,
            end_ts_ms=9 * ONE_MINUTE_MS,
            window_minutes=10,
        )
    assert len(chunk) == 10
    assert wb._cadence_gaps(chunk) == []


@pytest.mark.unit
def test_rebuild_stress_v2_writes_new_fingerprints(tmp_path: Path) -> None:
    month = "2020-01"
    enriched = tmp_path / "artifacts" / "market_data" / "enriched" / "binance" / "spot" / "BTCUSDT" / "1m" / month
    enriched.mkdir(parents=True)
    candles = _contiguous_block(1_578_441_600_000, 20_000)
    (enriched / "candles.jsonl").write_text(
        "\n".join(json.dumps(c) for c in candles),
        encoding="utf-8",
    )
    bank_root = tmp_path / "artifacts" / "market_data" / "window_bank" / "binance" / "spot" / "BTCUSDT" / "1m"
    old_id = "binance_1m_stress_max_drawdown"
    old_dir = bank_root / old_id
    old_dir.mkdir(parents=True)
    bad = _contiguous_block(1_578_441_600_000, 720) + _contiguous_block(
        1_543_622_400_000, 9360
    )
    (old_dir / "candles.jsonl").write_text(
        "\n".join(json.dumps(c) for c in bad),
        encoding="utf-8",
    )
    fp_old = wb.sha256_file(old_dir / "candles.jsonl")

    manifest = {
        "months": [{"month": month, "quality_verdict": "STRICT_COMPLETE"}],
        "source_sha": "abc123",
    }
    manifest_path = tmp_path / "artifacts" / "market_data" / "manifests" / "binance_btcusdt_1m_full_import.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    bank_manifest = {
        "windows": [
            {
                "window_id": old_id,
                "start_ts_ms": bad[0]["ts_ms"],
                "end_ts_ms": bad[-1]["ts_ms"],
                "candle_count": len(bad),
                "source_months": [month],
                "candles_path": str(old_dir / "candles.jsonl").replace("\\", "/"),
                "overlap_class": "stress",
            }
        ]
    }
    bank_root.mkdir(parents=True, exist_ok=True)
    (bank_root / "window_bank_manifest.json").write_text(
        json.dumps(bank_manifest),
        encoding="utf-8",
    )

    with patch.object(wb, "IMPORT_REPO", tmp_path):
        result = wb.rebuild_stress_windows_v2(
            tmp_path,
            metrics=("stress_max_drawdown",),
        )
    assert result["written_v2"]
    v2_id = result["written_v2"][0]["window_id"]
    assert v2_id.endswith("_v2")
    v2_path = bank_root / v2_id / "candles.jsonl"
    assert v2_path.exists()
    fp_new = wb.sha256_file(v2_path)
    assert fp_new != fp_old
    rejection = bank_root / old_id / "rejection_evidence.json"
    assert rejection.exists()


@pytest.mark.unit
def test_stress_rerun_manifest_schedules_exactly_six_jobs(tmp_path: Path) -> None:
    bank_root = tmp_path / "artifacts" / "market_data" / "window_bank" / "binance" / "spot" / "BTCUSDT" / "1m"
    for idx, wid in enumerate(
        ("binance_1m_stress_max_drawdown_v2", "binance_1m_stress_max_volatility_v2")
    ):
        d = bank_root / wid
        d.mkdir(parents=True)
        candles_path = d / "candles.jsonl"
        start = idx * 100 * ONE_MINUTE_MS
        candles_path.write_text(
            "\n".join(
                json.dumps(_candle(start + i * ONE_MINUTE_MS)) for i in range(10)
            ),
            encoding="utf-8",
        )
        fp = wb.sha256_file(candles_path)
        spec = {
            "dataset_id": wid,
            "window_id": wid,
            "fingerprint": fp,
            "candles_sha256": fp,
            "file_path": str(candles_path).replace("\\", "/"),
            "symbol": "BTCUSDT",
            "start_ts_ms": start,
            "end_ts_ms": start + 9 * ONE_MINUTE_MS,
            "evidence_class": "controlled_lab_evidence",
            "evidence_subclass": "historical_cross_venue_research",
            "ranking_ready": False,
        }
        (d / "dataset_spec.json").write_text(json.dumps(spec), encoding="utf-8")

    import_path = tmp_path / "artifacts" / "market_data" / "manifests" / "binance_btcusdt_1m_full_import.json"
    import_path.parent.mkdir(parents=True)
    import_path.write_text(json.dumps({"source_sha": "deadbeef"}), encoding="utf-8")

    with patch.object(wb, "IMPORT_REPO", tmp_path):
        manifest_path = wb.build_stress_rerun_manifest(
            tmp_path,
            campaign_id="test_campaign",
            source_sha="deadbeef",
        )
    from tools.arvp_vacation.coordinator import preflight_manifest

    info = preflight_manifest(manifest_path, tmp_path)
    assert info["dataset_count"] == 2
    assert info["job_count_estimate"] == 6


@pytest.mark.unit
def test_assert_no_legacy_market_data_path_rejects_e_drive() -> None:
    with pytest.raises(HistoricalProbeError, match="legacy market_data"):
        wb._assert_no_legacy_market_data_path(
            "E:/CDB_artifacts/market_data/window_bank/foo/candles.jsonl"
        )


@pytest.mark.unit
def test_rebuild_stress_v2_skips_when_existing_valid(tmp_path: Path) -> None:
    month = "2021-05"
    enriched = tmp_path / "artifacts" / "market_data" / "enriched" / "binance" / "spot" / "BTCUSDT" / "1m" / month
    enriched.mkdir(parents=True)
    candles = _contiguous_block(1_620_885_600_000, 20_000)
    (enriched / "candles.jsonl").write_text(
        "\n".join(json.dumps(c) for c in candles),
        encoding="utf-8",
    )
    bank_root = tmp_path / "artifacts" / "market_data" / "window_bank" / "binance" / "spot" / "BTCUSDT" / "1m"
    for wid, start in (
        ("binance_1m_stress_max_drawdown_v2", 1_620_885_600_000),
        ("binance_1m_stress_max_volatility_v2", 1_621_339_200_000),
    ):
        d = bank_root / wid
        d.mkdir(parents=True)
        chunk = _contiguous_block(start, wb.STRESS_V2_WINDOW_MINUTES)
        cp = d / "candles.jsonl"
        cp.write_text("\n".join(json.dumps(c) for c in chunk), encoding="utf-8")
        fp = wb.sha256_file(cp)
        spec = {
            "dataset_id": wid,
            "window_id": wid,
            "fingerprint": fp,
            "candles_sha256": fp,
            "file_path": str(cp.resolve()).replace("\\", "/"),
            "symbol": "BTCUSDT",
            "timeframe": "1m",
            "start_ts_ms": int(chunk[0]["ts_ms"]),
            "end_ts_ms": int(chunk[-1]["ts_ms"]),
            "data_quality_verdict": "STRICT_COMPLETE",
            "venue": "binance",
            "evidence_subclass": "historical_cross_venue_research",
            "ranking_ready": False,
            "source_months": [month],
            "overlap_class": "stress",
        }
        (d / "dataset_spec.json").write_text(json.dumps(spec), encoding="utf-8")

    import_path = tmp_path / "artifacts" / "market_data" / "manifests" / "binance_btcusdt_1m_full_import.json"
    import_path.parent.mkdir(parents=True)
    import_path.write_text(
        json.dumps({"months": [{"month": month, "quality_verdict": "STRICT_COMPLETE"}]}),
        encoding="utf-8",
    )
    (bank_root / "window_bank_manifest.json").write_text("{}", encoding="utf-8")

    with patch.object(wb, "IMPORT_REPO", tmp_path):
        result = wb.rebuild_stress_windows_v2(tmp_path)
    assert result.get("skipped_rebuild") is True
    assert result.get("written_v2") == []
