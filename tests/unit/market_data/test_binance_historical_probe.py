from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path
from urllib.error import HTTPError

import pytest

from tools.market_data import assign_regime_offline, binance_historical_probe as probe
from tools.market_data import historical_common as common

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


def _fake_opener(mapping: dict[str, bytes], content_types: dict[str, str] | None = None):
    content_types = content_types or {}

    def _open(request, timeout=120):  # noqa: ARG001
        url = request.full_url
        if url not in mapping:
            raise HTTPError(url, 404, "not found", None, io.BytesIO(b""))
        headers = {"Content-Type": content_types.get(url, "application/octet-stream")}
        return _FakeResponse(mapping[url], headers)

    return _open


def _build_zip(csv_bytes: bytes, member_name: str = "BTCUSDT-1m-2026-06.csv") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member_name, csv_bytes)
    return buffer.getvalue()


@pytest.mark.unit
def test_detect_timestamp_unit_microseconds() -> None:
    assert common.detect_timestamp_unit(1780272000000000) == "microseconds"


@pytest.mark.unit
def test_normalize_timestamp_units() -> None:
    assert common.normalize_timestamp_to_ms(1780272000) == 1780272000000
    assert common.normalize_timestamp_to_ms(1780272000000) == 1780272000000
    assert common.normalize_timestamp_to_ms(1780272000000000) == 1780272000000


@pytest.mark.unit
def test_unplausible_timestamp_fail_closed() -> None:
    with pytest.raises(common.HistoricalProbeError, match="Unplausible"):
        common.detect_timestamp_unit(10_000_000_000_000_000_000)


@pytest.mark.unit
def test_parse_official_checksum() -> None:
    text = f"{'a' * 64}  BTCUSDT-1m-2026-06.zip\n"
    digest = common.parse_official_checksum(
        text,
        expected_filename="BTCUSDT-1m-2026-06.zip",
    )
    assert digest == "a" * 64


@pytest.mark.unit
def test_parse_binance_headerless_csv_fixture() -> None:
    csv_bytes = (FIXTURE_DIR / "binance_btcusdt_1m_sample.csv").read_bytes()
    source_hash = hashlib.sha256(csv_bytes).hexdigest()
    candles, schema = probe.parse_binance_kline_csv(
        csv_bytes,
        symbol="BTCUSDT",
        timeframe="1m",
        source_file_sha256=source_hash,
    )
    assert len(candles) == 3
    assert schema["header_present"] is False
    assert schema["open_time_unit"] == "microseconds"
    assert candles[0].ts_ms == 1780272000000
    assert candles[0].trade_count == 2892
    assert candles[0].venue == "binance"


@pytest.mark.unit
def test_zip_traversal_blocked(tmp_path: Path) -> None:
    zip_path = tmp_path / "bad.zip"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../evil.csv", "x")
    zip_path.write_bytes(buffer.getvalue())
    with pytest.raises(common.HistoricalProbeError, match="Unsafe archive"):
        common.inspect_archive(zip_path)


@pytest.mark.unit
def test_html_response_rejected(tmp_path: Path) -> None:
    fetcher = common.HttpFetcher(opener=_fake_opener({}))
    destination = tmp_path / "bad.zip"
    html = (FIXTURE_DIR / "binance_error_response.html").read_bytes()
    fetcher._opener = _fake_opener(  # type: ignore[method-assign]
        {"https://example.test/bad.zip": html},
        {"https://example.test/bad.zip": "text/html"},
    )
    with pytest.raises(common.HistoricalProbeError, match="Refusing"):
        fetcher.download("https://example.test/bad.zip", destination)


@pytest.mark.unit
def test_partial_download_not_finalized(tmp_path: Path) -> None:
    def _boom(request, timeout=120):  # noqa: ARG001
        raise OSError("connection reset")

    fetcher = common.HttpFetcher(opener=_boom)
    destination = tmp_path / "sample.zip"
    with pytest.raises(common.HistoricalProbeError, match="Network error"):
        fetcher.download("https://example.test/sample.zip", destination)
    assert not destination.exists()
    assert not destination.with_suffix(".zip.partial").exists()


@pytest.mark.unit
def test_checksum_fail_blocks_verified_mark(tmp_path: Path) -> None:
    csv_bytes = (FIXTURE_DIR / "binance_btcusdt_1m_sample.csv").read_bytes()
    zip_bytes = _build_zip(csv_bytes)
    wrong = "b" * 64
    fetcher = common.HttpFetcher(
        opener=_fake_opener(
            {
                "https://example.test/archive.zip": zip_bytes,
                "https://example.test/archive.zip.CHECKSUM": (
                    f"{wrong}  BTCUSDT-1m-2026-06.zip\n".encode()
                ),
            }
        )
    )
    destination = tmp_path / "BTCUSDT-1m-2026-06.zip"
    with pytest.raises(common.HistoricalProbeError, match="hash mismatch"):
        fetcher.download(
            "https://example.test/archive.zip",
            destination,
            expected_sha256=wrong,
        )


