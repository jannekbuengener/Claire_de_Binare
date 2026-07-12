# Binance Full Archive Import — Issue #3990

**Date:** 2026-07-12  
**Issue:** [#3990](https://github.com/jannekbuengener/Claire_de_Binare/issues/3990)  
**Human-GO:** `HISTORICAL-DATA-GO #3990 Binance BTCUSDT 1m full archive import`  
**LR:** NO-GO (unchanged)

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
| Month count | `107` |
| Source | `https://data.binance.vision` (S3 listing + official `.CHECKSUM`) |

---

## Import Status

_See live manifest:_ `artifacts/market_data/manifests/binance_btcusdt_1m_full_import.json`

---

## Regime Plausibility

| Check | Result |
|-------|--------|
| Carry-over across months | enabled |
| Threshold mirror | `services/regime/service.py` + `REGIME_ATR_HIGH_VOL_THRESHOLD=2.0` |
| Blocking defect | _see manifest `regime_plausibility.blocking`_ |

---

## Cross-Venue Boundaries

Binance data is **historical_cross_venue_research** only. Not MEXC same-venue, not paper/live promotion evidence.

---

## Validation

```bash
pytest -q tests/unit/market_data/test_binance_full_archive_import.py tests/unit/market_data/test_binance_window_bank.py
python -m tools.market_data.binance_full_archive_import --list-months
```
