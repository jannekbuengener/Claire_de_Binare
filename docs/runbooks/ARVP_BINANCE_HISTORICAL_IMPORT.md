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

---

## Storage Location & Guard (#4004)

**Canonical path:** `REPO_ROOT/artifacts/market_data` (physically on the repository volume, typically DevDrive `D:`).

Historical full imports are **fail-closed** unless `tools.market_data.market_data_storage_guard` passes:

- Repository and `artifacts/market_data` on the **same volume**
- Volume label matches DevDrive (when resolvable)
- No Reparse Point / Junction / Symlink in the path chain to the target
- Resolved target **not** on blocked external drives (e.g. `E:` Backup II)
- No Removable/Network storage
- Free space ≥ expected write volume × 1.25

**No automatic external-drive fallback.** Imports must not silently redirect to `E:` or other Backup volumes.

`--list-months` and read-only offline reconcile are **not** blocked by the guard.

---

## Offline Reconcile vs Import (#4004)

**Do not** use `binance_full_archive_import --skip-download` as a general read-only manifest rebuild. It may still touch network listing, download fallbacks, and dataset writes.

Use the read-only reconciler instead:

```powershell
python -m tools.market_data.binance_archive_manifest_reconcile `
  --market-data-root "<ROOT>" `
  --output-dir "<OUTPUT_DIR>"
```

Outputs only under `--output-dir`: `reconciled_import_manifest.json`, `reconcile_report.json`, `reconcile_report.md`.

---

## E: → D: Relocation Flow (#4004)

1. **Preflight** — read-only source/destination inventory
2. **Copy** — `robocopy` to `market_data.__incoming_<UTC>` on D: (outside `artifacts` junction)
3. **Verify** — streaming SHA256 source vs staging (`relocate_hash_manifest`)
4. **Reconcile** — offline reconciler on staging copy
5. **Cutover** — break `artifacts` junction; physical `market_data` on D:; per-subtree re-junction for other `E:\CDB_artifacts` content
6. **Rename-test** — rename `E:\CDB_artifacts\market_data` → `market_data.__relocated_verified_<UTC>`; re-run smoke/preflight without E: dependency
7. **Delete** — remove only the renamed verified source folder after all gates PASS

Hash tooling:

```powershell
python -m tools.market_data.relocate_hash_manifest create --root "<ROOT>" --output "<FILE.jsonl>"
python -m tools.market_data.relocate_hash_manifest compare --source "<SRC.jsonl>" --destination "<DST.jsonl>" --output "<COMPARE.json>"
```
