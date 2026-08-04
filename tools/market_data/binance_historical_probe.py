"""Binance official public-data historical source probe (#3990).

Uses Binance Data Vision monthly kline archives with official .CHECKSUM files.
Cross-venue research evidence only — not MEXC same-venue execution evidence.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
import sys
import urllib.parse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.market_data.assign_regime_offline import (
    WARMUP_CANDLES,
    assign_regime_ids,
    regime_distribution,
)
from tools.market_data.historical_common import (
    ONE_MINUTE_MS,
    DownloadResult,
    HistoricalProbeError,
    HttpFetcher,
    NormalizedCandle,
    arvp_load_smoke,
    assert_dq_content_binding,
    build_quality_report,
    detect_timestamp_unit,
    decimal_str,
    extract_zip_csv,
    inspect_archive,
    month_bounds,
    normalize_timestamp_to_ms,
    normalized_hash,
    parse_official_checksum,
    parse_year_month,
    rest_crosscheck,
    sha256_file,
    utc_now_iso,
    write_json,
    write_jsonl,
)

DEFAULT_DATA_VISION_BASE = "https://data.binance.vision"
DEFAULT_REST_BASE = "https://api.binance.com"
BINANCE_KLINE_COLUMNS = (
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "number_of_trades",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
    "ignore",
)

PROBE_VERDICTS = frozenset(
    {
        "BINANCE_HISTORICAL_SOURCE_PROBE_PASS",
        "BINANCE_HISTORICAL_SOURCE_PROBE_PARTIAL",
        "BINANCE_HISTORICAL_SOURCE_PROBE_BLOCKED",
    }
)

STRATEGY_ADAPTER_MAP = {
    "donchian_breakout_v1": "donchian_breakout_runner_v1",
    "breakout_trend_filter_v1": "breakout_trend_filter_runner_v1",
    "primary_breakout_v1": "primary_breakout_runner_v1",
}


@dataclass(frozen=True, slots=True)
class SourceDiscovery:
    portal_url: str
    repository_url: str
    data_vision_base: str
    rest_klines_endpoint: str
    symbol: str
    product: str
    interval: str
    monthly_archive_available: bool
    daily_archive_available: bool
    checksum_files_available: bool
    account_required: bool
    license_reference: str
    proven_fields: dict[str, str]
    blocked_fields: dict[str, str]


def monthly_archive_filename(symbol: str, interval: str, year: int, month: int) -> str:
    return f"{symbol}-{interval}-{year:04d}-{month:02d}.zip"


def monthly_archive_url(
    base: str,
    *,
    symbol: str,
    interval: str,
    year: int,
    month: int,
) -> str:
    filename = monthly_archive_filename(symbol, interval, year, month)
    return f"{base.rstrip('/')}/data/spot/monthly/klines/{symbol}/{interval}/{filename}"


def monthly_checksum_url(
    base: str,
    *,
    symbol: str,
    interval: str,
    year: int,
    month: int,
) -> str:
    return (
        monthly_archive_url(
            base, symbol=symbol, interval=interval, year=year, month=month
        )
        + ".CHECKSUM"
    )


def discover_source(
    fetcher: HttpFetcher,
    *,
    symbol: str,
    interval: str,
    year: int,
    month: int,
    data_vision_base: str = DEFAULT_DATA_VISION_BASE,
) -> SourceDiscovery:
    archive_url = monthly_archive_url(
        data_vision_base,
        symbol=symbol,
        interval=interval,
        year=year,
        month=month,
    )
    checksum_url = monthly_checksum_url(
        data_vision_base,
        symbol=symbol,
        interval=interval,
        year=year,
        month=month,
    )
    monthly_available = True
    checksum_available = True
    blocked: dict[str, str] = {}
    try:
        fetcher._fetch(archive_url)
    except HistoricalProbeError as exc:
        monthly_available = False
        blocked["monthly_archive"] = str(exc)
    try:
        fetcher.fetch_text(checksum_url)
    except HistoricalProbeError as exc:
        checksum_available = False
        blocked["checksum_file"] = str(exc)

    return SourceDiscovery(
        portal_url="https://www.binance.com/en/landing/data",
        repository_url="https://github.com/binance/binance-public-data",
        data_vision_base=data_vision_base,
        rest_klines_endpoint=f"{DEFAULT_REST_BASE}/api/v3/klines",
        symbol=symbol,
        product="spot",
        interval=interval,
        monthly_archive_available=monthly_available,
        daily_archive_available=False,
        checksum_files_available=checksum_available,
        account_required=False,
        license_reference="https://github.com/binance/binance-public-data",
        proven_fields={
            "official_data_vision": data_vision_base,
            "official_checksum": checksum_url if checksum_available else "blocked",
            "spot_support": "proven",
            "btcusdt_support": "proven" if symbol == "BTCUSDT" else "not_proven",
            "1m_interval": "proven" if interval == "1m" else "not_proven",
            "no_account_required": "proven",
        },
        blocked_fields=blocked,
    )


def parse_binance_kline_csv(
    csv_bytes: bytes,
    *,
    symbol: str,
    timeframe: str,
    source_file_sha256: str,
) -> tuple[list[NormalizedCandle], dict[str, Any]]:
    text = csv_bytes.decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise HistoricalProbeError("Binance CSV archive is empty")

    has_header = rows[0][0].strip().lower() in {"open_time", "opentime", "timestamp"}
    data_rows = rows[1:] if has_header else rows
    if not data_rows:
        raise HistoricalProbeError("Binance CSV archive has no data rows")

    open_unit = detect_timestamp_unit(data_rows[0][0])
    close_unit = (
        detect_timestamp_unit(data_rows[0][6]) if len(data_rows[0]) > 6 else open_unit
    )

    candles: list[NormalizedCandle] = []
    for row in data_rows:
        if len(row) < 8:
            raise HistoricalProbeError(f"Unexpected Binance row width: {len(row)}")
        ts_ms = normalize_timestamp_to_ms(row[0], unit=open_unit)
        close_ts_ms = normalize_timestamp_to_ms(row[6], unit=close_unit)
        trade_count_raw = row[8] if len(row) > 8 else ""
        candles.append(
            NormalizedCandle(
                ts_ms=ts_ms,
                open=decimal_str(row[1]),
                high=decimal_str(row[2]),
                low=decimal_str(row[3]),
                close=decimal_str(row[4]),
                volume=decimal_str(row[5]),
                quote_volume=decimal_str(row[7]) if row[7] else None,
                trade_count=int(trade_count_raw) if trade_count_raw else None,
                symbol=symbol,
                venue="binance",
                timeframe=timeframe,
                source_type="binance_public_data",
                source_file_sha256=source_file_sha256,
                close_ts_ms=close_ts_ms,
                taker_buy_base_volume=(
                    decimal_str(row[9]) if len(row) > 9 and row[9] else None
                ),
                taker_buy_quote_volume=(
                    decimal_str(row[10]) if len(row) > 10 and row[10] else None
                ),
                extra_fields=tuple(BINANCE_KLINE_COLUMNS),
            )
        )

    schema = {
        "columns": list(BINANCE_KLINE_COLUMNS),
        "header_present": has_header,
        "open_time_unit": open_unit,
        "close_time_unit": close_unit,
        "row_count": len(candles),
    }
    return candles, schema


def build_dataset_spec(
    *,
    symbol: str,
    timeframe: str,
    start_ts_ms: int,
    end_ts_ms: int,
    file_path: Path,
    source_hash: str,
    quality_verdict: str,
    regime_enriched: bool,
    normalized_hash_value: str,
) -> dict[str, Any]:
    return {
        "schema_version": "dataset_spec.v2",
        "symbol": symbol,
        "venue": "binance",
        "venue_match": False,
        "target_validation_venue": "mexc",
        "source": "file",
        "source_label": "binance_public_data",
        "source_type": "binance_public_data",
        "file_path": str(file_path).replace("\\", "/"),
        "start_ts_ms": start_ts_ms,
        "end_ts_ms": end_ts_ms,
        "timeframe": timeframe,
        "source_file_sha256": source_hash,
        "normalized_hash_sha256": normalized_hash_value,
        "data_quality_verdict": quality_verdict,
        "regime_enriched": regime_enriched,
        "replay_compatibility": {
            "provider": "FileBackedDatasetProvider",
            "required_fields_present": True,
            "regime_id_status": "enriched" if regime_enriched else "not_enriched",
        },
        "evidence_class": "controlled_lab_evidence",
        "evidence_subclass": "historical_cross_venue_research",
        "not_evidence_class": [
            "mexc_same_venue",
            "natural_paper_evidence",
            "live_evidence",
            "promotion_ready",
        ],
        "ranking_ready": False,
        "lr_status": "NO-GO",
    }


def build_provenance_manifest(
    *,
    download: DownloadResult,
    checksum_official: str,
    checksum_verified: bool,
    schema: dict[str, Any],
    source_sha: str,
    parser_version: str,
    archive_path: str,
    download_path_type: str,
) -> dict[str, Any]:
    return {
        "issue": "#3990",
        "source": "binance_public_data",
        "portal_url": "https://www.binance.com/en/landing/data",
        "repository_url": "https://github.com/binance/binance-public-data",
        "download_path_type": download_path_type,
        "archive_path": archive_path,
        "original_filename": download.original_filename,
        "source_url": download.source_url,
        "downloaded_at_utc": download.downloaded_at_utc,
        "content_type": download.content_type,
        "content_length": download.content_length,
        "local_sha256": download.sha256,
        "official_checksum_sha256": checksum_official,
        "checksum_verified": checksum_verified,
        "archive_format": "zip",
        "schema": schema,
        "repo_source_sha": source_sha,
        "parser_version": parser_version,
        "venue": "binance",
        "evidence_class": "historical_cross_venue_research",
        "target_validation_venue": "mexc",
        "raw_data_git_policy": "DO_NOT_COMMIT",
        "normalized_data_git_policy": "DO_NOT_COMMIT",
        "metadata_and_hashes_git_policy": "ALLOWED",
        "redistribution": "LEGAL_REVIEW_REQUIRED",
    }


def run_replay_probe(
    *,
    candles_path: Path,
    strategy_id: str,
    output_dir: Path,
    scenario_group_id: str,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    adapter_id = STRATEGY_ADAPTER_MAP[strategy_id]
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "services.validation.strategy_replay_runner",
        "--input-candles",
        str(candles_path),
        "--strategy-id",
        strategy_id,
        "--adapter-id",
        adapter_id,
        "--symbol",
        "BTCUSDT",
        "--output-dir",
        str(output_dir),
        "--scenario-group",
        "baseline,pessimistic_execution,feed_gap",
        "--scenario-group-id",
        scenario_group_id,
    ]
    completed = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    manifest_path = output_dir / scenario_group_id / "scenario_group_manifest.json"
    manifest = None
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "strategy_id": strategy_id,
        "adapter_id": adapter_id,
        "scenario_group_id": scenario_group_id,
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
        "manifest_path": str(manifest_path).replace("\\", "/"),
        "manifest": manifest,
        "ranking_ready": False,
        "evidence_class": "historical_cross_venue_research",
        "venue": "binance",
        "target_validation_venue": "mexc",
    }


def probe_verdict(
    *,
    discovery: SourceDiscovery,
    checksum_verified: bool,
    quality_verdict: str | None,
    arvp_status: str | None,
    regime_status: str | None,
    replay_results: Sequence[dict[str, Any]],
) -> str:
    if not discovery.monthly_archive_available or not checksum_verified:
        return "BINANCE_HISTORICAL_SOURCE_PROBE_BLOCKED"
    if quality_verdict not in {"STRICT_COMPLETE", "COMPLETE_WITH_DOCUMENTED_ANOMALIES"}:
        if quality_verdict in {"SOURCE_INVALID", "SOURCE_UNAVAILABLE"}:
            return "BINANCE_HISTORICAL_SOURCE_PROBE_BLOCKED"
        return "BINANCE_HISTORICAL_SOURCE_PROBE_PARTIAL"
    if arvp_status != "PASS" or regime_status != "PASS":
        return "BINANCE_HISTORICAL_SOURCE_PROBE_PARTIAL"
    if not replay_results:
        return "BINANCE_HISTORICAL_SOURCE_PROBE_PARTIAL"
    if all(item.get("exit_code") == 0 for item in replay_results):
        return "BINANCE_HISTORICAL_SOURCE_PROBE_PASS"
    return "BINANCE_HISTORICAL_SOURCE_PROBE_PARTIAL"


def get_repo_source_sha(repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return "unknown"


def run_probe(
    *,
    symbol: str = "BTCUSDT",
    interval: str = "1m",
    month: str = "2026-06",
    repo_root: Path = REPO_ROOT,
    fetcher: HttpFetcher | None = None,
    discover_only: bool = False,
    skip_replay: bool = False,
) -> dict[str, Any]:
    fetcher = fetcher or HttpFetcher()
    year, month_num = parse_year_month(month)
    start_ts_ms, end_ts_ms, expected_minutes = month_bounds(year, month_num)
    discovery = discover_source(
        fetcher,
        symbol=symbol,
        interval=interval,
        year=year,
        month=month_num,
    )

    result: dict[str, Any] = {
        "issue": "#3990",
        "symbol": symbol,
        "interval": interval,
        "requested_month": month,
        "start_ts_ms": start_ts_ms,
        "end_ts_ms": end_ts_ms,
        "expected_minutes": expected_minutes,
        "discovery": asdict(discovery),
        "probe_verdict": "BINANCE_HISTORICAL_SOURCE_PROBE_BLOCKED",
        "evidence_class": "historical_cross_venue_research",
        "venue": "binance",
        "target_validation_venue": "mexc",
    }

    if discover_only:
        if discovery.monthly_archive_available:
            result["probe_verdict"] = "BINANCE_HISTORICAL_SOURCE_PROBE_PARTIAL"
        return result

    if not discovery.monthly_archive_available:
        result["blocked_reason"] = discovery.blocked_fields
        return result

    archive_name = monthly_archive_filename(symbol, interval, year, month_num)
    archive_url = monthly_archive_url(
        discovery.data_vision_base,
        symbol=symbol,
        interval=interval,
        year=year,
        month=month_num,
    )
    checksum_url = monthly_checksum_url(
        discovery.data_vision_base,
        symbol=symbol,
        interval=interval,
        year=year,
        month=month_num,
    )

    raw_dir = (
        repo_root
        / "artifacts"
        / "market_data"
        / "raw"
        / "binance"
        / "spot"
        / symbol
        / interval
        / month
    )
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_zip = raw_dir / archive_name
    checksum_path = raw_dir / f"{archive_name}.CHECKSUM"

    checksum_text = fetcher.fetch_text(checksum_url)
    official_checksum = parse_official_checksum(
        checksum_text, expected_filename=archive_name
    )
    if not checksum_path.exists():
        checksum_path.write_text(checksum_text, encoding="utf-8")

    download = fetcher.download(archive_url, raw_zip, expected_sha256=official_checksum)
    checksum_verified = download.sha256 == official_checksum

    _, csv_bytes = extract_zip_csv(raw_zip)
    candles, schema = parse_binance_kline_csv(
        csv_bytes,
        symbol=symbol,
        timeframe=interval,
        source_file_sha256=download.sha256,
    )
    second_parse_hash = normalized_hash(
        parse_binance_kline_csv(
            csv_bytes,
            symbol=symbol,
            timeframe=interval,
            source_file_sha256=download.sha256,
        )[0]
    )
    norm_hash = normalized_hash(candles)
    quality = build_quality_report(
        candles,
        start_ts_ms=start_ts_ms,
        end_ts_ms=end_ts_ms,
        step_ms=ONE_MINUTE_MS,
        source_hash=norm_hash,
        second_parse_hash=second_parse_hash,
    )
    assert_dq_content_binding(
        quality, content_fingerprint=quality["content_fingerprint"]
    )

    normalized_dir = (
        repo_root
        / "artifacts"
        / "market_data"
        / "normalized"
        / "binance"
        / "spot"
        / symbol
        / interval
        / month
    )
    jsonl_path = normalized_dir / "candles.jsonl"
    write_jsonl(jsonl_path, [candle.to_dict() for candle in candles])

    source_sha = get_repo_source_sha(repo_root)
    provenance = build_provenance_manifest(
        download=download,
        checksum_official=official_checksum,
        checksum_verified=checksum_verified,
        schema=schema,
        source_sha=source_sha,
        parser_version="tools.market_data.binance_historical_probe/1.0",
        archive_path=archive_url,
        download_path_type="monthly",
    )
    write_json(normalized_dir / "provenance_manifest.json", provenance)
    write_json(normalized_dir / "quality_report.json", quality)
    write_json(normalized_dir / "gap_report.json", quality["gaps"])
    write_json(
        normalized_dir / "dataset_spec.json",
        build_dataset_spec(
            symbol=symbol,
            timeframe=interval,
            start_ts_ms=start_ts_ms,
            end_ts_ms=end_ts_ms,
            file_path=jsonl_path,
            source_hash=download.sha256,
            quality_verdict=quality["verdict"],
            regime_enriched=False,
            normalized_hash_value=norm_hash,
        ),
    )

    mid_ts = candles[len(candles) // 2].ts_ms if candles else start_ts_ms
    rest = rest_crosscheck(
        fetcher,
        symbol=symbol,
        sample_points=(start_ts_ms, mid_ts, end_ts_ms),
        candles=candles,
        rest_base=DEFAULT_REST_BASE,
        interval=interval,
    )
    write_json(normalized_dir / "rest_crosscheck.json", rest)

    arvp = arvp_load_smoke(
        jsonl_path,
        symbol=symbol,
        start_ts_ms=start_ts_ms,
        end_ts_ms=end_ts_ms,
    )

    enriched_dir = (
        repo_root
        / "artifacts"
        / "market_data"
        / "enriched"
        / "binance"
        / "spot"
        / symbol
        / interval
        / month
    )
    enriched_jsonl = enriched_dir / "candles.jsonl"
    raw_rows = [candle.to_dict() for candle in candles]
    enriched_rows = assign_regime_ids(raw_rows)
    write_jsonl(enriched_jsonl, enriched_rows)
    regime_dist = regime_distribution(enriched_rows)
    regime_manifest = {
        "schema_version": "regime_assignment_manifest.v1",
        "issue": "#3990",
        "method": "offline_heuristic_adx_atr",
        "warmup_candles": WARMUP_CANDLES,
        "deterministic": True,
        "venue": "binance",
        "evidence_class": "historical_cross_venue_research",
        "regime_distribution": regime_dist,
        "input_rows": len(raw_rows),
        "output_rows": len(enriched_rows),
    }
    write_json(enriched_dir / "regime_assignment_manifest.json", regime_manifest)
    write_json(
        enriched_dir / "dataset_spec.json",
        build_dataset_spec(
            symbol=symbol,
            timeframe=interval,
            start_ts_ms=start_ts_ms,
            end_ts_ms=end_ts_ms,
            file_path=enriched_jsonl,
            source_hash=download.sha256,
            quality_verdict=quality["verdict"],
            regime_enriched=True,
            normalized_hash_value=normalized_hash(
                [
                    NormalizedCandle(
                        ts_ms=row["ts_ms"],
                        open=str(row["open"]),
                        high=str(row["high"]),
                        low=str(row["low"]),
                        close=str(row["close"]),
                        volume=str(row["volume"]),
                        quote_volume=row.get("quote_volume"),
                        trade_count=row.get("trade_count"),
                        symbol=symbol,
                        venue="binance",
                        timeframe=interval,
                        source_type="binance_public_data",
                        source_file_sha256=download.sha256,
                    )
                    for row in enriched_rows
                ]
            ),
        ),
    )
    regime_status = "PASS" if len(enriched_rows) == len(raw_rows) else "FAIL"

    replay_results: list[dict[str, Any]] = []
    if not skip_replay and arvp.get("status") == "PASS":
        replay_root = (
            repo_root / "artifacts" / "replay_reports" / "binance_probe_3990" / month
        )
        for strategy_id in ("donchian_breakout_v1", "breakout_trend_filter_v1"):
            replay_results.append(
                run_replay_probe(
                    candles_path=jsonl_path,
                    strategy_id=strategy_id,
                    output_dir=replay_root / strategy_id,
                    scenario_group_id=f"arvp_binance_probe_3990_{strategy_id}_{month.replace('-', '')}",
                    repo_root=repo_root,
                )
            )

    verdict = probe_verdict(
        discovery=discovery,
        checksum_verified=checksum_verified,
        quality_verdict=quality["verdict"],
        arvp_status=arvp.get("status"),
        regime_status=regime_status,
        replay_results=replay_results,
    )

    download_record = asdict(download)
    download_record["local_path"] = str(download.local_path)

    result.update(
        {
            "download": download_record,
            "official_checksum": official_checksum,
            "checksum_verified": checksum_verified,
            "schema": schema,
            "normalized_hash": norm_hash,
            "actual_candles": len(candles),
            "quality": quality,
            "rest_crosscheck": rest,
            "arvp_load": arvp,
            "regime_distribution": regime_dist,
            "regime_status": regime_status,
            "replay_results": replay_results,
            "probe_verdict": verdict,
            "paths": {
                "raw_zip": str(raw_zip),
                "normalized_jsonl": str(jsonl_path),
                "enriched_jsonl": str(enriched_jsonl),
            },
        }
    )
    write_json(normalized_dir / "probe_result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Binance historical source probe (#3990)"
    )
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="1m")
    parser.add_argument("--month", default="2026-06")
    parser.add_argument("--discover-only", action="store_true")
    parser.add_argument("--skip-replay", action="store_true")
    args = parser.parse_args()

    try:
        result = run_probe(
            symbol=args.symbol.upper(),
            interval=args.interval,
            month=args.month,
            discover_only=args.discover_only,
            skip_replay=args.skip_replay,
        )
    except HistoricalProbeError as exc:
        print(f"PROBE_ERROR: {exc}", file=sys.stderr)
        return 3

    print(json.dumps(result, indent=2, sort_keys=True))
    if result["probe_verdict"] == "BINANCE_HISTORICAL_SOURCE_PROBE_PASS":
        return 0
    if result["probe_verdict"] == "BINANCE_HISTORICAL_SOURCE_PROBE_PARTIAL":
        return 2
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
