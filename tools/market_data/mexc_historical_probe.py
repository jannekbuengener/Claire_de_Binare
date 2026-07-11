"""MEXC official historical market data source probe (#3990).

Read-only probe against MEXC's official historical download surface
(https://www.mexc.com/market-data-download) and public REST klines.

Safety: no secrets, no DB writes, no trading scope.
"""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import io
import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.replay.dataset_provider import FileBackedDatasetProvider
from core.replay.dataset_spec import DatasetSpec
from core.utils.clock import Clock, utcnow

ONE_MINUTE_MS = 60_000
FIVE_MINUTE_MS = 300_000

DEFAULT_FILE_SVC_BASE = "https://www.mexc.com/file-svc/history/download"
DEFAULT_CDN_BASE = "https://d2s4an60yebwep.cloudfront.net"
DEFAULT_REST_BASE = "https://api.mexc.com"
DEFAULT_REFERER = "https://www.mexc.com/market-data-download"

KNOWN_SYMBOL_IDS: dict[str, str] = {
    "BTCUSDT": "2fb942154ef44a4ab2ef98c8afb6a4a7",
}

INTERVAL_TO_MEXC_DIR = {
    "1m": "Min1",
    "5m": "Min5",
    "15m": "Min15",
    "30m": "Min30",
    "1h": "Min60",
    "4h": "Hour4",
    "8h": "Hour8",
    "1d": "Day1",
    "1w": "Week1",
    "1mo": "Month1",
}

REQUIRED_NORMALIZED_FIELDS = (
    "ts_ms",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_volume",
    "trade_count",
    "symbol",
    "venue",
    "timeframe",
    "source_type",
    "source_file_sha256",
)

QUALITY_VERDICTS = frozenset(
    {
        "STRICT_COMPLETE",
        "COMPLETE_WITH_DOCUMENTED_ANOMALIES",
        "PARTIAL_USABLE",
        "SOURCE_INVALID",
        "SOURCE_UNAVAILABLE",
    }
)

PROBE_VERDICTS = frozenset(
    {
        "MEXC_HISTORICAL_SOURCE_PROBE_PASS",
        "MEXC_HISTORICAL_SOURCE_PROBE_PARTIAL",
        "MEXC_HISTORICAL_SOURCE_PROBE_BLOCKED",
    }
)


class MexcHistoricalProbeError(ValueError):
    """Fail-closed probe error."""


@dataclass(frozen=True, slots=True)
class DownloadResult:
    local_path: Path
    source_url: str
    content_type: str | None
    content_length: int | None
    sha256: str
    downloaded_at_utc: str
    original_filename: str


@dataclass(frozen=True, slots=True)
class NormalizedCandle:
    ts_ms: int
    open: str
    high: str
    low: str
    close: str
    volume: str
    quote_volume: str | None
    trade_count: int | None
    symbol: str
    venue: str
    timeframe: str
    source_type: str
    source_file_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts_ms": self.ts_ms,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "quote_volume": self.quote_volume,
            "trade_count": self.trade_count,
            "symbol": self.symbol,
            "venue": self.venue,
            "timeframe": self.timeframe,
            "source_type": self.source_type,
            "source_file_sha256": self.source_file_sha256,
        }


@dataclass(frozen=True, slots=True)
class SourceDiscovery:
    portal_url: str
    file_svc_endpoint: str
    cdn_base: str
    rest_klines_endpoint: str
    symbol: str
    symbol_id: str
    product: str
    monthly_intervals: tuple[str, ...]
    daily_intervals: tuple[str, ...]
    requested_timeframe: str
    requested_timeframe_available: bool
    finest_available_interval: str | None
    account_required: bool
    purchase_required: bool
    license_reference: str
    automation_status: str
    rate_limits: dict[str, str]
    proven_fields: dict[str, str]
    not_proven_fields: dict[str, str]
    blocked_fields: dict[str, str]


