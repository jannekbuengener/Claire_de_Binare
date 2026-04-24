"""Fail-closed candle continuity gate and historical backfill CLI for ARVP.

Issue #1906 scope:
  - Check whether public.candles_1m covers a replay window plus warmup at exact
    1m cadence.
  - Backfill missing candles from a real historical source with provenance.

This script does not synthesize candles and does not soften replay contracts.
"""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from psycopg2.extras import Json

from core.utils.postgres_client import create_postgres_connection

ONE_MINUTE_MS = 60_000
CONTINUITY_CONTRACT_VERSION = "cdb_candle_continuity_check.v1"
BACKFILL_CONTRACT_VERSION = "cdb_candle_backfill_import.v1"
DEFAULT_BINANCE_BASE_URL = "https://api.binance.com"


class CandleContinuityError(ValueError):
    """Raised when candle continuity input or source data is invalid."""


@dataclass(frozen=True, slots=True)
class CandleRow:
    symbol: str
    ts_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    trade_count: int

    def stable_dict(self) -> dict[str, Any]:
        return {
            "close": str(self.close),
            "high": str(self.high),
            "low": str(self.low),
            "open": str(self.open),
            "symbol": self.symbol,
            "trade_count": self.trade_count,
            "ts_ms": self.ts_ms,
            "volume": str(self.volume),
        }


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _require_symbol(value: str) -> str:
    symbol = str(value or "").strip().upper()
    if not symbol:
        raise CandleContinuityError("symbol must be a non-empty string")
    return symbol


def _require_positive_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CandleContinuityError(f"{field_name} must be a positive integer")
    return value


def expected_timestamps(
    *,
    start_ts_ms: int,
    end_ts_ms: int,
    warmup_candles: int,
) -> list[int]:
    """Return the exact 1m timestamps required by a replay window."""
    _require_positive_int(start_ts_ms, "start_ts_ms")
    _require_positive_int(end_ts_ms, "end_ts_ms")
    if start_ts_ms > end_ts_ms:
        raise CandleContinuityError("start_ts_ms must be <= end_ts_ms")
    if isinstance(warmup_candles, bool) or warmup_candles < 0:
        raise CandleContinuityError("warmup_candles must be >= 0")
    if start_ts_ms % ONE_MINUTE_MS != 0 or end_ts_ms % ONE_MINUTE_MS != 0:
        raise CandleContinuityError("start_ts_ms and end_ts_ms must be 1m-aligned")
    warmup_start = start_ts_ms - warmup_candles * ONE_MINUTE_MS
    if warmup_start <= 0:
        raise CandleContinuityError("warmup window starts before epoch")
    return list(range(warmup_start, end_ts_ms + ONE_MINUTE_MS, ONE_MINUTE_MS))


def collapse_missing_timestamps(missing: Sequence[int]) -> list[dict[str, Any]]:
    """Collapse sorted missing timestamps into contiguous gap ranges."""
    if not missing:
        return []
    sorted_missing = sorted(int(x) for x in missing)
    gaps: list[dict[str, Any]] = []
    start = prev = sorted_missing[0]
    count = 1
    timestamps = [start]
    for ts_ms in sorted_missing[1:]:
        if ts_ms == prev + ONE_MINUTE_MS:
            count += 1
            timestamps.append(ts_ms)
            prev = ts_ms
            continue
        gaps.append(
            {
                "start_ts_ms": start,
                "end_ts_ms": prev,
                "missing_count": count,
                "timestamps": timestamps,
            }
        )
        start = prev = ts_ms
        count = 1
        timestamps = [ts_ms]
    gaps.append(
        {
            "start_ts_ms": start,
            "end_ts_ms": prev,
            "missing_count": count,
            "timestamps": timestamps,
        }
    )
    return gaps


