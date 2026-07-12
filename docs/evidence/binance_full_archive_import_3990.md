# Binance Full Archive Import — Issue #3990

**Date:** 2026-07-12  
**Issue:** [#3990](https://github.com/jannekbuengener/Claire_de_Binare/issues/3990)  
**Human-GO:** `HISTORICAL-DATA-GO #3990 Binance BTCUSDT 1m full archive import`  
**LR:** NO-GO (unchanged)  
**Final status:** `FULL_IMPORT_PARTIAL`

---

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `context_tool_status` | `available` |
| `context_trust_level` | `none` |
| `records_found` | `none` |
| `repo_fallback_reason` | `insufficient_evidence` |

---

## Import Range (official listing)

| Field | Value |
|-------|-------|
| Earliest available | `2017-08` |
| Last complete | `2026-06` |
| Month count (listed) | `107` |
| Source | `https://data.binance.vision` (S3 listing + official `.CHECKSUM`) |

---

## Import Status (runtime 2026-07-12)

| Metric | Value |
|--------|-------|
| `import_status` | `FULL_IMPORT_PARTIAL` |
| STRICT_COMPLETE | 81 |
| PARTIAL_USABLE | 26 |
| Failed | 0 |
| Total candles | 4,656,799 |
| Earliest ts | 2017-10-01 (first strict-complete month) |
| Latest ts | 2026-06-30 |
| Raw storage | ~229 MB |
| Normalized storage | ~2.38 GB |
| Enriched storage | ~1.88 GB |

**PARTIAL_USABLE months** (26): early-history months with documented calendar gaps (e.g. `2017-08` partial listing start, leap-year February edge cases). Excluded from window bank; not silently repaired.

Manifest: `artifacts/market_data/manifests/binance_btcusdt_1m_full_import.json`

---

## Checksums

All downloaded months: official `.CHECKSUM` verified before normalization. No `CHECKSUM_FAILED` in final manifest.

---

## Regime Plausibility

| Check | Result |
|-------|--------|
| Carry-over across months | enabled (`assign_regime_ids_with_state`) |
| Threshold mirror | `services/regime/service.py` + `REGIME_ATR_HIGH_VOL_THRESHOLD=2.0` |
| `regime_plausibility.status` | `PASS_WITH_CAVEAT` |
| `regime_plausibility.blocking` | `false` |
| HIGH_VOL_CHAOTIC share (sample) | ~99.5% |
| Finding | Absolute ATR threshold 2.0 on BTC (~7k USD) → contract-consistent HIGH_VOL_CHAOTIC dominance; not a normalization defect |

Replay campaign **not blocked** by regime contract.

---

## Window Bank

| Class | Count |
|-------|-------|
| monthly | 81 |
| quarterly | 19 |
| yearly | 3 |
| stress | 3 |
| **Total deduplicated** | **106** |

Temporal split: development (early) / validation (middle) / out-of-sample (≥20% latest strict-complete months).

Manifest: `artifacts/market_data/window_bank/binance/spot/BTCUSDT/1m/window_bank_manifest.json`

---

## Cross-Venue Boundaries

Binance data is **historical_cross_venue_research** only. Not MEXC same-venue, not paper/live promotion evidence.

---

## Validation

```bash
pytest -q tests/unit/market_data/test_binance_full_archive_import.py tests/unit/market_data/test_binance_window_bank.py
python -m tools.market_data.binance_full_archive_import --list-months
python -m tools.market_data.binance_full_archive_import --smoke-replay --smoke-month 2026-06
```

Smoke replay 2026-06: **PASS** (donchian_breakout_v1, breakout_trend_filter_v1, primary_breakout_v1 × 3 scenarios).

---

## Disk

Artifacts relocated to `E:\CDB_artifacts` via junction (`artifacts` → E:). D: freed ~14 GB before import.