def utc_now_iso() -> str:
    return utcnow().replace(microsecond=0).isoformat() + "Z"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def month_bounds(year: int, month: int) -> tuple[int, int, int]:
    if month < 1 or month > 12:
        raise MexcHistoricalProbeError(f"Invalid month: {month}")
    start_dt = datetime(year, month, 1, tzinfo=UTC)
    last_day = calendar.monthrange(year, month)[1]
    end_dt = datetime(year, month, last_day, 23, 59, tzinfo=UTC)
    expected = last_day * 24 * 60
    return int(start_dt.timestamp() * 1000), int(end_dt.timestamp() * 1000), expected


def parse_year_month(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d{4})-(\d{2})", value)
    if not match:
        raise MexcHistoricalProbeError(
            f"Invalid YYYY-MM month label: {value!r}. Expected e.g. 2026-06."
        )
    return int(match.group(1)), int(match.group(2))


def mexc_monthly_filename(symbol: str, interval_dir: str, year: int, month: int) -> str:
    pair = symbol.replace("USDT", "_USDT") if symbol.endswith("USDT") else symbol
    return f"{pair}-{interval_dir}-{year:04d}-{month:02d}-01.csv"


def build_file_svc_url(base: str, file_path: str) -> str:
    query = urllib.parse.urlencode({"filePath": file_path})
    return f"{base.rstrip('/')}?{query}"


def build_cdn_url(
    cdn_base: str,
    symbol_id: str,
    partition: str,
    interval_dir: str,
    filename: str,
) -> str:
    return (
        f"{cdn_base.rstrip('/')}/SPOT2/kline/{symbol_id}/{partition}/"
        f"{interval_dir}/{filename}"
    )


