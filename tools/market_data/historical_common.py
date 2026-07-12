"""Provider-neutral helpers for historical market-data source probes."""

from __future__ import annotations

import calendar
import hashlib
import io
import json
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Sequence

from core.replay.dataset_provider import FileBackedDatasetProvider
from core.replay.dataset_spec import DatasetSpec
from core.utils.clock import Clock, utcnow

ONE_MINUTE_MS = 60_000
SECONDS_THRESHOLD = 10_000_000_000
MILLISECONDS_THRESHOLD = 10_000_000_000_000
MICROSECONDS_THRESHOLD = 10_000_000_000_000_000

QUALITY_VERDICTS = frozenset(
    {
        "STRICT_COMPLETE",
        "COMPLETE_WITH_DOCUMENTED_ANOMALIES",
        "PARTIAL_USABLE",
        "SOURCE_INVALID",
        "SOURCE_UNAVAILABLE",
        "CHECKSUM_FAILED",
    }
)


class HistoricalProbeError(ValueError):
    """Fail-closed historical probe error."""


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
    close_ts_ms: int | None = None
    taker_buy_base_volume: str | None = None
    taker_buy_quote_volume: str | None = None
    extra_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
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
        if self.close_ts_ms is not None:
            payload["close_ts_ms"] = self.close_ts_ms
        if self.taker_buy_base_volume is not None:
            payload["taker_buy_base_volume"] = self.taker_buy_base_volume
        if self.taker_buy_quote_volume is not None:
            payload["taker_buy_quote_volume"] = self.taker_buy_quote_volume
        return payload


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
        raise HistoricalProbeError(f"Invalid month: {month}")
    start_dt = datetime(year, month, 1, tzinfo=UTC)
    last_day = calendar.monthrange(year, month)[1]
    end_dt = datetime(year, month, last_day, 23, 59, tzinfo=UTC)
    expected = last_day * 24 * 60
    return int(start_dt.timestamp() * 1000), int(end_dt.timestamp() * 1000), expected


def parse_year_month(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d{4})-(\d{2})", value)
    if not match:
        raise HistoricalProbeError(
            f"Invalid YYYY-MM month label: {value!r}. Expected e.g. 2026-06."
        )
    return int(match.group(1)), int(match.group(2))


def detect_timestamp_unit(raw: str | int) -> str:
    value = int(str(raw).strip())
    if value < 0:
        raise HistoricalProbeError(f"Negative timestamp: {value}")
    if value < SECONDS_THRESHOLD:
        return "seconds"
    if value < MILLISECONDS_THRESHOLD:
        return "milliseconds"
    if value < MICROSECONDS_THRESHOLD:
        return "microseconds"
    raise HistoricalProbeError(f"Unplausible timestamp magnitude: {value}")


def normalize_timestamp_to_ms(raw: str | int, *, unit: str | None = None) -> int:
    value = int(str(raw).strip())
    resolved = unit or detect_timestamp_unit(value)
    if resolved == "seconds":
        return value * 1000
    if resolved == "milliseconds":
        return value
    if resolved == "microseconds":
        return value // 1000
    raise HistoricalProbeError(f"Unsupported timestamp unit: {resolved}")


def decimal_str(raw: str | None) -> str:
    if raw is None or raw == "":
        raise HistoricalProbeError("Missing decimal field")
    try:
        return format(Decimal(raw), "f")
    except (InvalidOperation, ValueError) as exc:
        raise HistoricalProbeError(f"Invalid decimal value: {raw!r}") from exc


