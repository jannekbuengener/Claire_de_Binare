from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.market_data import binance_archive_manifest_reconcile as reconcile
from tools.market_data.historical_common import write_json


def _write_month(
    root: Path,
    month: str,
    *,
    verdict: str = "STRICT_COMPLETE",
    candles: int = 100,
) -> None:
    month_dir = (
        root
        / "normalized"
        / "binance"
        / "spot"
        / "BTCUSDT"
        / "1m"
        / month
    )
    month_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        month_dir / "quality_report.json",
        {
            "verdict": verdict,
            "gaps": {"actual_candles": candles},
            "duplicates": {},
        },
    )
    write_json(month_dir / "gap_report.json", {"actual_candles": candles})


@pytest.mark.unit
def test_reconcile_writes_only_output_dir(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    out = tmp_path / "out"
    _write_month(root, "2020-01", candles=50)
    wb_path = (
        root
        / "window_bank"
        / "binance"
        / "spot"
        / "BTCUSDT"
        / "1m"
        / "window_bank_manifest.json"
    )
    wb_path.parent.mkdir(parents=True)
    write_json(wb_path, {"windows": [], "stress_v2_rebuild": {"written_v2": []}})
    before = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    report = reconcile.reconcile_market_data_root(
        market_data_root=root,
        output_dir=out,
        expected={
            "earliest_month": "2020-01",
            "latest_month": "2020-01",
            "total_months": 1,
            "strict_complete": 1,
            "partial_usable": 0,
            "failed": 0,
            "total_candles": 50,
            "base_window_count": 0,
            "stress_v2_window_count": 0,
            "total_window_count": 0,
        },
    )
    after = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    assert before == after
    assert (out / "reconcile_report.json").is_file()
    assert report["verdict"] == "PASS"


@pytest.mark.unit
def test_reconcile_detects_stale_manifest_without_mutation(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    out = tmp_path / "out"
    _write_month(root, "2020-01", candles=10)
    manifest_path = root / "manifests" / "binance_btcusdt_1m_full_import.json"
    manifest_path.parent.mkdir(parents=True)
    stale = {"import_status": "FULL_IMPORT_PARTIAL", "coverage": {"month_count": 2}}
    write_json(manifest_path, stale)
    before = manifest_path.read_text(encoding="utf-8")
    reconcile.reconcile_market_data_root(
        market_data_root=root,
        output_dir=out,
        expected={
            "earliest_month": "2020-01",
            "latest_month": "2020-01",
            "total_months": 1,
            "strict_complete": 1,
            "partial_usable": 0,
            "failed": 0,
            "total_candles": 10,
            "base_window_count": 0,
            "stress_v2_window_count": 0,
            "total_window_count": 0,
        },
    )
    assert manifest_path.read_text(encoding="utf-8") == before
    payload = json.loads((out / "reconcile_report.json").read_text(encoding="utf-8"))
    assert payload["stale_manifest_summary"]["month_count"] == 2


@pytest.mark.unit
def test_reconcile_missing_quality_report_fails_contract(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    out = tmp_path / "out"
    month_dir = root / "normalized" / "binance" / "spot" / "BTCUSDT" / "1m" / "2020-02"
    month_dir.mkdir(parents=True)
    report = reconcile.reconcile_market_data_root(
        market_data_root=root,
        output_dir=out,
        expected={
            "earliest_month": "2020-02",
            "latest_month": "2020-02",
            "total_months": 1,
            "strict_complete": 0,
            "partial_usable": 0,
            "failed": 0,
            "total_candles": 0,
            "base_window_count": 0,
            "stress_v2_window_count": 0,
            "total_window_count": 0,
        },
    )
    assert report["verdict"] == "HOLD_DATASET_CONTRACT_MISMATCH"
    assert report["missing_files"]


@pytest.mark.unit
def test_reconcile_network_guard_blocks_urlopen() -> None:
    reconcile._guard_network_import()
    import urllib.request

    with pytest.raises(reconcile.NetworkAttemptError):
        urllib.request.urlopen("https://example.com")  # type: ignore[arg-type]


@pytest.mark.unit
def test_window_bank_stress_v2_split(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    out = tmp_path / "out"
    _write_month(root, "2020-01", candles=10)
    wb_path = (
        root
        / "window_bank"
        / "binance"
        / "spot"
        / "BTCUSDT"
        / "1m"
        / "window_bank_manifest.json"
    )
    wb_path.parent.mkdir(parents=True)
    write_json(
        wb_path,
        {
            "windows": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
            "stress_v2_rebuild": {"written_v2": ["stress_a_v2", "stress_b_v2"]},
        },
    )
    report = reconcile.reconcile_market_data_root(
        market_data_root=root,
        output_dir=out,
        expected={
            "earliest_month": "2020-01",
            "latest_month": "2020-01",
            "total_months": 1,
            "strict_complete": 1,
            "partial_usable": 0,
            "failed": 0,
            "total_candles": 10,
            "base_window_count": 1,
            "stress_v2_window_count": 2,
            "total_window_count": 3,
        },
    )
    assert report["base_window_count"] == 1
    assert report["stress_v2_window_count"] == 2
    assert report["total_window_count"] == 3