@pytest.mark.unit
def test_successful_download_with_checksum(tmp_path: Path) -> None:
    csv_bytes = (FIXTURE_DIR / "binance_btcusdt_1m_sample.csv").read_bytes()
    zip_bytes = _build_zip(csv_bytes)
    digest = hashlib.sha256(zip_bytes).hexdigest()
    url = "https://example.test/BTCUSDT-1m-2026-06.zip"
    fetcher = common.HttpFetcher(opener=_fake_opener({url: zip_bytes}))
    destination = tmp_path / "BTCUSDT-1m-2026-06.zip"
    first = fetcher.download(url, destination, expected_sha256=digest)
    second = fetcher.download(url, destination, expected_sha256=digest)
    assert first.sha256 == second.sha256 == digest


@pytest.mark.unit
def test_hash_conflict_on_existing_file(tmp_path: Path) -> None:
    csv_bytes = (FIXTURE_DIR / "binance_btcusdt_1m_sample.csv").read_bytes()
    zip_bytes = _build_zip(csv_bytes)
    url = "https://example.test/BTCUSDT-1m-2026-06.zip"
    destination = tmp_path / "BTCUSDT-1m-2026-06.zip"
    destination.write_bytes(zip_bytes)
    fetcher = common.HttpFetcher(opener=_fake_opener({url: zip_bytes}))
    with pytest.raises(common.HistoricalProbeError, match="different hash"):
        fetcher.download(url, destination, expected_sha256="c" * 64)


@pytest.mark.unit
def test_ohlc_and_gap_detection() -> None:
    candles = [
        common.NormalizedCandle(
            ts_ms=1780272000000 + i * 60_000,
            open="1",
            high="2",
            low="1",
            close="1.5",
            volume="10",
            quote_volume="20",
            trade_count=5,
            symbol="BTCUSDT",
            venue="binance",
            timeframe="1m",
            source_type="binance_public_data",
            source_file_sha256="abc",
        )
        for i in range(3)
    ]
    anomalies = common.validate_ohlc(candles)
    assert anomalies == []
    gaps = common.detect_gaps(
        candles,
        start_ts_ms=1780272000000,
        end_ts_ms=1780272000000 + 2 * 60_000,
        step_ms=60_000,
    )
    assert gaps["missing_minutes"] == 0


@pytest.mark.unit
def test_dataset_spec_evidence_classification() -> None:
    spec = probe.build_dataset_spec(
        symbol="BTCUSDT",
        timeframe="1m",
        start_ts_ms=1,
        end_ts_ms=2,
        file_path=Path("artifacts/x/candles.jsonl"),
        source_hash="a" * 64,
        quality_verdict="STRICT_COMPLETE",
        regime_enriched=False,
        normalized_hash_value="b" * 64,
    )
    assert spec["venue"] == "binance"
    assert spec["venue_match"] is False
    assert spec["evidence_subclass"] == "historical_cross_venue_research"
    assert spec["ranking_ready"] is False
    assert "mexc_same_venue" in spec["not_evidence_class"]


@pytest.mark.unit
def test_regime_assignment_deterministic() -> None:
    rows = [
        {
            "ts_ms": 1780272000000 + i * 60_000,
            "open": "100",
            "high": "101",
            "low": "99",
            "close": "100.5",
            "volume": "1",
            "symbol": "BTCUSDT",
        }
        for i in range(300)
    ]
    first = assign_regime_offline.assign_regime_ids(rows)
    second = assign_regime_offline.assign_regime_ids(rows)
    assert first == second
    assert all("regime_id" in row for row in first)


@pytest.mark.unit
def test_arvp_dataset_provider_loads_fixture_jsonl(tmp_path: Path) -> None:
    csv_bytes = (FIXTURE_DIR / "binance_btcusdt_1m_sample.csv").read_bytes()
    source_hash = hashlib.sha256(csv_bytes).hexdigest()
    candles, _ = probe.parse_binance_kline_csv(
        csv_bytes,
        symbol="BTCUSDT",
        timeframe="1m",
        source_file_sha256=source_hash,
    )
    jsonl_path = tmp_path / "candles.jsonl"
    common.write_jsonl(jsonl_path, [c.to_dict() for c in candles])
    result = common.arvp_load_smoke(
        jsonl_path,
        symbol="BTCUSDT",
        start_ts_ms=candles[0].ts_ms,
        end_ts_ms=candles[-1].ts_ms,
    )
    assert result["status"] == "PASS"
    assert result["candles_loaded"] == 3


@pytest.mark.unit
def test_probe_verdict_pass_requires_replay() -> None:
    discovery = probe.SourceDiscovery(
        portal_url="x",
        repository_url="x",
        data_vision_base="x",
        rest_klines_endpoint="x",
        symbol="BTCUSDT",
        product="spot",
        interval="1m",
        monthly_archive_available=True,
        daily_archive_available=False,
        checksum_files_available=True,
        account_required=False,
        license_reference="x",
        proven_fields={},
        blocked_fields={},
    )
    verdict = probe.probe_verdict(
        discovery=discovery,
        checksum_verified=True,
        quality_verdict="STRICT_COMPLETE",
        arvp_status="PASS",
        regime_status="PASS",
        replay_results=[{"exit_code": 0}],
    )
    assert verdict == "BINANCE_HISTORICAL_SOURCE_PROBE_PASS"
