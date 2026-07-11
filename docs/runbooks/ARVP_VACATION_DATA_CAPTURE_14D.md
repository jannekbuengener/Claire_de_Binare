# ARVP Vacation Data Capture — 14-Day MEXC BTCUSDT 1m (No Trading)

Version: 1.0  
Issue: #3990  
Parent: #1900  
Related: #3091 (capture path), #3986/#3988 (offline vacation queue — post-capture consumer)

## Purpose

Collect **new, provenance-valid MEXC BTCUSDT 1m candles** into `public.candles_1m` during operator absence.
This is a **data-capture campaign**, not paper trading, not signal execution, not live-go.

Static replay expansion improves evidence breadth but cannot provide two-week runtime capacity.
The vacation workload is a no-trading MEXC candle capture campaign. Replays consume the resulting windows after capture.

LR remains **NO-GO**. No paper, live, or Echtgeld scope.

## Verified minimal service set

Evidence chain (repo, #3091):

```text
MEXC WebSocket (cdb_ws)
  → Redis pub/sub market_data
  → Candle service (cdb_candles)
  → stream.candles_1m
  → DB Writer (cdb_db_writer)
  → public.candles_1m
```

| Service | Role | Compose file |
|---------|------|--------------|
| `cdb_postgres` | Candle persistence | `compose.blue.yml` |
| `cdb_redis` | Message bus | `compose.blue.yml` |
| `cdb_ws` | MEXC market input | `compose.red.yml` |
| `cdb_candles` | 1m aggregation | `compose.blue.yml` |
| `cdb_db_writer` | Stream → Postgres | `compose.blue.yml` |

**Explicitly excluded** (must not run): `cdb_signal`, `cdb_risk`, `cdb_allocation`, `cdb_execution`, `cdb_paper_runner`, vacation replay queue coordinator, any order/paper path.

**Not required for raw capture:** `cdb_market`, `cdb_regime` (regime enrichment is a post-export offline step).

## Artifacts

```text
manifests/vacation/vacation_data_capture_14d.yaml
scripts/arvp_vacation_data_capture.ps1
artifacts/arvp_vacation/data_capture/<campaign_id>/
  campaign_state.json
  campaign_events.jsonl
  heartbeat.json
  service_inventory.json
  coverage_snapshots.jsonl
  final_capture_summary.json   (after stop / return)
  final_capture_summary.md
```

## Preflight (before GO)

```powershell
cd D:\Dev\Workspaces\Repos\Claire_de_Binare
git rev-parse HEAD
git status
.\scripts\arvp_vacation_data_capture.ps1 -Preflight -Json
```

Preflight checks (14 items):

1. Git HEAD matches manifest `source_sha` (or `RUNTIME_RESOLVE` at GO)
2. Working tree clean
3. Docker reachable
4. Free disk ≥ manifest minimum (default 5 GB)
5. Postgres/Redis start path available (compose files present)
6. No forbidden trading/paper services running
7. No productive exchange credentials used for orders (forbidden services off)
8. Candle stream / DB-writer contract unchanged (allowed set only)
9. `public.candles_1m` coverage probe via `POSTGRES_READONLY_PASSWORD_DSN` when set
10. Campaign ID unused (no prior `campaign_state.json`)
11. No volume/data deletion (`stop` never uses `down -v`)
12. UTC timestamps enforced at runtime window resolution
13. Planned end = start + exactly 14 days (validated at Start)
14. Safety flags: `allow_signal/execution/paper/live_trading=false`

Pin `source_sha` in the manifest before departure if you require a fixed commit pin instead of `RUNTIME_RESOLVE`.

## Human gate (Start / Resume)

Start and Resume are blocked unless the exact phrase is supplied:

```text
DATA-CAPTURE-GO #3990 vacation 14d preflight and acceptance drill
```

```powershell
$go = "DATA-CAPTURE-GO #3990 vacation 14d preflight and acceptance drill"
.\scripts\arvp_vacation_data_capture.ps1 -Start -GoPhrase $go
.\scripts\arvp_vacation_data_capture.ps1 -Status -Json
.\scripts\arvp_vacation_data_capture.ps1 -Stop
.\scripts\arvp_vacation_data_capture.ps1 -Resume -GoPhrase $go
```

## Acceptance drill (before 14-day run)

Use a **separate campaign ID** (copy manifest, set `drill_campaign_id` pattern, `max_duration_days` unchanged but stop manually after ~15 minutes).

Drill must prove:

1. Only allowed services start
2. No signal/execution/paper services run
3. New MEXC candles reach `cdb_candles` (Redis stream growth)
4. New rows appear in `public.candles_1m`
5. Timestamps monotonic in drill window
6. No duplicates/gaps in drill window (readonly gap script post-drill)
7. Status coverage correct
8. Stop ends capture services cleanly
9. Data retained after stop
10. Resume works or is documented as manual-only

Suggested drill flow:

```powershell
# 1. Preflight
.\scripts\arvp_vacation_data_capture.ps1 -Preflight -Json

# 2. Start with GO phrase (drill manifest copy if isolated campaign_id desired)
$go = "DATA-CAPTURE-GO #3990 vacation 14d preflight and acceptance drill"
.\scripts\arvp_vacation_data_capture.ps1 -Start -GoPhrase $go

# 3. Wait >= drill_duration_minutes (default 15) — observe Status every few minutes
.\scripts\arvp_vacation_data_capture.ps1 -Status -Json

# 4. Stop (no volume delete)
.\scripts\arvp_vacation_data_capture.ps1 -Stop
```

## 14-day operation

Expected candle volume: **20 160** rows (14 × 24 × 60), plus warmup overlap negligible.

Disk estimate (Postgres candles row ~200–400 B): **~8–15 MB** raw table growth for BTCUSDT 1m only; allow headroom for WAL/logs (manifest default 5 GB free minimum).

Status polling: heartbeat every `heartbeat_interval_seconds` (300 s); stale if no new candle > `stale_threshold_seconds` (180 s) while campaign running.

## Host reboot / auto-resume

**Not enabled.** Tier-3 Evidence Harvester supervisor (#3733/#3738) targets the harvester coordinator, not this Docker capture set.
Trading-adjacent services are forbidden; unproven Windows Task Scheduler install is out of scope.

After host reboot: **manual Resume** with GO phrase, respecting `max_restart_budget` (default 3) and `planned_end_utc`.

## Post-return export (read-only)

No DB writes. No large artifact commits.

1. **Inventory** (readonly DSN):

   ```powershell
   python scripts/arvp_3742_natural_paper_window_inventory.py
   ```

   Or scoped SELECT on `public.candles_1m` for `[start_ts_ms, end_ts_ms]` from `campaign_state.json`.

2. **Gap / continuity**: reuse patterns from `docs/evidence/mexc_future_capture_3091.md` and `scripts/profitability/build_mexc_multi_window_evidence_3032.py` (island detection, 1m step checks).

3. **File-backed dataset**: export JSONL + `dataset_spec.json` + `provenance_manifest.json` under `artifacts/candles/<campaign_window_id>/` (readonly principal `cdb_readonly`).

4. **Regime-enriched variant** (optional, offline): `assign_regime_calibrate_3032_expansion` pipeline on exported file — not required for capture campaign.

5. **Vacation queue**: add new dataset roots to a **generated** vacation manifest (do not edit tracked MVP manifest in-place). Offline replays consume windows after capture.

## Boundaries

- No signal/strategy execution, paper trading, orders, live-go, LR upgrade
- No deletion/overwrite of existing candles
- No compose `down -v`
- No secrets in evidence artifacts

## Verdicts

| Verdict | Meaning |
|---------|---------|
| `VACATION_DATA_CAPTURE_READY_FOR_DRILL` | Preflight tooling merged; drill not yet run |
| `VACATION_DATA_CAPTURE_PARTIAL` | Drill partial or resume unproven |
| `VACATION_DATA_CAPTURE_NO_GO` | Safety/preflight blocker |

This preparation slice targets **READY_FOR_DRILL** without runtime start.
