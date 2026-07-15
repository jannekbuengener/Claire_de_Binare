# Binance Historical Data Relocation E: → D: — Issue #4004

**Date:** 2026-07-12  
**Issue:** [#4004](https://github.com/jannekbuengener/Claire_de_Binare/issues/4004)  
**Upstream:** [#3990](https://github.com/jannekbuengener/Claire_de_Binare/issues/3990), PR #3997  
**Final status:** `DONE_MERGED_DATA_RELOCATED_E_TO_D`  
**LR:** NO-GO (unchanged)

---

## Summary

The #3990 Binance BTCUSDT 1m corpus was relocated from external volume **Backup II** (`E:\CDB_artifacts\market_data`) to physical `REPO_ROOT/artifacts/market_data` on DevDrive `D:`. The top-level `artifacts` junction was broken; `market_data` is now a normal directory on `D:`; all other `E:\CDB_artifacts` subtrees remain reachable via per-subtree junctions.

---

## Source / Destination

| Field | Source (pre-migration) | Post-cutover |
|-------|------------------------|--------------|
| Volume | `E:` Backup II (Fixed USB) | `D:` DevDrive |
| Path | `E:\CDB_artifacts\market_data` | `D:\Dev\Workspaces\Repos\Claire_de_Binare\artifacts\market_data` |
| Bytes | 8,553,025,212 (~7.97 GiB) | same corpus |
| Files | 1,403 | 1,403 |
| Reparse in `market_data` path | via parent junction | **none** (physical) |

---

## Verification Chain

| Step | Result |
|------|--------|
| robocopy staging | exit 1 (success), 1,403 files, 0 errors |
| SHA256 source vs staging (pre-transform) | **PASS** (0 missing/extra/mismatched) |
| Offline reconcile (source + staging) | **PASS** |
| Manifest transform (staging only) | 1 intentional delta: `config/arvp/binance_btcusdt_1m_full_import.json` |
| SHA256 post-transform | exactly 1 mismatched file (manifest only) |
| Junction cutover | **PASS**, 0 tracked artifact drift |
| Smoke replay 2026-06 | **PASS** |
| Window bank pilot manifest | **PASS** |
| ARVP preflight-only | **PASS** |
| Post-rename re-tests | **PASS**, 0 hidden `E:\CDB_artifacts\market_data` refs |
| Source delete | only `market_data.__relocated_verified_20260712T205513Z` removed |

---

## Dataset Contract (unchanged)

| Metric | Value |
|--------|-------|
| Months | 107 (2017-08 … 2026-06) |
| STRICT_COMPLETE | 81 |
| PARTIAL_USABLE | 26 |
| Failed | 0 |
| Total candles | 4,656,799 |
| Window bank | 108 (106 base + 2 stress_v2) |

---

## Tooling Delivered

- `tools/market_data/binance_archive_manifest_reconcile.py` — read-only offline reconcile
- `tools/market_data/market_data_storage_guard.py` — fail-closed import guard
- `tools/market_data/relocate_hash_manifest.py` — streaming SHA256 manifests
- Runbook update: `docs/runbooks/ARVP_BINANCE_HISTORICAL_IMPORT.md`

---

## Boundaries

- No Docker / DB / MCP / runtime mutation
- No ARVP campaign start
- No live / Echtgeld scope
- Other `E:\CDB_artifacts` content preserved (junctions + copied top-level files)
- Full hash manifests and copy logs remain local under `data-relocation/4004/` (gitignored)

---

## Machine-readable companion

See `BINANCE_HISTORICAL_DATA_RELOCATION_E_TO_D_2026-07-12.json`.
