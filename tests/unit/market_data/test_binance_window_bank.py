from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.market_data import binance_window_bank as wb


@pytest.mark.unit
def test_compute_temporal_split_no_overlap() -> None:
    months = [f"2022-{m:02d}" for m in range(1, 13)]
    split = wb.compute_temporal_split(months)
    dev = set(split["development"])
    val = set(split["validation"])
    oos = set(split["out_of_sample"])
    assert dev.isdisjoint(val)
    assert dev.isdisjoint(oos)
    assert val.isdisjoint(oos)
    assert len(oos) >= 2


@pytest.mark.unit
def test_strict_complete_months_filters() -> None:
    manifest = {
        "months": [
            {"month": "2020-01", "quality_verdict": "STRICT_COMPLETE"},
            {"month": "2020-02", "quality_verdict": "CHECKSUM_FAILED"},
            {"month": "2020-03", "quality_verdict": "STRICT_COMPLETE"},
        ]
    }
    assert wb.strict_complete_months(manifest) == ["2020-01", "2020-03"]


@pytest.mark.unit
def test_window_spec_evidence_class() -> None:
    spec = wb.WindowSpec(
        window_id="binance_1m_month_2020_01",
        start_ts_ms=1,
        end_ts_ms=2,
        candle_count=100,
        dataset_fingerprint="a" * 64,
        regime_distribution={"0": {"count": 50}},
        source_months=("2020-01",),
        overlap_class="monthly",
        evidence_class="controlled_lab_evidence",
        purpose="development",
        quality_verdict="STRICT_COMPLETE",
        candles_path="/x/candles.jsonl",
        spec_path="/x/dataset_spec.json",
    )
    assert spec.evidence_class == "controlled_lab_evidence"
    assert spec.purpose in wb.PURPOSES


@pytest.mark.unit
def test_build_window_bank_requires_manifest(tmp_path: Path) -> None:
    with patch.object(wb, "IMPORT_REPO", tmp_path):
        with pytest.raises(Exception, match="Import manifest missing"):
            wb.build_window_bank(tmp_path)


@pytest.mark.unit
def test_enforce_contiguous_cadence_stops_at_gap() -> None:
    candles = [
        {"ts_ms": 0},
        {"ts_ms": 60_000},
        {"ts_ms": 120_000},
        {"ts_ms": 5_270_580_000},  # multi-day gap
        {"ts_ms": 5_270_640_000},
    ]
    out = wb._enforce_contiguous_cadence(candles)
    assert len(out) == 3
    assert wb._is_contiguous_cadence(out)
    assert not wb._is_contiguous_cadence(candles)
