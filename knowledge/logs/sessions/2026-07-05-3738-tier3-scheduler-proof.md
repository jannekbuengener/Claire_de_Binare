# Session: #3738 Tier-3 host-resilience & scheduler proof

**Date:** 2026-07-05  
**Issue:** #3738  
**Main SHA at start:** 41ca6ba4  
**Status:** DONE_SCHEDULER_PASS_TIER3_LIMITATION

## Scope

- GO-1: Scheduler deployment smoke (install/run/uninstall + boot readiness)
- GO-2: Tier-3 bounded coordinator+supervisor run
- Tier-3 reboot/hibernate: explicit LIMITATION docs
- Scheduler fix: schtasks `/TR` 261-char limit via `run_task.cmd`

## Delivered

| Slice | Verdict | run_id |
|-------|---------|--------|
| Scheduler deployment | **PASS** | `scheduler-20260705T114504Z` |
| Tier-3 bounded run | **LIMITATION** | `tier3-sleep-20260705T114800Z` |
| Reboot/Hibernate | **LIMITATION** | docs-only |

## Validation

- `boot preflight/status`: PASS (21/21)
- `scheduler install --explicit`: PASS (after run_task.cmd fix)
- `schtasks /Run`: PASS (snapshot generated)
- `scheduler uninstall --explicit`: PASS
- `pytest tests/unit/tools/evidence_harvester/test_scheduler.py`: 6 passed
- Tier-3: 2/6 cycles PASS, in-process sleep/wake; no OS sleep triggered

## Boundaries

- LR **NO-GO** unchanged
- No Docker/DB/MCP/trading mutation
- No new >=72h coordinator run

## Artifacts

- `docs/evidence/host_resilience_proof/scheduler-20260705T114504Z/`
- `docs/evidence/host_resilience_proof/tier3-sleep-20260705T114800Z/`
- `docs/evidence/evidence_harvester_*_2026-07-05.md`
- Runtime trees under `artifacts/evidence_harvester/host_resilience_proof/`

## Follow-ups

- Optional future scope: ATLOGON/startup task for coordinator+supervisor autostart after reboot (not in #3738 acceptance)