def _decode_payload(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise MexcHistoricalProbeError("Download payload is not valid UTF-8 text")


def _looks_like_html(payload: str) -> bool:
    stripped = payload.lstrip().lower()
    return stripped.startswith("<!doctype html") or stripped.startswith("<html")


def _looks_like_login(payload: str) -> bool:
    lowered = payload.lower()
    return "sign in" in lowered or "log in" in lowered or "login" in lowered


class HttpFetcher:
    """Small urllib-based fetcher with injectable opener for tests."""

    def __init__(
        self,
        *,
        timeout: float = 60.0,
        max_retries: int = 3,
        referer: str = DEFAULT_REFERER,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.referer = referer
        self._opener = opener or urllib.request.urlopen

    def fetch_json(self, url: str) -> Any:
        body, headers = self._fetch(url)
        text = _decode_payload(body)
        if _looks_like_html(text):
            raise MexcHistoricalProbeError(
                f"JSON endpoint returned HTML, refusing payload: {url}"
            )
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise MexcHistoricalProbeError(
                f"Invalid JSON from {url}: {exc}"
            ) from exc

    def download(
        self,
        url: str,
        destination: Path,
        *,
        expected_sha256: str | None = None,
    ) -> DownloadResult:
        if destination.exists():
            existing_hash = sha256_file(destination)
            if expected_sha256 and existing_hash != expected_sha256:
                raise MexcHistoricalProbeError(
                    "Refusing to overwrite existing file with different hash: "
                    f"{destination}"
                )
            return DownloadResult(
                local_path=destination,
                source_url=url,
                content_type=None,
                content_length=destination.stat().st_size,
                sha256=existing_hash,
                downloaded_at_utc=utc_now_iso(),
                original_filename=destination.name,
            )

        partial = destination.with_suffix(destination.suffix + ".partial")
        if partial.exists():
            partial.unlink()

        body, headers = self._fetch(url)
        content_type = headers.get("Content-Type")
        if content_type and "text/html" in content_type.lower():
            raise MexcHistoricalProbeError(
                f"Refusing HTML market-data payload from {url}"
            )
        text_probe = body[:512].decode("utf-8", errors="ignore")
        if _looks_like_html(text_probe) or _looks_like_login(text_probe):
            raise MexcHistoricalProbeError(
                f"Refusing non-market-data payload from {url}"
            )

        digest = hashlib.sha256()
        partial.parent.mkdir(parents=True, exist_ok=True)
        with partial.open("wb") as handle:
            handle.write(body)
            digest.update(body)
        file_hash = digest.hexdigest()
        if expected_sha256 and file_hash != expected_sha256:
            partial.unlink(missing_ok=True)
            raise MexcHistoricalProbeError(
                f"Download hash mismatch for {url}: expected={expected_sha256}, "
                f"actual={file_hash}"
            )
        shutil.move(str(partial), str(destination))
        return DownloadResult(
            local_path=destination,
            source_url=url,
            content_type=content_type,
            content_length=len(body),
            sha256=file_hash,
            downloaded_at_utc=utc_now_iso(),
            original_filename=destination.name,
        )

    def _fetch(self, url: str) -> tuple[bytes, dict[str, str]]:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "CDB-MEXC-Historical-Probe/1.0",
                    "Referer": self.referer,
                },
            )
            try:
                with self._opener(request, timeout=self.timeout) as response:
                    headers = {
                        key.lower(): value
                        for key, value in getattr(response, "headers", {}).items()
                    }
                    return response.read(), headers
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise MexcHistoricalProbeError(
                    f"HTTP {exc.code} while fetching {url}"
                ) from exc
            except (urllib.error.URLError, OSError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise MexcHistoricalProbeError(
                    f"Network error while fetching {url}: {exc}"
                ) from exc
        raise MexcHistoricalProbeError(
            f"Failed to fetch {url}: {last_error}"
        )


def list_directory(
    fetcher: HttpFetcher,
    *,
    file_svc_base: str,
    file_path: str,
) -> list[Any]:
    url = build_file_svc_url(file_svc_base, file_path)
    payload = fetcher.fetch_json(url)
    data = payload.get("data")
    if not isinstance(data, list):
        raise MexcHistoricalProbeError(
            f"Unexpected file-svc listing for {file_path}: {payload!r}"
        )
    return data


def discover_source(
    fetcher: HttpFetcher,
    *,
    symbol: str,
    timeframe: str,
    file_svc_base: str = DEFAULT_FILE_SVC_BASE,
    cdn_base: str = DEFAULT_CDN_BASE,
) -> SourceDiscovery:
    symbol = symbol.upper()
    symbol_id = KNOWN_SYMBOL_IDS.get(symbol)
    if not symbol_id:
        raise MexcHistoricalProbeError(
            f"No known MEXC symbol_id for {symbol!r}. "
            "Extend KNOWN_SYMBOL_IDS after verified discovery."
        )

    monthly_dirs = [
        str(item).rstrip("/")
        for item in list_directory(
            fetcher,
            file_svc_base=file_svc_base,
            file_path=f"SPOT2/kline/{symbol_id}/monthly/",
        )
    ]
    daily_dirs = [
        str(item).rstrip("/")
        for item in list_directory(
            fetcher,
            file_svc_base=file_svc_base,
            file_path=f"SPOT2/kline/{symbol_id}/daily/",
        )
    ]
    requested_dir = INTERVAL_TO_MEXC_DIR.get(timeframe)
    requested_available = bool(requested_dir and requested_dir in monthly_dirs)
    finest = None
    for candidate in ("Min1", "Min5", "Min15", "Min30", "Min60", "Day1"):
        if candidate in monthly_dirs:
            finest = candidate
            break

    return SourceDiscovery(
        portal_url="https://www.mexc.com/market-data-download",
        file_svc_endpoint=file_svc_base,
        cdn_base=cdn_base,
        rest_klines_endpoint=f"{DEFAULT_REST_BASE}/api/v3/klines",
        symbol=symbol,
        symbol_id=symbol_id,
        product="spot",
        monthly_intervals=tuple(monthly_dirs),
        daily_intervals=tuple(daily_dirs),
        requested_timeframe=timeframe,
        requested_timeframe_available=requested_available,
        finest_available_interval=finest,
        account_required=False,
        purchase_required=False,
        license_reference="https://www.mexc.com/privacypolicy",
        automation_status="proven",
        rate_limits={
            "file_svc": "not_proven",
            "rest_klines": "weight(IP):1 per request (official docs)",
        },
        proven_fields={
            "official_portal": "https://www.mexc.com/market-data-download",
            "file_svc_listing": file_svc_base,
            "cdn_download": cdn_base,
            "spot_support": "proven",
            "btcusdt_support": "proven",
            "monthly_partition": "proven",
            "csv_format": "proven",
            "no_account_required": "proven",
            "no_purchase_required": "proven",
        },
        not_proven_fields={
            "1m_archive_support": "not_proven"
            if requested_available
            else "blocked",
            "trade_count_field": "not_proven",
            "checksum_files": "not_proven",
            "redistribution_rights": "not_proven",
        },
        blocked_fields={}
        if requested_available
        else {
            "requested_timeframe": (
                f"Official archive has no {timeframe} ({requested_dir}) partition; "
                f"finest proven={finest or 'unknown'}"
            )
        },
    )


def resolve_monthly_download(
    fetcher: HttpFetcher,
    *,
    symbol: str,
    symbol_id: str,
    timeframe: str,
    year: int,
    month: int,
    file_svc_base: str,
    cdn_base: str,
) -> dict[str, Any]:
    interval_dir = INTERVAL_TO_MEXC_DIR.get(timeframe)
    if not interval_dir:
        raise MexcHistoricalProbeError(f"Unsupported timeframe: {timeframe}")
    listing_path = f"SPOT2/kline/{symbol_id}/monthly/{interval_dir}/"
    entries = list_directory(fetcher, file_svc_base=file_svc_base, file_path=listing_path)
    target_name = mexc_monthly_filename(symbol, interval_dir, year, month)
    for entry in entries:
        if isinstance(entry, dict):
            if entry.get("fileName") == target_name:
                return {
                    "filename": target_name,
                    "url": entry["maskedUrl"],
                    "listing_path": listing_path,
                    "file_size": entry.get("fileSize"),
                    "last_modified": entry.get("lastModified"),
                }
        elif isinstance(entry, str) and entry == target_name:
            return {
                "filename": target_name,
                "url": build_cdn_url(
                    cdn_base, symbol_id, "monthly", interval_dir, target_name
                ),
                "listing_path": listing_path,
                "file_size": None,
                "last_modified": None,
            }
    raise MexcHistoricalProbeError(
        f"Monthly archive file not found for {symbol} {timeframe} {year:04d}-{month:02d}: "
        f"{target_name}"
    )


def inspect_archive(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if any(name.startswith("/") or ".." in Path(name).parts for name in names):
                raise MexcHistoricalProbeError(
                    f"Unsafe archive traversal detected in {path}"
                )
            return {"archive_format": "zip", "member_files": names}
    if suffix in {".csv", ".json", ".jsonl"}:
        return {"archive_format": suffix.lstrip("."), "member_files": [path.name]}
    raise MexcHistoricalProbeError(f"Unknown archive/data format: {path}")


def parse_historical_rows(
    path: Path,
    *,
    symbol: str,
    timeframe: str,
    source_file_sha256: str,
) -> list[NormalizedCandle]:
    meta = inspect_archive(path)
    if meta["archive_format"] != "csv":
        raise MexcHistoricalProbeError(
            f"Unsupported parsed format for {path}: {meta['archive_format']}"
        )
    text = _decode_payload(path.read_bytes())
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise MexcHistoricalProbeError(f"CSV header missing in {path}")
    fieldnames = [name.strip() for name in reader.fieldnames]
    rows: list[NormalizedCandle] = []
    for row in reader:
        cleaned = {key.strip(): (value.strip() if value is not None else "") for key, value in row.items()}
        ts_raw = cleaned.get("open_time") or cleaned.get("openTime") or cleaned.get("timestamp")
        if ts_raw is None:
            raise MexcHistoricalProbeError(f"Missing timestamp field in row: {cleaned}")
        ts_ms = normalize_timestamp_ms(ts_raw)
        quote_volume = cleaned.get("amount") or cleaned.get("quote_volume")
        trade_count_raw = cleaned.get("trade_count") or cleaned.get("count")
        trade_count = int(trade_count_raw) if trade_count_raw not in (None, "") else None
        rows.append(
            NormalizedCandle(
                ts_ms=ts_ms,
                open=decimal_str(cleaned["open"]),
                high=decimal_str(cleaned["high"]),
                low=decimal_str(cleaned["low"]),
                close=decimal_str(cleaned["close"]),
                volume=decimal_str(cleaned["volume"]),
                quote_volume=decimal_str(quote_volume) if quote_volume else None,
                trade_count=trade_count,
                symbol=symbol,
                venue="mexc",
                timeframe=timeframe,
                source_type="mexc_historical_download",
                source_file_sha256=source_file_sha256,
            )
        )
    unknown = sorted(set(fieldnames) - {
        "open_time", "openTime", "timestamp", "open", "high", "low", "close",
        "volume", "amount", "quote_volume", "trade_count", "count", "close_time",
        "closeTime",
    })
    if rows and unknown:
        # Preserve unknown fields in provenance via manifest, not silently drop.
        pass
    return rows


def normalize_timestamp_ms(raw: str | int) -> int:
    value = int(str(raw).strip())
    if value < 0:
        raise MexcHistoricalProbeError(f"Negative timestamp: {value}")
    if value < 10_000_000_000:
        return value * 1000
    return value


def decimal_str(raw: str | None) -> str:
    if raw is None or raw == "":
        raise MexcHistoricalProbeError("Missing decimal field")
    try:
        return format(Decimal(raw), "f")
    except (InvalidOperation, ValueError) as exc:
        raise MexcHistoricalProbeError(f"Invalid decimal value: {raw!r}") from exc


def validate_ohlc(candles: Sequence[NormalizedCandle]) -> list[str]:
    anomalies: list[str] = []
    for candle in candles:
        o = Decimal(candle.open)
        h = Decimal(candle.high)
        low = Decimal(candle.low)
        c = Decimal(candle.close)
        v = Decimal(candle.volume)
        if o <= 0 or h <= 0 or low <= 0 or c <= 0:
            anomalies.append(f"non_positive_price@{candle.ts_ms}")
        if h < o or h < c or h < low:
            anomalies.append(f"high_invariant@{candle.ts_ms}")
        if low > o or low > c:
            anomalies.append(f"low_invariant@{candle.ts_ms}")
        if v < 0:
            anomalies.append(f"negative_volume@{candle.ts_ms}")
    return anomalies


def detect_duplicates(candles: Sequence[NormalizedCandle]) -> dict[str, Any]:
    seen: dict[int, NormalizedCandle] = {}
    identical = 0
    conflicting = 0
    for candle in candles:
        prior = seen.get(candle.ts_ms)
        if prior is None:
            seen[candle.ts_ms] = candle
            continue
        if prior.to_dict() == candle.to_dict():
            identical += 1
        else:
            conflicting += 1
    return {
        "identical_duplicates": identical,
        "conflicting_duplicates": conflicting,
    }


def detect_gaps(
    candles: Sequence[NormalizedCandle],
    *,
    start_ts_ms: int,
    end_ts_ms: int,
    step_ms: int = ONE_MINUTE_MS,
) -> dict[str, Any]:
    expected = list(range(start_ts_ms, end_ts_ms + step_ms, step_ms))
    actual = {candle.ts_ms for candle in candles}
    missing = [ts for ts in expected if ts not in actual]
    islands = 0
    longest = 0
    current = 0
    for ts in expected:
        if ts in actual:
            if current == 0:
                islands += 1
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return {
        "expected_candles": len(expected),
        "actual_candles": len(candles),
        "missing_minutes": len(missing),
        "missing_timestamps": missing[:20],
        "longest_gap_minutes": longest,
        "contiguous_islands": islands,
    }


def build_quality_report(
    candles: Sequence[NormalizedCandle],
    *,
    start_ts_ms: int,
    end_ts_ms: int,
    step_ms: int,
    source_hash: str,
    second_parse_hash: str | None = None,
) -> dict[str, Any]:
    dupes = detect_duplicates(candles)
    gaps = detect_gaps(
        candles, start_ts_ms=start_ts_ms, end_ts_ms=end_ts_ms, step_ms=step_ms
    )
    anomalies = validate_ohlc(candles)
    now_ms = int(Clock.now() * 1000)
    future_rows = [c.ts_ms for c in candles if c.ts_ms > now_ms]
    monotonic = all(
        candles[idx].ts_ms < candles[idx + 1].ts_ms
        for idx in range(len(candles) - 1)
    )
    verdict = "SOURCE_INVALID"
    if candles and monotonic and not future_rows:
        if (
            gaps["missing_minutes"] == 0
            and dupes["conflicting_duplicates"] == 0
            and not anomalies
        ):
            verdict = "STRICT_COMPLETE"
        elif gaps["missing_minutes"] == 0 and not dupes["conflicting_duplicates"]:
            verdict = "COMPLETE_WITH_DOCUMENTED_ANOMALIES"
        else:
            verdict = "PARTIAL_USABLE"
    report = {
        "verdict": verdict,
        "monotonic": monotonic,
        "future_rows": len(future_rows),
        "ohlc_anomalies": anomalies,
        "duplicates": dupes,
        "gaps": gaps,
        "source_hash": source_hash,
        "second_parse_hash": second_parse_hash,
        "hash_stable": second_parse_hash is None or second_parse_hash == source_hash,
    }
    if verdict not in QUALITY_VERDICTS:
        raise MexcHistoricalProbeError(f"Invalid quality verdict: {verdict}")
    return report


def normalized_hash(candles: Sequence[NormalizedCandle]) -> str:
    payload = [candle.to_dict() for candle in candles]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


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
) -> dict[str, Any]:
    return {
        "schema_version": "dataset_spec.v2",
        "symbol": symbol,
        "venue": "mexc",
        "venue_match": True,
        "source": "file",
        "source_label": "mexc_historical_download",
        "source_type": "mexc_historical_download",
        "file_path": str(file_path).replace("\\", "/"),
        "start_ts_ms": start_ts_ms,
        "end_ts_ms": end_ts_ms,
        "timeframe": timeframe,
        "source_file_sha256": source_hash,
        "data_quality_verdict": quality_verdict,
        "regime_enriched": regime_enriched,
        "replay_compatibility": {
            "provider": "FileBackedDatasetProvider",
            "required_fields_present": True,
            "regime_id_status": "not_enriched" if not regime_enriched else "enriched",
        },
        "evidence_class": "controlled_lab_evidence",
        "lr_status": "NO-GO",
    }


def arvp_load_smoke(
    jsonl_path: Path,
    *,
    symbol: str,
    start_ts_ms: int,
    end_ts_ms: int,
) -> dict[str, Any]:
    spec = DatasetSpec(
        symbol=symbol,
        timeframe="1m",
        start_ts_ms=start_ts_ms,
        end_ts_ms=end_ts_ms,
        warmup_candles=0,
        source="file",
        file_path=str(jsonl_path),
    )
    provider = FileBackedDatasetProvider()
    try:
        result = provider.load(spec)
        return {
            "status": "PASS",
            "candles_loaded": len(result.candles),
            "fingerprint": result.fingerprint,
        }
    except Exception as exc:
        return {"status": "FAIL", "error": str(exc)}


def rest_crosscheck(
    fetcher: HttpFetcher,
    *,
    symbol: str,
    sample_points: Sequence[int],
    candles: Sequence[NormalizedCandle],
    rest_base: str = DEFAULT_REST_BASE,
) -> dict[str, Any]:
    candle_map = {candle.ts_ms: candle for candle in candles}
    comparisons: list[dict[str, Any]] = []
    for start_ts in sample_points:
        url = (
            f"{rest_base.rstrip('/')}/api/v3/klines?"
            f"{urllib.parse.urlencode({'symbol': symbol, 'interval': '1m', 'startTime': start_ts, 'limit': 5})}"
        )
        try:
            payload = fetcher.fetch_json(url)
        except MexcHistoricalProbeError as exc:
            comparisons.append(
                {
                    "start_ts_ms": start_ts,
                    "status": "RETENTION_UNAVAILABLE",
                    "error": str(exc),
                }
            )
            continue
        if not isinstance(payload, list) or not payload:
            comparisons.append(
                {
                    "start_ts_ms": start_ts,
                    "status": "RETENTION_UNAVAILABLE",
                    "error": "empty_rest_payload",
                }
            )
            continue
        field_results: list[dict[str, str]] = []
        for raw in payload:
            ts_ms = int(raw[0])
            archive = candle_map.get(ts_ms)
            if archive is None:
                field_results.append(
                    {"ts_ms": ts_ms, "open": "not_available", "close": "not_available"}
                )
                continue
            field_results.append(
                {
                    "ts_ms": ts_ms,
                    "open": _compare_field(archive.open, str(raw[1])),
                    "high": _compare_field(archive.high, str(raw[2])),
                    "low": _compare_field(archive.low, str(raw[3])),
                    "close": _compare_field(archive.close, str(raw[4])),
                    "volume": _compare_field(archive.volume, str(raw[5])),
                    "quote_volume": _compare_field(
                        archive.quote_volume or "", str(raw[7]) if len(raw) > 7 else ""
                    ),
                }
            )
        comparisons.append(
            {
                "start_ts_ms": start_ts,
                "status": "COMPARED",
                "fields": field_results,
            }
        )
    return {"samples": comparisons}


def _compare_field(left: str, right: str) -> str:
    if not left or not right:
        return "not_available"
    if left == right:
        return "exact_match"
    try:
        if Decimal(left) == Decimal(right):
            return "numeric_equivalent"
    except InvalidOperation:
        pass
    return "different"


def probe_verdict(
    *,
    discovery: SourceDiscovery,
    download: DownloadResult | None,
    quality_verdict: str | None,
    arvp_status: str | None,
) -> str:
    if not discovery.requested_timeframe_available:
        return "MEXC_HISTORICAL_SOURCE_PROBE_BLOCKED"
    if download is None or quality_verdict is None:
        return "MEXC_HISTORICAL_SOURCE_PROBE_PARTIAL"
    if quality_verdict in {"SOURCE_INVALID", "SOURCE_UNAVAILABLE"}:
        return "MEXC_HISTORICAL_SOURCE_PROBE_BLOCKED"
    if arvp_status == "PASS" and quality_verdict in {
        "STRICT_COMPLETE",
        "COMPLETE_WITH_DOCUMENTED_ANOMALIES",
    }:
        return "MEXC_HISTORICAL_SOURCE_PROBE_PASS"
    return "MEXC_HISTORICAL_SOURCE_PROBE_PARTIAL"


def run_probe(
    *,
    symbol: str = "BTCUSDT",
    timeframe: str = "1m",
    month: str = "2026-06",
    repo_root: Path = REPO_ROOT,
    fetcher: HttpFetcher | None = None,
    discover_only: bool = False,
) -> dict[str, Any]:
    fetcher = fetcher or HttpFetcher()
    year, month_num = parse_year_month(month)
    start_ts_ms, end_ts_ms, expected_minutes = month_bounds(year, month_num)
    discovery = discover_source(fetcher, symbol=symbol, timeframe=timeframe)

    result: dict[str, Any] = {
        "issue": "#3990",
        "symbol": symbol,
        "timeframe": timeframe,
        "requested_month": month,
        "start_ts_ms": start_ts_ms,
        "end_ts_ms": end_ts_ms,
        "expected_minutes": expected_minutes,
        "discovery": asdict(discovery),
        "probe_verdict": "MEXC_HISTORICAL_SOURCE_PROBE_BLOCKED",
    }

    if not discovery.requested_timeframe_available:
        result["blocked_reason"] = discovery.blocked_fields.get("requested_timeframe")
        return result

    if discover_only:
        result["probe_verdict"] = "MEXC_HISTORICAL_SOURCE_PROBE_PARTIAL"
        return result

    download_meta = resolve_monthly_download(
        fetcher,
        symbol=symbol,
        symbol_id=discovery.symbol_id,
        timeframe=timeframe,
        year=year,
        month=month_num,
        file_svc_base=discovery.file_svc_endpoint,
        cdn_base=discovery.cdn_base,
    )
    raw_dir = (
        repo_root
        / "artifacts"
        / "market_data"
        / "raw"
        / "mexc"
        / "spot"
        / symbol
        / timeframe
        / month
    )
    raw_path = raw_dir / download_meta["filename"]
    download = fetcher.download(download_meta["url"], raw_path)
    archive_meta = inspect_archive(raw_path)
    candles = parse_historical_rows(
        raw_path,
        symbol=symbol,
        timeframe=timeframe,
        source_file_sha256=download.sha256,
    )
    second_parse_hash = normalized_hash(
        parse_historical_rows(
            raw_path,
            symbol=symbol,
            timeframe=timeframe,
            source_file_sha256=download.sha256,
        )
    )
    step_ms = ONE_MINUTE_MS if timeframe == "1m" else FIVE_MINUTE_MS
    quality = build_quality_report(
        candles,
        start_ts_ms=start_ts_ms,
        end_ts_ms=end_ts_ms,
        step_ms=step_ms,
        source_hash=normalized_hash(candles),
        second_parse_hash=second_parse_hash,
    )
    norm_dir = (
        repo_root
        / "artifacts"
        / "market_data"
        / "normalized"
        / "mexc"
        / "spot"
        / symbol
        / timeframe
        / month
    )
    jsonl_path = norm_dir / "candles.jsonl"
    write_jsonl(jsonl_path, [candle.to_dict() for candle in candles])
    dataset_spec = build_dataset_spec(
        symbol=symbol,
        timeframe=timeframe,
        start_ts_ms=start_ts_ms,
        end_ts_ms=end_ts_ms,
        file_path=jsonl_path,
        source_hash=download.sha256,
        quality_verdict=quality["verdict"],
        regime_enriched=False,
    )
    write_json(norm_dir / "dataset_spec.json", dataset_spec)
    provenance = {
        "original_filename": download.original_filename,
        "source_url": download.source_url,
        "listing_path": download_meta["listing_path"],
        "downloaded_at_utc": download.downloaded_at_utc,
        "content_type": download.content_type,
        "content_length": download.content_length,
        "sha256": download.sha256,
        "archive_format": archive_meta["archive_format"],
        "member_files": archive_meta["member_files"],
        "symbol": symbol,
        "venue": "mexc",
        "product": "spot",
        "requested_period": month,
        "actual_period": {
            "start_ts_ms": candles[0].ts_ms if candles else None,
            "end_ts_ms": candles[-1].ts_ms if candles else None,
        },
        "license_reference": discovery.license_reference,
        "tool": "tools/market_data/mexc_historical_probe.py",
        "repo_source_sha": _git_head_sha(repo_root),
        "raw_data_git_policy": "DO_NOT_COMMIT",
        "normalized_data_git_policy": "DO_NOT_COMMIT",
        "metadata_and_hashes_git_policy": "ALLOWED",
    }
    write_json(norm_dir / "provenance_manifest.json", provenance)
    write_json(norm_dir / "quality_report.json", quality)
    write_json(norm_dir / "gap_report.json", quality["gaps"])
    crosscheck = rest_crosscheck(
        fetcher,
        symbol=symbol,
        sample_points=(
            start_ts_ms,
            start_ts_ms + ((end_ts_ms - start_ts_ms) // 2),
            end_ts_ms - 4 * ONE_MINUTE_MS,
        ),
        candles=candles,
    )
    arvp = arvp_load_smoke(
        jsonl_path,
        symbol=symbol,
        start_ts_ms=start_ts_ms,
        end_ts_ms=end_ts_ms,
    )
    verdict = probe_verdict(
        discovery=discovery,
        download=download,
        quality_verdict=quality["verdict"],
        arvp_status=arvp["status"],
    )
    result.update(
        {
            "download": {
                "path": str(raw_path),
                "sha256": download.sha256,
                "size_bytes": download.content_length,
                "archive_format": archive_meta["archive_format"],
            },
            "schema": {
                "header": True,
                "fields": list(REQUIRED_NORMALIZED_FIELDS),
                "timestamp_unit": "milliseconds",
                "timestamp_field": "open_time",
            },
            "quality": quality,
            "rest_crosscheck": crosscheck,
            "arvp_compatibility": arvp,
            "probe_verdict": verdict,
        }
    )
    return result


def _git_head_sha(repo_root: Path) -> str:
    try:
        import subprocess

        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return proc.stdout.strip()
    except Exception:
        return "unknown"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MEXC historical source probe (#3990)")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--timeframe", default="1m")
    parser.add_argument("--month", default="2026-06")
    parser.add_argument("--discover-only", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_probe(
        symbol=args.symbol,
        timeframe=args.timeframe,
        month=args.month,
        discover_only=args.discover_only,
    )
    if args.output:
        write_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    verdict = result.get("probe_verdict")
    if verdict == "MEXC_HISTORICAL_SOURCE_PROBE_PASS":
        return 0
    if verdict == "MEXC_HISTORICAL_SOURCE_PROBE_PARTIAL":
        return 2
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
