from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

import pytest

from tools.market_data import mexc_historical_probe as probe

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "market_data"


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
    def _open(request, timeout=60):  # noqa: ARG001
        url = request.full_url
        if url not in mapping:
            raise HTTPError(url, 404, "not found", None, io.BytesIO(b""))
        headers = {"Content-Type": "application/json"}
        if url.endswith(".csv"):
            headers = {"Content-Type": "text/csv"}
        return _FakeResponse(mapping[url], headers)

    return _open


@pytest.mark.unit
def test_normalize_timestamp_ms_seconds_and_millis() -> None:
    assert probe.normalize_timestamp_ms(1780272000) == 1780272000000
    assert probe.normalize_timestamp_ms("1780272000000") == 1780272000000


@pytest.mark.unit
def test_parse_historical_rows_from_fixture() -> None:
    path = FIXTURE_DIR / "mexc_btcusdt_min1_sample.csv"
    source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    rows = probe.parse_historical_rows(
        path,
        symbol="BTCUSDT",
        timeframe="1m",
        source_file_sha256=source_hash,
    )
    assert len(rows) == 3
    assert rows[0].ts_ms == 1780272000000
    assert rows[0].trade_count is None
    assert rows[0].quote_volume is not None


@pytest.mark.unit
def test_html_response_rejected(tmp_path: Path) -> None:
    fetcher = probe.HttpFetcher(opener=_fake_opener({}))
    destination = tmp_path / "bad.csv"
    html = (FIXTURE_DIR / "mexc_login_response.html").read_bytes()
    fetcher._opener = _fake_opener({"https://example.test/bad.csv": html})  # type: ignore[method-assign]
    with pytest.raises(probe.MexcHistoricalProbeError, match="Refusing non-market-data"):
        fetcher.download("https://example.test/bad.csv", destination)


@pytest.mark.unit
def test_partial_download_not_finalized(tmp_path: Path) -> None:
    csv_bytes = (FIXTURE_DIR / "mexc_btcusdt_min1_sample.csv").read_bytes()

    def _boom(request, timeout=60):  # noqa: ARG001
        raise OSError("connection reset")

    fetcher = probe.HttpFetcher(opener=_boom)
    destination = tmp_path / "sample.csv"
    with pytest.raises(probe.MexcHistoricalProbeError, match="Network error"):
        fetcher.download("https://example.test/sample.csv", destination)
    assert not destination.exists()
    assert not destination.with_suffix(".csv.partial").exists()


@pytest.mark.unit
def test_idempotent_download_and_hash_conflict(tmp_path: Path) -> None:
    csv_bytes = (FIXTURE_DIR / "mexc_btcusdt_min1_sample.csv").read_bytes()
    url = "https://example.test/sample.csv"
    fetcher = probe.HttpFetcher(opener=_fake_opener({url: csv_bytes}))
    destination = tmp_path / "sample.csv"
    first = fetcher.download(url, destination)
    second = fetcher.download(url, destination)
    assert first.sha256 == second.sha256
    destination.write_text("mutated", encoding="utf-8")
    with pytest.raises(probe.MexcHistoricalProbeError, match="different hash"):
        fetcher.download(url, destination, expected_sha256=first.sha256)


@pytest.mark.unit
def test_archive_traversal_blocked(tmp_path: Path) -> None:
    archive_path = tmp_path / "evil.zip"
    import zipfile

    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../outside.csv", "bad")
    with pytest.raises(probe.MexcHistoricalProbeError, match="traversal"):
        probe.inspect_archive(archive_path)


@pytest.mark.unit
def test_gap_duplicate_and_ohlc_validation() -> None:
    path = FIXTURE_DIR / "mexc_btcusdt_min1_sample.csv"
    source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    rows = probe.parse_historical_rows(
        path,
        symbol="BTCUSDT",
        timeframe="1m",
        source_file_sha256=source_hash,
    )
    dupes = probe.detect_duplicates(rows + [rows[0]])
    assert dupes["identical_duplicates"] == 1
    gaps = probe.detect_gaps(
        rows,
        start_ts_ms=1780272000000,
        end_ts_ms=1780272120000,
        step_ms=probe.ONE_MINUTE_MS,
    )
    assert gaps["missing_minutes"] == 0
    assert not probe.validate_ohlc(rows)


@pytest.mark.unit
def test_month_bounds_june_2026() -> None:
    start, end, expected = probe.month_bounds(2026, 6)
    assert start == 1780272000000
    assert end == 1782863940000
    assert expected == 43200


