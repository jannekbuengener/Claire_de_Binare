# ARVP Binance Historical Import Runbook (#3990)

**Issue:** [#3990](https://github.com/jannekbuengener/Claire_de_Binare/issues/3990)  
**LR:** NO-GO — cross-venue research only, not MEXC same-venue evidence.

---

## Prerequisites

- Explicit Human-GO: `HISTORICAL-DATA-GO #3990 Binance BTCUSDT 1m full archive import`
- Free disk: ≥ 5 GB recommended (raw + normalized + enriched + replay artifacts)
- Network access to `data.binance.vision` (official S3 listing + archives)
- No Docker trading services required (offline replay only)

---

## Phase 1 — Discover Range

```bash
python -m tools.market_data.binance_full_archive_import --list-months
```

Expected: earliest month from official listing (typically `2017-08`), last complete month excludes current calendar month.

---

## Phase 2 — Full Archive Import

```bash
python -m tools.market_data.binance_full_archive_import
```

Artifacts:

| Layer | Path |
|-------|------|
| Raw | `artifacts/market_data/raw/binance/spot/BTCUSDT/1m/<YYYY-MM>/` |
| Normalized | `artifacts/market_data/normalized/binance/spot/BTCUSDT/1m/<YYYY-MM>/` |
| Enriched | `artifacts/market_data/enriched/binance/spot/BTCUSDT/1m/<YYYY-MM>/` |
| Manifest | `artifacts/market_data/manifests/binance_btcusdt_1m_full_import.json` |

Resume: idempotent — existing valid files are not overwritten on hash conflict.

---

## Phase 3 — Regime Plausibility

Regime enrichment uses carry-over state across months (`assign_regime_ids_with_state`).

If `regime_plausibility.blocking=true` in import manifest → **stop**, do not start replay campaign.

Known caveat: `ATR_HIGH_VOL_THRESHOLD=2.0` (absolute units) mirrors runtime compose; BTC 1m ATR >> 2 → HIGH_VOL_CHAOTIC dominance. Document, do not silently repair.

---

## Phase 4 — Window Bank

```bash
python -m tools.market_data.binance_window_bank --build-bank --vacation-manifest
```

Window classes: monthly, quarterly (non-overlapping), yearly (complete years), stress (deduplicated).

Temporal split: development (early) / validation (middle) / out-of-sample (≥20% latest).

---

## Phase 5 — Replay Campaign (ordered)

1. Smoke:

```bash
python -m tools.market_data.binance_full_archive_import --smoke-replay --smoke-month 2026-06
```

2. Pilot manifest:

```bash
python -m tools.market_data.binance_window_bank --pilot-manifest
python -m tools.arvp_vacation.coordinator --manifest artifacts/arvp_vacation/manifests/binance_historical_campaign_3990.yaml --preflight-only
```

3. Full campaign:

```bash
python -m tools.market_data.binance_window_bank --run-campaign --manifest-path artifacts/arvp_vacation/manifests/binance_historical_campaign_3990.yaml
```

---

## Evidence Outputs

- `docs/evidence/binance_full_archive_import_3990.md`
- `docs/evidence/arvp_binance_historical_campaign_3990.md`
- `artifacts/arvp_vacation/<campaign_id>/vacation_summary.json`

---

## Cross-Venue Boundaries

| Allowed | Forbidden |
|---------|-----------|
| `historical_cross_venue_research` | `mexc_same_venue` |
| `controlled_lab_evidence` | `natural_paper_evidence` |
| `venue=binance` | `live_evidence`, `promotion_ready` |
| `ranking_ready=false` | LR upgrade, paper/live go |

---

## Stop Rules

- Checksum failure → month isolated, campaign may continue with honest partial status
- Disk below `min_free_disk_gb` → fatal stop
- Regime contract blocking → `FULL_IMPORT_PARTIAL_REGIME_BLOCKED`
- Smoke/pilot FAIL → do not start full bank campaign