def build_continuity_report(
    *,
    symbol: str,
    start_ts_ms: int,
    end_ts_ms: int,
    warmup_candles: int,
    observed_ts_ms: Sequence[int],
) -> dict[str, Any]:
    """Build a machine-readable continuity report from observed DB timestamps."""
    resolved_symbol = _require_symbol(symbol)
    expected = expected_timestamps(
        start_ts_ms=start_ts_ms,
        end_ts_ms=end_ts_ms,
        warmup_candles=warmup_candles,
    )
    observed = {int(ts) for ts in observed_ts_ms}
    missing = [ts for ts in expected if ts not in observed]
    stable_payload = {
        "contract_version": CONTINUITY_CONTRACT_VERSION,
        "effective_window": {
            "end_ts_ms": end_ts_ms,
            "start_ts_ms": expected[0],
        },
        "expected_candles": len(expected),
        "gaps": collapse_missing_timestamps(missing),
        "missing_count": len(missing),
        "observed_candles": len([ts for ts in expected if ts in observed]),
        "requested_window": {
            "end_ts_ms": end_ts_ms,
            "start_ts_ms": start_ts_ms,
            "warmup_candles": warmup_candles,
        },
        "replay_ready": not missing,
        "source_table": "public.candles_1m",
        "symbol": resolved_symbol,
    }
    return {
        **stable_payload,
        "checked_at_utc": _utc_now_iso(),
        "continuity_fingerprint": _canonical_hash(stable_payload),
    }


