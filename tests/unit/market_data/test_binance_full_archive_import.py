from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.market_data import assign_regime_offline
from tools.market_data import binance_full_archive_import as full_import
from tools.market_data import binance_window_bank as window_bank
from tools.market_data import historical_common as common

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "market_data"


def _fake_listing_html(months: list[str]) -> str:
    keys = "\n".join(
        f"<Key>data/spot/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-{m}.zip</Key>"
        for m in months
    )
    return f"<ListBucketResult>{keys}</ListBucketResult>"


def _build_zip(csv_bytes: bytes, member: str = "BTCUSDT-1m-2020-01.csv") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member, csv_bytes)
    return buffer.getvalue()


class _FakeResponse:
    def __init__(self, body: bytes, headers: dict[str, str] | None = None) -> None:
        self._body = body
        self.headers = headers or {}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _fake_opener(mapping: dict[str, bytes]):
    from urllib.error import HTTPError

    def _open(request, timeout=120):  # noqa: ARG001
        url = request.full_url
        if url not in mapping:
            raise HTTPError(url, 404, "not found", None, io.BytesIO(b""))
        return _FakeResponse(mapping[url])

    return _open


@pytest.mark.unit
def test_list_available_months_from_s3_listing() -> None:
    months = ["2017-08", "2020-01", "2026-06"]
    fetcher = common.HttpFetcher(
        opener=_fake_opener(
            {full_import.S3_LISTING_URL: _fake_listing_html(months).encode()}
        )
    )
    result = full_import.list_available_months(fetcher)
    assert result == months


@pytest.mark.unit
def test_last_complete_month_excludes_current() -> None:
    from datetime import UTC, datetime

    now = datetime(2026, 7, 12, tzinfo=UTC)
    assert full_import.last_complete_month(now=now) == "2026-06"
    assert full_import.last_complete_month(
        now=now, available=["2017-08", "2026-05", "2026-06", "2026-07"]
    ) == "2026-06"


@pytest.mark.unit
def test_missing_month_not_in_range() -> None:
    months = ["2020-01", "2020-03"]
    fetcher = common.HttpFetcher(
        opener=_fake_opener(
            {full_import.S3_LISTING_URL: _fake_listing_html(months).encode()}
        )
    )
    with patch.object(full_import, "list_available_months", return_value=months):
        with patch.object(
            full_import,
            "_import_single_month",
            side_effect=common.HistoricalProbeError("missing"),
        ):
            manifest = full_import.import_range(
                start_month="2020-01",
                end_month="2020-03",
                fetcher=fetcher,
                max_retries=1,
            )
    assert manifest["summary"]["failed"] >= 1


@pytest.mark.unit
def test_checksum_fail_month_isolated(tmp_path: Path) -> None:
    csv_bytes = (FIXTURE_DIR / "binance_btcusdt_1m_sample.csv").read_bytes()
    zip_bytes = _build_zip(csv_bytes, "BTCUSDT-1m-2020-01.csv")
    digest = hashlib.sha256(zip_bytes).hexdigest()
    wrong = "f" * 64
    archive_url = (
        "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1m/"
        "BTCUSDT-1m-2020-01.zip"
    )
    checksum_url = archive_url + ".CHECKSUM"
    fetcher = common.HttpFetcher(
        opener=_fake_opener(
            {
                archive_url: zip_bytes,
                checksum_url: f"{wrong}  BTCUSDT-1m-2020-01.zip\n".encode(),
            }
        )
    )
    with pytest.raises(common.HistoricalProbeError, match="hash mismatch"):
        full_import._import_single_month(
            month="2020-01",
            repo_root=tmp_path,
            fetcher=fetcher,
            skip_download=False,
        )


@pytest.mark.unit
def test_resume_existing_valid_month(tmp_path: Path) -> None:
    csv_bytes = (FIXTURE_DIR / "binance_btcusdt_1m_sample.csv").read_bytes()
    zip_bytes = _build_zip(csv_bytes, "BTCUSDT-1m-2020-02.csv")
    digest = hashlib.sha256(zip_bytes).hexdigest()
    archive_url = (
        "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1m/"
        "BTCUSDT-1m-2020-02.zip"
    )
    checksum_url = archive_url + ".CHECKSUM"
    raw_dir = full_import._raw_dir(tmp_path, "2020-02")
    raw_dir.mkdir(parents=True)
    (raw_dir / "BTCUSDT-1m-2020-02.zip").write_bytes(zip_bytes)
    (raw_dir / "BTCUSDT-1m-2020-02.zip.CHECKSUM").write_text(
        f"{digest}  BTCUSDT-1m-2020-02.zip\n", encoding="utf-8"
    )
    fetcher = common.HttpFetcher(opener=_fake_opener({}))
    result = full_import._import_single_month(
        month="2020-02",
        repo_root=tmp_path,
        fetcher=fetcher,
        skip_download=True,
    )
    assert result["checksum_verified"] is True


