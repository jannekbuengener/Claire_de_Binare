# Provenance — mexc_strict_window_3091

**Window ID:** `mexc_strict_window_3091_island_3`
**Data Quality Grade:** `strict_campaign_grade`
**Date:** 2026-06-12
**Export Slice:** `#3091 export-first`

## Capture Pipeline

```
MEXC Spot V3 WebSocket (wss://wbs-api.mexc.com/ws)
  → protobuf-decoded public.aggre.deals via Redis PubSub
  → cdb_candles (services/candles/service.py): 1m OHLCV aggregation
  → Redis Stream: stream.candles_1m (maxlen=100000)
  → cdb_db_writer (services/db_writer/db_writer.py:873): _candle_stream_worker
    → Postgres: public.candles_1m (ON CONFLICT (symbol, ts_ms) DO NOTHING)
```

## Source Verification

| Property | Value |
|----------|-------|
| Source type | Real-time MEXC WS, protobuf-decoded aggregated deals |
| Venue | MEXC (same-venue — original paper-trade venue) |
| Symbol | BTCUSDT |
| Cadence | 1-minute OHLCV |
| No backfill | This window contains zero `candle_backfill_imports` rows (DB-verified 2026-06-12) |
| No synthetic | All data originates from real MEXC market activity |

## Window Selection

This window (Island #3) was selected because:

1. **Largest continuous STRICT window** found: 3,496 consecutive minutes (58.3h)
2. **0 gaps** — 100% 1m cadence throughout
3. **Post-#3028** — covers a period after the #3028 reference window (2026-06-06)
4. **Verified active capture** — db_writer logs confirm continuous operation during this period (hourly portfolio snapshots at :43 each hour from Jun 6 13:43 through Jun 8 23:43)
5. **Sufficient for 7 campaign slots** — supports multiple 8h campaign attempts without data degradation

## Deterministic Fingerprint (DB-backed)

SHA-256 fingerprint computed over all 3,496 canonical rows:
- Fields: `ts_ms`, `open`, `high`, `low`, `close`, `volume`, `trade_count`
- Delimiter: `|` (pipe)
- Order: `ts_ms ASC`
- Result: `618064a3ec6f2f4e51f9f3a8a5ba4ccfe30c30d60685e17794d49c11a78b4586`

Reproduce with:
```bash
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -t -A \
  -c "SELECT ts_ms, open, high, low, close, volume, trade_count FROM candles_1m WHERE ts_ms >= 1780753380000 AND ts_ms <= 1780963080000 ORDER BY ts_ms" \
  | python -c "import sys, hashlib; h=hashlib.sha256(); [h.update(line.encode()) for line in sys.stdin if '|' in line]; print(h.hexdigest())"
```

## File-Backed Export (#3091 slice)

| Property | Value |
|----------|-------|
| Export principal | `cdb_readonly` via `POSTGRES_READONLY_PASSWORD_DSN` |
| Export identity | `current_user=cdb_readonly`, `session_user=cdb_readonly` |
| Readonly grant | Applied from PR #3138 (`c69a9a4b`) |
| Export query | `SELECT ... FROM public.candles_1m WHERE symbol='BTCUSDT' AND ts_ms >= 1780753380000 AND ts_ms <= 1780963080000 ORDER BY ts_ms ASC` |
| Export row count | 3496 |
| Export format | JSONL, one candle per line |
| candles.jsonl SHA-256 | `d79a1c3c81191dcf4418ae0c2b2775a6f354ed0cc6801a6955904871c4077605` |
| No runtime capture | No stack, Docker, or WS was started in this slice |
| PRs | #3133 (DB qualification), #3138 (readonly grant contract) |

## Gap Context (Broader 7-Day View)

While this window itself has zero gaps, the surrounding 7-day period (Jun 5–12) contains 3 major gaps indicating stack downtime:

| Gap | Duration | Period (UTC) |
|-----|----------|--------------|
| Gap A | 396 min | Jun 6 07:07 → 13:43 |
| Gap B | 746 min | Jun 8 23:58 → Jun 9 10:45 |
| Gap C | 580 min | Jun 9 22:56 → Jun 10 11:22 |

Gap B is partially evidenced: `docker logs cdb_db_writer` shows a service restart at 2026-06-09 00:00:47 UTC with PostgreSQL initially rejecting connections. Gaps A and C are consistent with stack restart patterns but lack direct log confirmation in this slice.

## Governance

- LR remains **NO-GO**
- Dataset readiness only — NOT natural_paper_evidence
- Cannot satisfy §5.2.4 without a successful natural paper campaign
- No Product-Complete claim
- Board stage `trade-capable` is NOT Live-Go