def query_observed_timestamps(
    conn,
    *,
    symbol: str,
    required_start_ts_ms: int,
    end_ts_ms: int,
) -> list[int]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ts_ms
            FROM public.candles_1m
            WHERE symbol = %s
              AND ts_ms >= %s
              AND ts_ms <= %s
            ORDER BY ts_ms ASC
            """,
            (symbol, required_start_ts_ms, end_ts_ms),
        )
        return [int(row[0]) for row in cur.fetchall()]


def run_check_window(
    *,
    symbol: str,
    start_ts_ms: int,
    end_ts_ms: int,
    warmup_candles: int,
    output: Path | None,
) -> dict[str, Any]:
    expected = expected_timestamps(
        start_ts_ms=start_ts_ms,
        end_ts_ms=end_ts_ms,
        warmup_candles=warmup_candles,
    )
    conn = create_postgres_connection()
    try:
        observed = query_observed_timestamps(
            conn,
            symbol=_require_symbol(symbol),
            required_start_ts_ms=expected[0],
            end_ts_ms=end_ts_ms,
        )
    finally:
        conn.close()
    report = build_continuity_report(
        symbol=symbol,
        start_ts_ms=start_ts_ms,
        end_ts_ms=end_ts_ms,
        warmup_candles=warmup_candles,
        observed_ts_ms=observed,
    )
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def parse_binance_kline(symbol: str, raw: Sequence[Any]) -> CandleRow:
    """Parse one Binance spot kline row into the candles_1m shape."""
    if len(raw) < 9:
        raise CandleContinuityError("Binance kline row has fewer than 9 fields")
    ts_ms = int(raw[0])
    if ts_ms <= 0 or ts_ms % ONE_MINUTE_MS != 0:
        raise CandleContinuityError(f"Binance kline open time is not 1m-aligned: {ts_ms}")
    row = CandleRow(
        symbol=_require_symbol(symbol),
        ts_ms=ts_ms,
        open=Decimal(str(raw[1])),
        high=Decimal(str(raw[2])),
        low=Decimal(str(raw[3])),
        close=Decimal(str(raw[4])),
        volume=Decimal(str(raw[5])),
        trade_count=int(raw[8]),
    )
    if row.open <= 0 or row.high <= 0 or row.low <= 0 or row.close <= 0:
        raise CandleContinuityError("Binance kline contains non-positive OHLC")
    if row.high < row.low:
        raise CandleContinuityError("Binance kline high is below low")
    if row.volume < 0 or row.trade_count < 0:
        raise CandleContinuityError("Binance kline contains negative volume/trade_count")
    return row


def candle_rows_checksum(rows: Sequence[CandleRow]) -> str:
    payload = [row.stable_dict() for row in sorted(rows, key=lambda r: (r.symbol, r.ts_ms))]
    return _canonical_hash(payload)


def fetch_binance_klines(
    *,
    symbol: str,
    start_ts_ms: int,
    end_ts_ms: int,
    base_url: str = DEFAULT_BINANCE_BASE_URL,
) -> tuple[list[CandleRow], list[str]]:
    """Fetch real 1m klines from Binance spot REST API."""
    resolved_symbol = _require_symbol(symbol)
    expected = expected_timestamps(
        start_ts_ms=start_ts_ms,
        end_ts_ms=end_ts_ms,
        warmup_candles=0,
    )
    current = expected[0]
    rows: list[CandleRow] = []
    requested_urls: list[str] = []
    while current <= end_ts_ms:
        params = {
            "endTime": end_ts_ms + ONE_MINUTE_MS - 1,
            "interval": "1m",
            "limit": 1000,
            "startTime": current,
            "symbol": resolved_symbol,
        }
        url = f"{base_url.rstrip('/')}/api/v3/klines?{urllib.parse.urlencode(params)}"
        requested_urls.append(url)
        with urllib.request.urlopen(url, timeout=20) as response:
            body = response.read().decode("utf-8")
        raw_rows = json.loads(body)
        if not isinstance(raw_rows, list):
            raise CandleContinuityError("Binance response root is not an array")
        if not raw_rows:
            break
        parsed = [parse_binance_kline(resolved_symbol, raw) for raw in raw_rows]
        rows.extend(row for row in parsed if start_ts_ms <= row.ts_ms <= end_ts_ms)
        last_ts = int(parsed[-1].ts_ms)
        if last_ts < current:
            raise CandleContinuityError("Binance response did not advance")
        current = last_ts + ONE_MINUTE_MS
        if len(raw_rows) < 1000:
            break
    rows = sorted({row.ts_ms: row for row in rows}.values(), key=lambda row: row.ts_ms)
    fetched_ts = {row.ts_ms for row in rows}
    missing = [ts for ts in expected if ts not in fetched_ts]
    if missing:
        raise CandleContinuityError(
            "historical source did not return full requested 1m window: "
            f"missing={missing}"
        )
    return rows, requested_urls


def insert_candles(conn, rows: Sequence[CandleRow]) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    with conn.cursor() as cur:
        for row in rows:
            cur.execute(
                """
                INSERT INTO public.candles_1m
                    (symbol, ts_ms, open, high, low, close, volume, trade_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, ts_ms) DO NOTHING
                """,
                (
                    row.symbol,
                    row.ts_ms,
                    row.open,
                    row.high,
                    row.low,
                    row.close,
                    row.volume,
                    row.trade_count,
                ),
            )
            if cur.rowcount == 1:
                inserted += 1
            else:
                skipped += 1
    return inserted, skipped


def record_backfill_provenance(conn, manifest: dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.candle_backfill_imports
                (
                    import_id,
                    source,
                    source_url,
                    import_command,
                    imported_at,
                    symbol,
                    start_ts_ms,
                    end_ts_ms,
                    row_count,
                    inserted_count,
                    skipped_existing_count,
                    checksum_sha256,
                    payload
                )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (import_id) DO NOTHING
            """,
            (
                manifest["import_id"],
                manifest["source"],
                manifest["source_url"],
                manifest["import_command"],
                manifest["imported_at_utc"],
                manifest["symbol"],
                manifest["window"]["start_ts_ms"],
                manifest["window"]["end_ts_ms"],
                manifest["row_count"],
                manifest["inserted_count"],
                manifest["skipped_existing_count"],
                manifest["checksum_sha256"],
                Json(manifest),
            ),
        )