@pytest.mark.unit
def test_discovery_blocks_missing_min1_interval() -> None:
    symbol_id = probe.KNOWN_SYMBOL_IDS["BTCUSDT"]
    listing = {
        probe.build_file_svc_url(
            probe.DEFAULT_FILE_SVC_BASE, f"SPOT2/kline/{symbol_id}/monthly/"
        ): json.dumps({"data": ["Day1/", "Min5/", "Min15/"]}).encode("utf-8"),
        probe.build_file_svc_url(
            probe.DEFAULT_FILE_SVC_BASE, f"SPOT2/kline/{symbol_id}/daily/"
        ): json.dumps({"data": ["Day1/", "Min5/"]}).encode("utf-8"),
    }
    fetcher = probe.HttpFetcher(opener=_fake_opener(listing))
    discovery = probe.discover_source(fetcher, symbol="BTCUSDT", timeframe="1m")
    assert discovery.requested_timeframe_available is False
    assert discovery.finest_available_interval == "Min5"


@pytest.mark.unit
def test_successful_download_with_fixture_mapping(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    csv_bytes = (FIXTURE_DIR / "mexc_btcusdt_min1_sample.csv").read_bytes()
    monthly_listing = {
        "fileName": "BTC_USDT-Min1-2026-06-01.csv",
        "maskedUrl": "https://example.test/BTC_USDT-Min1-2026-06-01.csv",
        "fileSize": len(csv_bytes),
        "lastModified": "2026-07-01T06:02:02Z",
    }
    mapping = {
        probe.build_file_svc_url(
            probe.DEFAULT_FILE_SVC_BASE,
            "SPOT2/kline/2fb942154ef44a4ab2ef98c8afb6a4a7/monthly/",
        ): json.dumps({"data": ["Min1/", "Min5/"]}).encode("utf-8"),
        probe.build_file_svc_url(
            probe.DEFAULT_FILE_SVC_BASE,
            "SPOT2/kline/2fb942154ef44a4ab2ef98c8afb6a4a7/daily/",
        ): json.dumps({"data": ["Min1/", "Min5/"]}).encode("utf-8"),
        probe.build_file_svc_url(
            probe.DEFAULT_FILE_SVC_BASE,
            "SPOT2/kline/2fb942154ef44a4ab2ef98c8afb6a4a7/monthly/Min1/",
        ): json.dumps({"data": [monthly_listing]}).encode("utf-8"),
        "https://example.test/BTC_USDT-Min1-2026-06-01.csv": csv_bytes,
        "https://api.mexc.com/api/v3/klines?symbol=BTCUSDT&interval=1m&startTime=1780272000000&limit=5": json.dumps(
            [
                [
                    1780272000000,
                    rows_open := "104500.1200000000000000000000000000",
                    "104520.4500000000000000000000000000",
                    "104490.0000000000000000000000000000",
                    "104510.3300000000000000000000000000",
                    "1.25000000",
                    1780272060000,
                    "130637.910000000000000000",
                ]
            ]
        ).encode("utf-8"),
    }
    fetcher = probe.HttpFetcher(opener=_fake_opener(mapping))
    monkeypatch.setattr(probe, "KNOWN_SYMBOL_IDS", {"BTCUSDT": "2fb942154ef44a4ab2ef98c8afb6a4a7"})
    result = probe.run_probe(
        symbol="BTCUSDT",
        timeframe="1m",
        month="2026-06",
        repo_root=tmp_path,
        fetcher=fetcher,
    )
    assert result["probe_verdict"] == "MEXC_HISTORICAL_SOURCE_PROBE_PARTIAL"
    assert "download" in result
    manifest = json.loads(
        (
            tmp_path
            / "artifacts/market_data/normalized/mexc/spot/BTCUSDT/1m/2026-06/provenance_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert "cookie" not in json.dumps(manifest).lower()
    assert manifest["sha256"]


@pytest.mark.unit
def test_run_probe_blocked_when_min1_missing() -> None:
    listing = {
        probe.build_file_svc_url(
            probe.DEFAULT_FILE_SVC_BASE,
            "SPOT2/kline/2fb942154ef44a4ab2ef98c8afb6a4a7/monthly/",
        ): json.dumps({"data": ["Min5/", "Day1/"]}).encode("utf-8"),
        probe.build_file_svc_url(
            probe.DEFAULT_FILE_SVC_BASE,
            "SPOT2/kline/2fb942154ef44a4ab2ef98c8afb6a4a7/daily/",
        ): json.dumps({"data": ["Min5/", "Day1/"]}).encode("utf-8"),
    }
    fetcher = probe.HttpFetcher(opener=_fake_opener(listing))
    result = probe.run_probe(
        symbol="BTCUSDT",
        timeframe="1m",
        month="2026-06",
        fetcher=fetcher,
    )
    assert result["probe_verdict"] == "MEXC_HISTORICAL_SOURCE_PROBE_BLOCKED"
    assert "Min1" in result["blocked_reason"]
