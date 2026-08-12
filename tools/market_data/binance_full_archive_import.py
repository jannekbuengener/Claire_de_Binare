"""Full Binance BTCUSDT 1m monthly archive import (#3990).

Cross-venue research corpus only — not MEXC same-venue execution evidence.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import gc
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.utils.clock import utcnow
from tools.market_data import binance_historical_probe as probe
from tools.market_data.assign_regime_offline import (
    RegimeCarryState,
    analyze_regime_plausibility,
    assign_regime_ids_with_state,
    regime_distribution,
)
from tools.market_data.historical_common import (
    ONE_MINUTE_MS,
    HistoricalProbeError,
    HttpFetcher,
    assert_dq_content_binding,
    content_fingerprint_for_candle_rows,
    content_fingerprint_for_normalized,
    enforce_dq_content_binding,
    load_dq_report_sidecar,
    month_bounds,
    parse_year_month,
    sha256_file,
    utc_now_iso,
    write_json,
    write_jsonl,
)
from tools.market_data.market_data_storage_guard import resolve_market_data_path

MANIFEST_SCHEMA_VERSION = "binance_full_import.v1"
S3_LISTING_URL = (
    "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
    "?prefix=data/spot/monthly/klines/BTCUSDT/1m/"
)


def _market_data_root(repo_root: Path) -> Path:
    """Resolve the current import target, including explicit bulk opt-in."""
    return resolve_market_data_path(repo_root)


DEFAULT_DATA_VISION_BASE = probe.DEFAULT_DATA_VISION_BASE
IMPORT_FINAL_STATUSES = frozenset(
    {
        "FULL_IMPORT_AND_CAMPAIGN_PASS",
        "FULL_IMPORT_PASS_CAMPAIGN_PARTIAL",
        "FULL_IMPORT_PARTIAL_REGIME_BLOCKED",
        "FULL_IMPORT_BLOCKED",
        "CAMPAIGN_TECHNICALLY_BLOCKED",
    }
)


@dataclass
class MonthImportRecord:
    month: str
    download_status: str = "pending"
    checksum_status: str = "pending"
    normalization_status: str = "pending"
    regime_status: str = "pending"
    quality_verdict: str = "SOURCE_UNAVAILABLE"
    local_raw_path: str | None = None
    local_normalized_path: str | None = None
    local_enriched_path: str | None = None
    raw_file_hash: str | None = None
    normalized_hash: str | None = None
    enriched_hash: str | None = None
    candle_count: int = 0
    gaps: dict[str, Any] = field(default_factory=dict)
    duplicates: dict[str, Any] = field(default_factory=dict)
    error_classification: str | None = None
    retry_count: int = 0


def list_available_months(
    fetcher: HttpFetcher | None = None,
    *,
    listing_url: str = S3_LISTING_URL,
) -> list[str]:
    """Return sorted YYYY-MM labels from official S3 listing."""
    fetcher = fetcher or HttpFetcher()
    text = fetcher.fetch_text(listing_url)
    months = sorted(set(re.findall(r"BTCUSDT-1m-(\d{4}-\d{2})\.zip", text)))
    if not months:
        raise HistoricalProbeError("No BTCUSDT 1m monthly archives found in listing")
    return months


def last_complete_month(
    *,
    now: datetime | None = None,
    available: Sequence[str] | None = None,
) -> str:
    """Last fully completed calendar month (excludes current incomplete month)."""
    now = now or utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    if now.month == 1:
        complete_end = f"{now.year - 1}-12"
    else:
        complete_end = f"{now.year}-{now.month - 1:02d}"
    if available:
        candidates = [m for m in available if m <= complete_end]
        if not candidates:
            raise HistoricalProbeError(
                f"No complete month <= {complete_end} in available listing"
            )
        return candidates[-1]
    return complete_end


def import_range(
    *,
    start_month: str | None = None,
    end_month: str | None = None,
    repo_root: Path = REPO_ROOT,
    fetcher: HttpFetcher | None = None,
    max_retries: int = 3,
    skip_download: bool = False,
    enrich_regime: bool = True,
    resume: bool = True,
    skip_storage_guard: bool = False,
) -> dict[str, Any]:
    """Import all months in range with manifest and coverage report."""
    if not skip_storage_guard:
        from tools.market_data.market_data_storage_guard import (
            enforce_market_data_storage,
        )

        enforce_market_data_storage(
            repo_root=repo_root,
            required_write_bytes=12_000_000_000,
        )
    started_at = utc_now_iso()
    fetcher = fetcher or HttpFetcher()
    available = list_available_months(fetcher)
    start = start_month or available[0]
    end = end_month or last_complete_month(available=available)
    months = [m for m in available if start <= m <= end]
    if not months:
        raise HistoricalProbeError(f"Empty import range {start}..{end}")

    source_sha = probe.get_repo_source_sha(repo_root)
    campaign_id = f"binance_btcusdt_1m_full_import_3990_{source_sha[:8]}"

    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "campaign_id": campaign_id,
        "source_sha": source_sha,
        "symbol": "BTCUSDT",
        "venue": "binance",
        "timeframe": "1m",
        "product": "spot",
        "requested_range": {"start_month": start, "end_month": end},
        "actual_range": {"start_month": months[0], "end_month": months[-1]},
        "months": [],
        "started_at_utc": started_at,
        "evidence_class": "historical_cross_venue_research",
        "not_evidence_class": ["mexc_same_venue", "live_evidence", "promotion_ready"],
        "lr_status": "NO-GO",
    }

    records: list[MonthImportRecord] = []
    regime_state: RegimeCarryState | None = None
    plausibility_sample: list[dict[str, Any]] = []
    max_plausibility_sample = 50_000

    for month in months:
        record = MonthImportRecord(month=month)
        if resume and _month_already_complete(repo_root, month):
            cached = _load_cached_month_record(repo_root, month)
            if cached:
                records.append(cached)
                regime_state = _load_regime_carry_state(repo_root, month)
                _append_plausibility_sample(
                    plausibility_sample,
                    repo_root,
                    month,
                    max_plausibility_sample,
                )
                continue
        for attempt in range(1, max_retries + 1):
            record.retry_count = attempt
            try:
                month_result = _import_single_month(
                    month=month,
                    repo_root=repo_root,
                    fetcher=fetcher,
                    skip_download=skip_download,
                )
                record.download_status = "complete"
                record.checksum_status = (
                    "verified" if month_result["checksum_verified"] else "failed"
                )
                if not month_result["checksum_verified"]:
                    record.quality_verdict = "CHECKSUM_FAILED"
                    record.normalization_status = "blocked"
                    records.append(record)
                    break
                record.normalization_status = "complete"
                record.quality_verdict = month_result["quality_verdict"]
                record.local_raw_path = month_result["raw_zip"]
                record.local_normalized_path = month_result["normalized_jsonl"]
                record.raw_file_hash = month_result["raw_hash"]
                record.normalized_hash = month_result["normalized_hash"]
                record.candle_count = month_result["candle_count"]
                record.gaps = month_result["gaps"]
                record.duplicates = month_result["duplicates"]

                if enrich_regime and record.quality_verdict == "STRICT_COMPLETE":
                    row_count, regime_state, enriched_hash = _enrich_month(
                        month=month,
                        repo_root=repo_root,
                        regime_state=regime_state,
                    )
                    record.regime_status = "complete"
                    enriched_path = _enriched_dir(repo_root, month) / "candles.jsonl"
                    record.local_enriched_path = str(enriched_path).replace("\\", "/")
                    record.enriched_hash = enriched_hash
                    _append_plausibility_sample(
                        plausibility_sample,
                        repo_root,
                        month,
                        max_plausibility_sample,
                    )
                elif enrich_regime:
                    record.regime_status = "skipped_quality"
                records.append(record)
                gc.collect()
                break
            except HistoricalProbeError as exc:
                record.error_classification = str(exc)
                if attempt >= max_retries:
                    record.download_status = "failed"
                    record.quality_verdict = "SOURCE_INVALID"
                    records.append(record)
                else:
                    time.sleep(min(2**attempt, 8))
            except OSError as exc:
                record.error_classification = f"disk_error:{exc}"
                record.download_status = "failed"
                records.append(record)
                break

    manifest["months"] = [asdict(r) for r in records]
    coverage = build_coverage_report(records, months)
    manifest["coverage"] = coverage
    manifest["finished_at_utc"] = utc_now_iso()

    regime_plausibility = None
    if plausibility_sample:
        regime_plausibility = analyze_regime_plausibility(plausibility_sample)
        manifest["regime_plausibility"] = regime_plausibility
        manifest["regime_distribution_sample"] = regime_distribution(
            plausibility_sample
        )

    complete = sum(1 for r in records if r.quality_verdict == "STRICT_COMPLETE")
    failed = sum(
        1
        for r in records
        if r.quality_verdict
        in {"SOURCE_INVALID", "CHECKSUM_FAILED", "SOURCE_UNAVAILABLE"}
    )
    if complete == len(months):
        manifest["import_status"] = "FULL_IMPORT_PASS"
    elif complete > 0:
        manifest["import_status"] = "FULL_IMPORT_PARTIAL"
    else:
        manifest["import_status"] = "FULL_IMPORT_BLOCKED"

    manifest["summary"] = {
        "total_months": len(months),
        "strict_complete": complete,
        "failed": failed,
        "partial": len(months) - complete - failed,
    }

    manifest_path = (
        _market_data_root(repo_root)
        / "manifests"
        / "binance_btcusdt_1m_full_import.json"
    )
    write_json(manifest_path, manifest)
    manifest["manifest_path"] = str(manifest_path).replace("\\", "/")
    return manifest


def _enriched_dir(repo_root: Path, month: str) -> Path:
    return (
        _market_data_root(repo_root)
        / "enriched"
        / "binance"
        / "spot"
        / "BTCUSDT"
        / "1m"
        / month
    )


def _normalized_dir(repo_root: Path, month: str) -> Path:
    return (
        _market_data_root(repo_root)
        / "normalized"
        / "binance"
        / "spot"
        / "BTCUSDT"
        / "1m"
        / month
    )


def _raw_dir(repo_root: Path, month: str) -> Path:
    return (
        _market_data_root(repo_root)
        / "raw"
        / "binance"
        / "spot"
        / "BTCUSDT"
        / "1m"
        / month
    )


def _hash_jsonl_rows(rows: Sequence[dict[str, Any]]) -> str:
    import hashlib

    digest = hashlib.sha256()
    for row in rows:
        line = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def hash_jsonl_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_regime_carry_state(repo_root: Path, month: str) -> RegimeCarryState | None:
    report_path = _enriched_dir(repo_root, month) / "regime_report.json"
    if not report_path.exists():
        return None
    report = json.loads(report_path.read_text(encoding="utf-8"))
    carry = report.get("carry_state") or {}
    buffer_path = _enriched_dir(repo_root, month) / "candles.jsonl"
    buffer: list[dict[str, Any]] = []
    if buffer_path.exists():
        lines = buffer_path.read_text(encoding="utf-8").splitlines()
        from tools.market_data.assign_regime_offline import BUFFER_MAXLEN

        for line in lines[-BUFFER_MAXLEN:]:
            if line.strip():
                buffer.append(json.loads(line))
    return RegimeCarryState(
        current_regime=str(carry.get("current_regime", "UNKNOWN")),
        candidate_regime=carry.get("candidate_regime"),
        candidate_count=int(carry.get("candidate_count", 0)),
        buffer=buffer,
    )


def _append_plausibility_sample(
    sample: list[dict[str, Any]],
    repo_root: Path,
    month: str,
    max_size: int,
    *,
    per_month: int = 100,
) -> None:
    if len(sample) >= max_size:
        return
    path = _enriched_dir(repo_root, month) / "candles.jsonl"
    if not path.exists():
        return
    taken = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if len(sample) >= max_size or taken >= per_month:
                break
            if line.strip():
                sample.append(json.loads(line))
                taken += 1


def _month_already_complete(repo_root: Path, month: str) -> bool:
    norm = _normalized_dir(repo_root, month)
    enriched = _enriched_dir(repo_root, month)
    return (norm / "quality_report.json").exists() and (
        enriched / "candles.jsonl"
    ).exists()


def _load_cached_month_record(repo_root: Path, month: str) -> MonthImportRecord | None:
    norm = _normalized_dir(repo_root, month)
    quality_path = norm / "quality_report.json"
    if not quality_path.exists():
        return None
    quality = load_dq_report_sidecar(quality_path)
    if quality is None:
        return None
    candles_path = norm / "candles.jsonl"
    if not candles_path.exists():
        raise HistoricalProbeError(
            f"Cached month {month} has quality_report.json but missing candles.jsonl"
        )
    # CDB-050: reuse is only valid when the stored DQ verdict still binds to
    # the on-disk candle content (independent recompute — no self-compare).
    candle_rows: list[dict[str, Any]] = []
    with candles_path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                candle_rows.append(json.loads(line))
    enforce_dq_content_binding(report=quality, candles=candle_rows)
    raw_zip = _raw_dir(repo_root, month)
    zip_files = list(raw_zip.glob("BTCUSDT-1m-*.zip"))
    record = MonthImportRecord(
        month=month,
        download_status="complete",
        checksum_status="verified",
        normalization_status="complete",
        regime_status="complete",
        quality_verdict=str(quality.get("verdict", "SOURCE_INVALID")),
        local_raw_path=str(zip_files[0]).replace("\\", "/") if zip_files else None,
        local_normalized_path=str(candles_path).replace("\\", "/"),
        local_enriched_path=str(
            (_enriched_dir(repo_root, month) / "candles.jsonl")
        ).replace("\\", "/"),
        candle_count=int(quality.get("gaps", {}).get("actual_candles", 0)),
        gaps=quality.get("gaps", {}),
        duplicates=quality.get("duplicates", {}),
    )
    if record.local_normalized_path and Path(record.local_normalized_path).exists():
        spec_path = norm / "dataset_spec.json"
        if spec_path.exists():
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            fp = spec.get("fingerprint") or spec.get("candles_sha256")
            if isinstance(fp, str):
                record.normalized_hash = fp
            content_fp = spec.get("content_fingerprint")
            if isinstance(content_fp, str) and content_fp.strip():
                assert_dq_content_binding(
                    {"content_fingerprint": content_fp},
                    content_fingerprint=content_fingerprint_for_candle_rows(
                        candle_rows
                    ),
                )
        if not record.normalized_hash:
            record.normalized_hash = hash_jsonl_file(Path(record.local_normalized_path))
    if record.local_enriched_path and Path(record.local_enriched_path).exists():
        espec = _enriched_dir(repo_root, month) / "dataset_spec.json"
        if espec.exists():
            spec = json.loads(espec.read_text(encoding="utf-8"))
            fp = spec.get("fingerprint") or spec.get("candles_sha256")
            if isinstance(fp, str):
                record.enriched_hash = fp
        if not record.enriched_hash:
            record.enriched_hash = hash_jsonl_file(Path(record.local_enriched_path))
    if zip_files:
        record.raw_file_hash = sha256_file(zip_files[0])
    return record


def _enrich_month(
    *,
    month: str,
    repo_root: Path,
    regime_state: RegimeCarryState | None,
) -> tuple[int, RegimeCarryState, str]:
    norm_dir = _normalized_dir(repo_root, month)
    jsonl_path = norm_dir / "candles.jsonl"
    raw_rows = [
        json.loads(line)
        for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    enriched_rows, new_state = assign_regime_ids_with_state(
        raw_rows, initial_state=regime_state
    )
    del raw_rows
    enriched_dir = _enriched_dir(repo_root, month)
    enriched_jsonl = enriched_dir / "candles.jsonl"
    from tools.market_data.historical_common import write_jsonl_and_hash

    enriched_hash = write_jsonl_and_hash(enriched_jsonl, enriched_rows)
    row_count = len(enriched_rows)
    dist = regime_distribution(enriched_rows)
    del enriched_rows
    write_json(
        enriched_dir / "regime_report.json",
        {
            "schema_version": "regime_report.v1",
            "month": month,
            "method": "offline_heuristic_adx_atr",
            "carry_over": True,
            "regime_distribution": dist,
            "carry_state": {
                **new_state.to_dict(),
                "current_regime": new_state.current_regime,
                "candidate_regime": new_state.candidate_regime,
                "candidate_count": new_state.candidate_count,
            },
        },
    )
    norm_spec_path = norm_dir / "dataset_spec.json"
    if norm_spec_path.exists():
        spec = json.loads(norm_spec_path.read_text(encoding="utf-8"))
        write_json(
            enriched_dir / "dataset_spec.json",
            {
                **spec,
                "file_path": str(enriched_jsonl).replace("\\", "/"),
                "regime_enriched": True,
                "fingerprint": enriched_hash,
                "candles_sha256": enriched_hash,
            },
        )
    write_json(
        enriched_dir / "provenance_manifest.json",
        {
            "issue": "#3990",
            "month": month,
            "source": "binance_public_data",
            "regime_method": "offline_heuristic_adx_atr_carry_over",
            "evidence_class": "historical_cross_venue_research",
        },
    )
    return row_count, new_state, enriched_hash


def _import_single_month(
    *,
    month: str,
    repo_root: Path,
    fetcher: HttpFetcher,
    skip_download: bool,
) -> dict[str, Any]:
    year, month_num = parse_year_month(month)
    start_ts_ms, end_ts_ms, expected = month_bounds(year, month_num)
    archive_name = probe.monthly_archive_filename("BTCUSDT", "1m", year, month_num)
    archive_url = probe.monthly_archive_url(
        DEFAULT_DATA_VISION_BASE,
        symbol="BTCUSDT",
        interval="1m",
        year=year,
        month=month_num,
    )
    checksum_url = probe.monthly_checksum_url(
        DEFAULT_DATA_VISION_BASE,
        symbol="BTCUSDT",
        interval="1m",
        year=year,
        month=month_num,
    )

    raw_dir = _raw_dir(repo_root, month)
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_zip = raw_dir / archive_name
    checksum_path = raw_dir / f"{archive_name}.CHECKSUM"
    meta_path = raw_dir / "download_metadata.json"

    if not skip_download or not raw_zip.exists():
        checksum_text = fetcher.fetch_text(checksum_url)
        official_checksum = probe.parse_official_checksum(
            checksum_text, expected_filename=archive_name
        )
        if not checksum_path.exists():
            checksum_path.write_text(checksum_text, encoding="utf-8")
        download = fetcher.download(
            archive_url, raw_zip, expected_sha256=official_checksum
        )
        write_json(
            meta_path,
            {
                "source_url": archive_url,
                "checksum_url": checksum_url,
                "downloaded_at_utc": download.downloaded_at_utc,
                "sha256": download.sha256,
                "official_checksum": official_checksum,
            },
        )
    else:
        checksum_text = checksum_path.read_text(encoding="utf-8")
        official_checksum = probe.parse_official_checksum(
            checksum_text, expected_filename=archive_name
        )
        download_sha = sha256_file(raw_zip)

    download_sha = sha256_file(raw_zip)
    checksum_verified = download_sha == official_checksum

    _, csv_bytes = probe.extract_zip_csv(raw_zip)
    candles, schema = probe.parse_binance_kline_csv(
        csv_bytes,
        symbol="BTCUSDT",
        timeframe="1m",
        source_file_sha256=download_sha,
    )
    from tools.market_data.historical_common import (
        assert_dq_content_binding,
        build_quality_report,
        write_jsonl_and_hash,
    )

    norm_dir = _normalized_dir(repo_root, month)
    jsonl_path = norm_dir / "candles.jsonl"
    file_hash = write_jsonl_and_hash(
        jsonl_path,
        [c.to_dict() for c in candles],
    )
    candle_count = len(candles)
    quality = build_quality_report(
        candles,
        start_ts_ms=start_ts_ms,
        end_ts_ms=end_ts_ms,
        step_ms=ONE_MINUTE_MS,
        source_hash=file_hash,
        second_parse_hash=file_hash,
    )
    # CDB-050: expected FP derived independently from the live candle series.
    independent_content_fp = content_fingerprint_for_normalized(candles)
    assert_dq_content_binding(
        quality,
        content_fingerprint=independent_content_fp,
    )
    del candles
    write_json(norm_dir / "quality_report.json", quality)
    write_json(norm_dir / "gap_report.json", quality["gaps"])
    write_json(
        norm_dir / "dataset_spec.json",
        {
            **probe.build_dataset_spec(
                symbol="BTCUSDT",
                timeframe="1m",
                start_ts_ms=start_ts_ms,
                end_ts_ms=end_ts_ms,
                file_path=jsonl_path,
                source_hash=download_sha,
                quality_verdict=quality["verdict"],
                regime_enriched=False,
                normalized_hash_value=file_hash,
            ),
            "fingerprint": file_hash,
            "candles_sha256": file_hash,
            "content_fingerprint": independent_content_fp,
            "month": month,
        },
    )
    write_json(
        norm_dir / "provenance_manifest.json",
        probe.build_provenance_manifest(
            download=type(
                "DL",
                (),
                {
                    "original_filename": archive_name,
                    "source_url": archive_url,
                    "downloaded_at_utc": utc_now_iso(),
                    "content_type": "application/zip",
                    "content_length": raw_zip.stat().st_size,
                    "sha256": download_sha,
                },
            )(),
            checksum_official=official_checksum,
            checksum_verified=checksum_verified,
            schema=schema,
            source_sha=probe.get_repo_source_sha(repo_root),
            parser_version="tools.market_data.binance_full_archive_import/1.0",
            archive_path=archive_url,
            download_path_type="monthly",
        ),
    )

    return {
        "month": month,
        "checksum_verified": checksum_verified,
        "quality_verdict": quality["verdict"],
        "raw_zip": str(raw_zip).replace("\\", "/"),
        "normalized_jsonl": str(jsonl_path).replace("\\", "/"),
        "raw_hash": download_sha,
        "normalized_hash": file_hash,
        "candle_count": candle_count,
        "gaps": quality["gaps"],
        "duplicates": quality["duplicates"],
        "expected_candles": expected,
    }


def build_coverage_report(
    records: Sequence[MonthImportRecord],
    months: Sequence[str],
) -> dict[str, Any]:
    strict = [r for r in records if r.quality_verdict == "STRICT_COMPLETE"]
    partial = [
        r
        for r in records
        if r.quality_verdict
        not in {
            "STRICT_COMPLETE",
            "SOURCE_INVALID",
            "CHECKSUM_FAILED",
            "SOURCE_UNAVAILABLE",
        }
    ]
    failed = [r for r in records if r not in strict and r not in partial]
    total_candles = sum(r.candle_count for r in records)
    expected_total = len(months) * 43200  # approximate; Feb differs
    missing_months = [m for m in months if m not in {r.month for r in records}]

    earliest_ts = None
    latest_ts = None
    for r in strict:
        year, month_num = parse_year_month(r.month)
        start, end, _ = month_bounds(year, month_num)
        earliest_ts = start if earliest_ts is None else min(earliest_ts, start)
        latest_ts = end if latest_ts is None else max(latest_ts, end)

    def _dir_size(base: Path) -> int:
        if not base.exists():
            return 0
        return sum(f.stat().st_size for f in base.rglob("*") if f.is_file())

    market_data_root = _market_data_root(REPO_ROOT)
    raw_base = market_data_root / "raw" / "binance"
    norm_base = market_data_root / "normalized" / "binance"
    enrich_base = market_data_root / "enriched" / "binance"

    return {
        "earliest_ts_ms": earliest_ts,
        "latest_ts_ms": latest_ts,
        "month_count": len(months),
        "strict_complete_months": len(strict),
        "partial_months": len(partial),
        "failed_months": len(failed),
        "missing_months": missing_months,
        "total_candles": total_candles,
        "expected_candles_approx": expected_total,
        "storage_bytes": {
            "raw": _dir_size(raw_base),
            "normalized": _dir_size(norm_base),
            "enriched": _dir_size(enrich_base),
        },
    }


def run_import_by_year(
    *,
    repo_root: Path = REPO_ROOT,
    start_year: int | None = None,
    end_year: int | None = None,
) -> dict[str, Any]:
    """Run one subprocess per year to avoid long-run memory fragmentation."""
    available = list_available_months()
    start = start_year or int(available[0].split("-")[0])
    end = end_year or int(last_complete_month(available=available).split("-")[0])
    results: list[dict[str, Any]] = []
    for year in range(start, end + 1):
        year_months = [m for m in available if m.startswith(f"{year}-")]
        if not year_months:
            continue
        cmd = [
            sys.executable,
            "-m",
            "tools.market_data.binance_full_archive_import",
            "--start-month",
            year_months[0],
            "--end-month",
            year_months[-1],
            "--no-subprocess",
        ]
        completed = subprocess.run(
            cmd, cwd=str(repo_root), capture_output=True, text=True, check=False
        )
        results.append(
            {
                "year": year,
                "exit_code": completed.returncode,
                "stderr_tail": completed.stderr[-2000:],
            }
        )
        if completed.returncode == 3:
            break
    return import_range(repo_root=repo_root)


def run_smoke_replays(
    *,
    repo_root: Path = REPO_ROOT,
    month: str | None = None,
) -> dict[str, Any]:
    """Smoke replay on one month before full campaign."""
    month = month or "2026-06"
    jsonl = _normalized_dir(repo_root, month) / "candles.jsonl"
    if not jsonl.exists():
        raise HistoricalProbeError(f"Smoke input missing: {jsonl}")
    results = []
    for strategy_id in (
        "donchian_breakout_v1",
        "breakout_trend_filter_v1",
        "primary_breakout_v1",
    ):
        enriched = _enriched_dir(repo_root, month) / "candles.jsonl"
        candles_path = (
            enriched
            if strategy_id == "primary_breakout_v1" and enriched.exists()
            else jsonl
        )
        results.append(
            probe.run_replay_probe(
                candles_path=candles_path,
                strategy_id=strategy_id,
                output_dir=repo_root
                / "artifacts"
                / "replay_reports"
                / "binance_full_import_smoke_3990"
                / month
                / strategy_id,
                scenario_group_id=f"bin_smoke_{strategy_id[:8]}_{month.replace('-', '')}",
                repo_root=repo_root,
            )
        )
    all_pass = all(r.get("exit_code") == 0 for r in results)
    return {"status": "PASS" if all_pass else "FAIL", "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Binance BTCUSDT 1m full archive import (#3990)"
    )
    parser.add_argument("--list-months", action="store_true")
    parser.add_argument("--start-month", default=None)
    parser.add_argument("--end-month", default=None)
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--no-regime", action="store_true")
    parser.add_argument("--smoke-replay", action="store_true")
    parser.add_argument("--smoke-month", default="2026-06")
    parser.add_argument("--no-subprocess", action="store_true")
    parser.add_argument("--by-year", action="store_true")
    args = parser.parse_args()

    try:
        if args.list_months:
            months = list_available_months()
            print(
                json.dumps(
                    {
                        "count": len(months),
                        "first": months[0],
                        "last": months[-1],
                        "last_complete": last_complete_month(available=months),
                    },
                    indent=2,
                )
            )
            return 0
        if args.smoke_replay:
            result = run_smoke_replays(month=args.smoke_month)
            print(json.dumps(result, indent=2))
            return 0 if result["status"] == "PASS" else 2

        if args.by_year:
            manifest = run_import_by_year()
            print(json.dumps(manifest, indent=2))
            return 0 if manifest.get("import_status") == "FULL_IMPORT_PASS" else 2

        manifest = import_range(
            start_month=args.start_month,
            end_month=args.end_month,
            skip_download=args.skip_download,
            enrich_regime=not args.no_regime,
        )
        print(json.dumps(manifest, indent=2))
        if manifest["import_status"] == "FULL_IMPORT_BLOCKED":
            return 3
        if manifest["import_status"] == "FULL_IMPORT_PARTIAL":
            return 2
        return 0
    except HistoricalProbeError as exc:
        print(f"IMPORT_ERROR: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