def _decode_payload(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HistoricalProbeError("Download payload is not valid UTF-8 text")


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
        timeout: float = 120.0,
        max_retries: int = 3,
        user_agent: str = "CDB-Historical-Probe/1.0",
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent
        self._opener = opener or urllib.request.urlopen

    def fetch_text(self, url: str) -> str:
        body, headers = self._fetch(url)
        content_type = headers.get("content-type", "")
        if "text/html" in content_type.lower():
            raise HistoricalProbeError(f"Refusing HTML payload from {url}")
        text = _decode_payload(body)
        if _looks_like_html(text) or _looks_like_login(text):
            raise HistoricalProbeError(f"Refusing non-data payload from {url}")
        return text

    def fetch_json(self, url: str) -> Any:
        text = self.fetch_text(url)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise HistoricalProbeError(f"Invalid JSON from {url}: {exc}") from exc

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
                raise HistoricalProbeError(
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
            raise HistoricalProbeError(
                f"Refusing HTML market-data payload from {url}"
            )
        text_probe = body[:512].decode("utf-8", errors="ignore")
        if _looks_like_html(text_probe) or _looks_like_login(text_probe):
            raise HistoricalProbeError(
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
            raise HistoricalProbeError(
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
                headers={"User-Agent": self.user_agent},
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
                    time.sleep(min(2**attempt, 8))
                    continue
                raise HistoricalProbeError(
                    f"HTTP {exc.code} while fetching {url}"
                ) from exc
            except (urllib.error.URLError, OSError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 8))
                    continue
                raise HistoricalProbeError(
                    f"Network error while fetching {url}: {exc}"
                ) from exc
        raise HistoricalProbeError(f"Failed to fetch {url}: {last_error}")


def inspect_archive(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if any(name.startswith("/") or ".." in Path(name).parts for name in names):
                raise HistoricalProbeError(
                    f"Unsafe archive traversal detected in {path}"
                )
            return {"archive_format": "zip", "member_files": names}
    if suffix in {".csv", ".json", ".jsonl"}:
        return {"archive_format": suffix.lstrip("."), "member_files": [path.name]}
    raise HistoricalProbeError(f"Unknown archive/data format: {path}")


def extract_zip_csv(path: Path) -> tuple[Path, bytes]:
    meta = inspect_archive(path)
    if meta["archive_format"] != "zip":
        raise HistoricalProbeError(f"Expected zip archive: {path}")
    with zipfile.ZipFile(path) as archive:
        csv_members = [name for name in archive.namelist() if name.endswith(".csv")]
        if not csv_members:
            raise HistoricalProbeError(f"No CSV member in archive {path}")
        member = csv_members[0]
        return Path(member), archive.read(member)


def parse_official_checksum(text: str, *, expected_filename: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        digest, filename = parts[0], parts[-1]
        if filename != expected_filename:
            continue
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise HistoricalProbeError(
                f"Invalid checksum digest in official file: {digest!r}"
            )
        return digest
    raise HistoricalProbeError(
        f"No checksum entry found for {expected_filename!r} in official checksum file"
    )


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
        if candle.trade_count is not None and candle.trade_count < 0:
            anomalies.append(f"negative_trade_count@{candle.ts_ms}")
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
        raise HistoricalProbeError(f"Invalid quality verdict: {verdict}")
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


def write_jsonl_and_hash(path: Path, rows: Sequence[dict[str, Any]]) -> str:
    """Write JSONL and return SHA-256 without loading entire file back."""
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            line = json.dumps(row, ensure_ascii=False) + "\n"
            digest.update(line.encode("utf-8"))
            handle.write(line)
    return digest.hexdigest()


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
    rest_base: str,
    interval: str = "1m",
    limit: int = 5,
) -> dict[str, Any]:
    candle_map = {candle.ts_ms: candle for candle in candles}
    comparisons: list[dict[str, Any]] = []
    for start_ts in sample_points:
        url = (
            f"{rest_base.rstrip('/')}/api/v3/klines?"
            f"{urllib.parse.urlencode({'symbol': symbol, 'interval': interval, 'startTime': start_ts, 'limit': limit})}"
        )
        try:
            payload = fetcher.fetch_json(url)
        except HistoricalProbeError as exc:
            comparisons.append(
                {
                    "start_ts_ms": start_ts,
                    "status": "retention_unavailable",
                    "error": str(exc),
                }
            )
            continue
        if not isinstance(payload, list) or not payload:
            comparisons.append(
                {
                    "start_ts_ms": start_ts,
                    "status": "retention_unavailable",
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
                    {
                        "ts_ms": ts_ms,
                        "open": "not_available",
                        "close": "not_available",
                    }
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
                        archive.quote_volume or "",
                        str(raw[7]) if len(raw) > 7 else "",
                    ),
                    "trade_count": _compare_field(
                        str(archive.trade_count) if archive.trade_count is not None else "",
                        str(raw[8]) if len(raw) > 8 else "",
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