@pytest.mark.unit
def test_regime_carry_over_across_chunks() -> None:
    rows = [
        {
            "ts_ms": 1780272000000 + i * 60_000,
            "open": str(100 + i * 0.01),
            "high": str(101 + i * 0.01),
            "low": str(99 + i * 0.01),
            "close": str(100.5 + i * 0.01),
            "volume": "1",
        }
        for i in range(400)
    ]
    first_chunk, state = assign_regime_offline.assign_regime_ids_with_state(rows[:200])
    second_chunk, _ = assign_regime_offline.assign_regime_ids_with_state(
        rows[200:], initial_state=state
    )
    combined = assign_regime_offline.assign_regime_ids(rows)
    assert len(first_chunk) + len(second_chunk) == len(combined)
    assert all("regime_id" in r for r in first_chunk + second_chunk)


@pytest.mark.unit
def test_regime_plausibility_not_blocking() -> None:
    rows = [
        {
            "ts_ms": 1780272000000 + i * 60_000,
            "open": "100000",
            "high": "100100",
            "low": "99900",
            "close": "100050",
            "volume": "1",
            "regime_id": 2,
        }
        for i in range(300)
    ]
    report = assign_regime_offline.analyze_regime_plausibility(rows)
    assert report["blocking"] is False
    assert report["status"] in {"PASS", "PASS_WITH_CAVEAT"}


@pytest.mark.unit
def test_temporal_split_reserves_oos() -> None:
    months = [f"202{i // 12 + 0:04d}-{i % 12 + 1:02d}" for i in range(24)]
    months = [f"2020-{m:02d}" for m in range(1, 13)] + [
        f"2021-{m:02d}" for m in range(1, 13)
    ]
    split = window_bank.compute_temporal_split(months, oos_fraction=0.20)
    assert len(split["out_of_sample"]) >= 4
    assert len(split["development"]) >= 1
    assert set(split["development"] + split["validation"] + split["out_of_sample"]) == set(
        months
    )


@pytest.mark.unit
def test_window_dedup() -> None:
    a = window_bank.WindowSpec(
        window_id="a",
        start_ts_ms=1,
        end_ts_ms=2,
        candle_count=10,
        dataset_fingerprint="",
        regime_distribution={},
        source_months=("2020-01",),
        overlap_class="monthly",
        evidence_class="controlled_lab_evidence",
        purpose="development",
        quality_verdict="STRICT_COMPLETE",
        candles_path="",
        spec_path="",
    )
    b = window_bank.WindowSpec(
        window_id="b",
        start_ts_ms=1,
        end_ts_ms=2,
        candle_count=10,
        dataset_fingerprint="",
        regime_distribution={},
        source_months=("2020-01",),
        overlap_class="monthly",
        evidence_class="controlled_lab_evidence",
        purpose="development",
        quality_verdict="STRICT_COMPLETE",
        candles_path="",
        spec_path="",
    )
    assert len(window_bank.deduplicate_windows([a, b])) == 1


@pytest.mark.unit
def test_leap_year_february_bounds() -> None:
    start, end, expected = common.month_bounds(2024, 2)
    assert expected == 29 * 24 * 60


@pytest.mark.unit
def test_coverage_report_shape() -> None:
    records = [
        full_import.MonthImportRecord(
            month="2020-01",
            quality_verdict="STRICT_COMPLETE",
            candle_count=44640,
        )
    ]
    cov = full_import.build_coverage_report(records, ["2020-01"])
    assert cov["strict_complete_months"] == 1
    assert cov["total_candles"] == 44640


@pytest.mark.unit
def test_vacation_manifest_cross_venue(tmp_path: Path) -> None:
    bank = {
        "source_sha": "abc123",
        "bank_root": str(tmp_path / "bank"),
        "windows": [],
    }
    with patch.object(window_bank, "REPO_ROOT", tmp_path):
        path = window_bank.build_vacation_manifest(bank, repo_root=tmp_path)
    raw = path.read_text(encoding="utf-8")
    assert "allow_paper_jobs: false" in raw
    assert "donchian_breakout_v1" in raw
    data = __import__("yaml").safe_load(raw)
    assert data["evidence_class"] == "controlled_lab_evidence"
