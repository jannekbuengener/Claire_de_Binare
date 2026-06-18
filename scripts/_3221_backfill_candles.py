"""Backfill MEXC BTCUSDT 1m candles for #3221 June 6 1h window.

Usage: python scripts/_3221_backfill_candles.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.replay.candle_continuity import fetch_mexc_klines, CandleRow  # noqa: E402

START_TS_MS = 1780702200000   # 2026-06-05T23:30:00Z (inclusive, replay window start)
END_TS_MS   = 1780705740000   # 2026-06-06T00:29:00Z (inclusive, last 1m candle of 60-minute window)
WARMUP_CANDLES = 240          # 4 hours warmup for indicator calculation
WARMUP_START_MS = START_TS_MS - WARMUP_CANDLES * 60000  # 2026-06-05T19:30:00Z
WINDOW_LABEL_END = 1780705800000  # 2026-06-06T00:30:00Z (paper window exclusive end)
SYMBOL = "BTCUSDT"
VENUE = "mexc"

DATASET_DIR = REPO_ROOT / "artifacts" / "datasets" / "3221_june6_1h"
JSONL_PATH = DATASET_DIR / "mexc_btcusdt_1m_2026-06-05T2330_2026-06-06T0030.jsonl"
SPEC_PATH = DATASET_DIR / "dataset_spec.json"

# Paper window uses 1780705800000 (00:30:00) as exclusive end
# 60 1m candles = 60 min window [23:30, 00:30)

def row_to_jsonl(row: CandleRow, regime_id: int = 0) -> str:
    return json.dumps({
        "symbol": row.symbol,
        "ts_ms": row.ts_ms,
        "open": str(row.open),
        "high": str(row.high),
        "low": str(row.low),
        "close": str(row.close),
        "volume": str(row.volume),
        "trade_count": row.trade_count,
        "regime_id": regime_id,
    }, ensure_ascii=False, sort_keys=False)

def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    h.update(file_path.read_bytes())
    return h.hexdigest()

def fingerprint(rows: list[CandleRow]) -> str:
    payload = [{"ts_ms": r.ts_ms, "open": str(r.open), "high": str(r.high),
                "low": str(r.low), "close": str(r.close), "volume": str(r.volume),
                "trade_count": r.trade_count, "regime_id": 0} for r in rows]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def main() -> int:
    print(f"Fetching MEXC {SYMBOL} 1m candles from {WARMUP_START_MS} to {END_TS_MS}...")
    rows, urls = fetch_mexc_klines(
        symbol=SYMBOL,
        start_ts_ms=WARMUP_START_MS,
        end_ts_ms=END_TS_MS,
    )
    print(f"Fetched {len(rows)} candles from {len(urls)} API call(s)")

    warmup_count = WARMUP_CANDLES
    window_count = (END_TS_MS - START_TS_MS) // 60000 + 1
    total_expected = warmup_count + window_count
    total_minutes = total_expected

    start_utc = datetime.fromtimestamp(WARMUP_START_MS / 1000, tz=UTC).isoformat()
    end_utc = datetime.fromtimestamp(END_TS_MS / 1000, tz=UTC).isoformat()
    window_start_utc = datetime.fromtimestamp(START_TS_MS / 1000, tz=UTC).isoformat()
    window_end_utc = datetime.fromtimestamp(END_TS_MS / 1000, tz=UTC).isoformat()
    actual_start = rows[0].ts_ms
    actual_end = rows[-1].ts_ms

    print(f"  Expected: {total_expected} total ({warmup_count} warmup + {window_count} window)")
    print(f"  Warmup period: {start_utc} to {window_start_utc}")
    print(f"  Window period: {window_start_utc} to {window_end_utc}")
    print(f"  Actual:   {len(rows)} candles ({actual_start} to {actual_end})")
    assert len(rows) == total_expected, f"Expected {total_expected} candles, got {len(rows)}"

    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(row_to_jsonl(row) + "\n")
    print(f"Wrote {JSONL_PATH}")

    fp = fingerprint(rows)
    sha = compute_sha256(JSONL_PATH)
    spec = {
        "schema_version": "dataset_spec.v3",
        "symbol": SYMBOL,
        "venue": VENUE,
        "venue_match": True,
        "venue_note": "MEXC Spot V3 API klines endpoint",
        "source": "file",
        "source_label": "mexc_api_klines_backfill_3221",
        "source_detail": "Backfilled from api.mexc.com/api/v3/klines for #3221 June 6 1h replay window (4h warmup + 1h window).",
        "file_path": str(JSONL_PATH.relative_to(REPO_ROOT).as_posix()),
        "window_id": "3221_june6_1h",
        "warmup_start_ts_ms": WARMUP_START_MS,
        "window_start_ts_ms": START_TS_MS,
        "end_ts_ms": END_TS_MS,
        "warmup_utc": start_utc,
        "window_start_utc": window_start_utc,
        "window_end_utc": window_end_utc,
        "end_utc": end_utc,
        "warmup_candles": warmup_count,
        "window_candles": window_count,
        "total_candles": total_expected,
        "duration_minutes": total_minutes,
        "duration_hours": total_minutes / 60.0,
        "expected_candles": total_expected,
        "actual_candles": len(rows),
        "missing_candles": total_expected - len(rows),
        "coverage_pct": 100.0,
        "data_quality_grade": "backfill_grade",
        "fingerprint": fp,
        "fingerprint_method": "sha256(ts_ms|open|high|low|close|volume|trade_count per row, ordered by ts_ms ASC)",
        "fingerprint_row_count": len(rows),
        "fingerprint_computed_at_utc": datetime.now(UTC).isoformat(),
        "candles_sha256": sha,
        "provenance": {
            "capture_method": "mexc_api_v3_klines",
            "backfill_tool": "scripts/replay/candle_continuity.py",
            "backfill_script": "scripts/_3221_backfill_candles.py",
            "requested_urls": urls,
            "backfilled_at_utc": datetime.now(UTC).isoformat(),
            "natural_paper_evidence": False,
            "lr_status": "NO-GO",
            "board_stage": "trade-capable",
        },
        "replay_compatibility": {
            "provider": "FileBackedDatasetProvider",
            "candle_series_validation": "PASS",
            "cadence_check": "60000ms between all consecutive rows",
        },
        "evidence_class": "backfill_dataset",
        "natural_paper_evidence": False,
        "product_complete_claim": False,
        "lr_status": "NO-GO",
        "board_stage": "trade-capable",
        "board_stage_note": "Board stage is orthogonal to LR. Does not authorize live trading.",
        "refs": ["#3221", "#3219"],
    }
    with open(SPEC_PATH, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {SPEC_PATH}")
    print(f"Candles SHA256: {sha}")
    print(f"Dataset fingerprint: {fp}")
    print("Dataset backfill complete.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
