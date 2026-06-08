# ARVP #3083: MEXC Same-Venue Candle Backfill for #3028 Window

**Status:** HOLD_DATA_UNAVAILABLE
**Date:** 2026-06-08
**Author:** Agent

---

## Summary

Attempted to backfill the #3028 paper reference window with real 1m klines from
the MEXC public Spot API (same venue as the original paper trade). MEXC's public
klines endpoint only retains ~2.5 days of 1m candle history — the #3028 window
(2026-06-06) falls outside the available retention window.

**Code delivered:** `scripts/replay/candle_continuity.py` now includes
`parse_mexc_kline`, `fetch_mexc_klines`, `run_backfill_mexc`, and the
`backfill-mexc` CLI subcommand — usable for future windows within MEXC's
retention range.

**No dataset committed.** Per policy: no fake/synthetic/ersatz dataset, no
venue-mismatch substitute.

---

## MEXC Public Klines API

| Field | Value |
|-------|-------|
| Endpoint | `https://api.mexc.com/api/v3/klines` |
| Auth | None (public) |
| Response format | Per-kline array: `[open_time, open, high, low, close, volume, close_time, quote_volume]` (8 fields) |
| `trade_count` | Not available in MEXC klines; defaulted to `0` in parser |

### Retention Window

| Property | Value |
|----------|-------|
| Earliest 1m candle available | ts=1780921620000 (2026-06-08T12:27:00 UTC) |
| Latest 1m candle (at query time) | ts=1780921680000 (2026-06-08T12:28:00 UTC) |
| Approximate retention | ~2.5 days of 1m kline history |
| API reachability | Confirmed (`Status: 200`, valid JSON array) |

---

## Gap Analysis: #3028 Window vs MEXC Retention

| Property | Value |
|----------|-------|
| #3028 window start | 1780691280000 (2026-06-05T20:28:00 UTC) |
| #3028 window end | 1780705860000 (2026-06-06T00:31:00 UTC) |
| Total expected candles | 244 (1m cadence) |
| Earliest MEXC candle | 1780921620000 (2026-06-08T12:27:00 UTC) |
| Gap (window end to earliest MEXC) | 3596 minutes (~60 hours) |
| Verdict | **Window entirely outside MEXC retention — no data available** |

When querying `startTime=1780691280000`, MEXC returns the earliest candle
in its retention (`2026-06-08T12:28:00`), not data for the requested range.
All 244 expected timestamps are missing.

Fetch invoked with:
```
python -m scripts.replay.candle_continuity backfill-mexc \
  --symbol BTCUSDT --start-ts-ms 1780691280000 --end-ts-ms 1780705860000 \
  --provenance-out artifacts/candles/3028_window_mexc/provenance.json
```
Result: `CandleContinuityError` — all 244 timestamps reported as missing.

---

## Code Delivered (Not Data)

The following additions to `scripts/replay/candle_continuity.py` are valid
and remain available for future MEXC-venue windows inside the retention range:

- `parse_mexc_kline(symbol, raw)` — parses 8-field MEXC kline arrays, defaults `trade_count=0`
- `fetch_mexc_klines(symbol, start_ts_ms, end_ts_ms, base_url)` — paginates MEXC public klines with gap detection
- `run_backfill_mexc(...)` — dry-run or apply backfill with provenance manifest
- `backfill-mexc` CLI subcommand — `--symbol`, `--start-ts-ms`, `--end-ts-ms`, `--provenance-out`, `--base-url`, `--apply`

### MEXC Kline Parser Details

| Field | Index | Mapped to |
|-------|-------|-----------|
| open_time | 0 | `CandleRow.ts_ms` |
| open | 1 | `CandleRow.open` |
| high | 2 | `CandleRow.high` |
| low | 3 | `CandleRow.low` |
| close | 4 | `CandleRow.close` |
| volume | 5 | `CandleRow.volume` |
| close_time | 6 | Not mapped (informational only in MEXC) |
| quote_volume | 7 | Not mapped (informational only in MEXC) |
| trade_count | N/A | **Defaulted to 0** (MEXC klines lack this field) |

---

## Key Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| MEXC parser + CLI code | `scripts/replay/candle_continuity.py` | Committed (pending PR) |
| MEXC unit tests | `tests/unit/scripts/test_candle_continuity.py` | Added |
| This evidence document | `docs/evidence/arvp_mexc_backfill_3083.md` | Written |
| MEXC candle dataset | `artifacts/candles/3028_window_mexc/` | **NOT CREATED** (HOLD_DATA_UNAVAILABLE) |

---

## Status for Related Issues

### #3083 (this issue) — HOLD_DATA_UNAVAILABLE
- MEXC code infrastructure delivered (parser, fetcher, CLI)
- MEXC public klines do not retain data for the #3028 window timeframe
- No same-venue dataset can be produced from MEXC's public API at this time
- Future windows within MEXC's ~2.5-day retention range can use this code

### #2971 (trading core confidence) — UNCHANGED
- Same-venue data for #3028 remains unavailable
- LR NO-GO unaffected

### #2974 (product-complete re-assessment)
- No same-venue dataset delivered; Product-Complete status unchanged
- Re-evaluation requires same-venue data or explicit waiver

### #2980 (fill/execution realism fix)
- Re-assessment after venue-matched replay deferred — no same-venue data produced

### #1900 (ARVP venue-matched data blocker)
- Partial progress: MEXC fetch infrastructure exists, but historical range too short
- Blocker remains for pre-2026-06-08 windows

---

## Safety Boundaries

| Boundary | Status |
|----------|--------|
| No live API keys / secrets exposed | Confirmed |
| No DB write (`--apply` omitted) | Confirmed |
| No runtime / Docker stack involvement | Confirmed |
| No Live-Go or Echtgeld | Confirmed (LR NO-GO) |
| No ersatz or synthetic dataset | Confirmed (HOLD, no fake data committed) |
| Public API only | Confirmed (no auth endpoint used) |

---

## Commands Used

```
# Test MEXC API reachability
python -c "import urllib.request,json; d=json.loads(urllib.request.urlopen('https://api.mexc.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=1').read()); print(d[0] if d else 'empty')"

# Attempt backfill (HOLD_DATA_UNAVAILABLE)
python -m scripts.replay.candle_continuity backfill-mexc --symbol BTCUSDT --start-ts-ms 1780691280000 --end-ts-ms 1780705860000 --provenance-out artifacts/candles/3028_window_mexc/provenance.json

# Probe earliest available candle
python -c "import urllib.request,json,datetime; d=json.loads(urllib.request.urlopen('https://api.mexc.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=1').read()); print(d[0][0], datetime.datetime.fromtimestamp(d[0][0]/1000,tz=datetime.timezone.utc).isoformat())"
```