def build_backfill_manifest(
    *,
    source: str,
    source_urls: Sequence[str],
    import_command: str,
    symbol: str,
    start_ts_ms: int,
    end_ts_ms: int,
    rows: Sequence[CandleRow],
    inserted_count: int,
    skipped_existing_count: int,
) -> dict[str, Any]:
    checksum = candle_rows_checksum(rows)
    stable = {
        "checksum_sha256": checksum,
        "contract_version": BACKFILL_CONTRACT_VERSION,
        "import_command": import_command,
        "row_count": len(rows),
        "source": source,
        "source_url": "\n".join(source_urls),
        "symbol": _require_symbol(symbol),
        "window": {
            "end_ts_ms": end_ts_ms,
            "start_ts_ms": start_ts_ms,
        },
    }
    return {
        **stable,
        "import_id": str(uuid.uuid5(uuid.NAMESPACE_URL, _canonical_hash(stable))),
        "imported_at_utc": _utc_now_iso(),
        "inserted_count": inserted_count,
        "rows": [row.stable_dict() for row in rows],
        "skipped_existing_count": skipped_existing_count,
    }


def run_backfill_binance(
    *,
    symbol: str,
    start_ts_ms: int,
    end_ts_ms: int,
    provenance_out: Path,
    apply: bool,
    base_url: str,
) -> dict[str, Any]:
    rows, urls = fetch_binance_klines(
        symbol=symbol,
        start_ts_ms=start_ts_ms,
        end_ts_ms=end_ts_ms,
        base_url=base_url,
    )
    inserted = 0
    skipped = 0
    if apply:
        conn = create_postgres_connection()
        try:
            inserted, skipped = insert_candles(conn, rows)
            manifest = build_backfill_manifest(
                source="binance_spot_api_v3_klines",
                source_urls=urls,
                import_command=" ".join(sys.argv),
                symbol=symbol,
                start_ts_ms=start_ts_ms,
                end_ts_ms=end_ts_ms,
                rows=rows,
                inserted_count=inserted,
                skipped_existing_count=skipped,
            )
            record_backfill_provenance(conn, manifest)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        manifest = build_backfill_manifest(
            source="binance_spot_api_v3_klines",
            source_urls=urls,
            import_command=" ".join(sys.argv),
            symbol=symbol,
            start_ts_ms=start_ts_ms,
            end_ts_ms=end_ts_ms,
            rows=rows,
            inserted_count=0,
            skipped_existing_count=0,
        )
    provenance_out.parent.mkdir(parents=True, exist_ok=True)
    provenance_out.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="candle_continuity",
        description="Check ARVP candle continuity and backfill real historical 1m candles.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check-window", help="Check public.candles_1m continuity.")
    check.add_argument("--symbol", required=True)
    check.add_argument("--start-ts-ms", required=True, type=int)
    check.add_argument("--end-ts-ms", required=True, type=int)
    check.add_argument("--warmup-candles", required=True, type=int)
    check.add_argument("--output", type=Path, default=None)

    backfill = sub.add_parser("backfill-binance", help="Backfill from Binance real 1m klines.")
    backfill.add_argument("--symbol", required=True)
    backfill.add_argument("--start-ts-ms", required=True, type=int)
    backfill.add_argument("--end-ts-ms", required=True, type=int)
    backfill.add_argument("--provenance-out", required=True, type=Path)
    backfill.add_argument("--base-url", default=DEFAULT_BINANCE_BASE_URL)
    backfill.add_argument("--apply", action="store_true", help="Insert rows and record DB provenance.")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    try:
        if args.command == "check-window":
            report = run_check_window(
                symbol=args.symbol,
                start_ts_ms=args.start_ts_ms,
                end_ts_ms=args.end_ts_ms,
                warmup_candles=args.warmup_candles,
                output=args.output,
            )
            print(json.dumps(report, sort_keys=True))
            return 0 if report["replay_ready"] else 2
        if args.command == "backfill-binance":
            manifest = run_backfill_binance(
                symbol=args.symbol,
                start_ts_ms=args.start_ts_ms,
                end_ts_ms=args.end_ts_ms,
                provenance_out=args.provenance_out,
                apply=bool(args.apply),
                base_url=str(args.base_url),
            )
            print(json.dumps(manifest, sort_keys=True))
            return 0
    except CandleContinuityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    parser.error(f"unknown command {args.command!r}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
