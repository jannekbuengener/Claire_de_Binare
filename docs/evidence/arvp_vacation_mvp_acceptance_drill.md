# ARVP Vacation Autopilot MVP — Acceptance Drill (#3986)

Status: **PASS** (unit/fixture drill)
Issue: [#3986](https://github.com/jannekbuengener/Claire_de_Binare/issues/3986)
Parent: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - pytest tests/unit/arvp/test_arvp_vacation_mvp.py tests/unit/arvp/test_arvp_vacation_recovery.py
  - python -m tools.arvp_vacation.coordinator --preflight-only
records_or_results:
  - 16/16 vacation MVP tests PASS
repo_crosscheck:
  - tools/arvp_vacation/
  - config/arvp/vacation/vacation_autopilot_mvp.yaml
limitations:
  - Drill uses injectable subprocess/disk probes; no destructive host/docker/db fault injection
  - Production replay jobs not executed in this evidence slice
```

## Drill matrix

| Step | Simulation | Result |
|------|------------|--------|
| 1 | >=6 jobs from 3 datasets x 2 active + 1 parked strategies | PASS (fixture) |
| 2 | Normal job completion | PASS |
| 3 | Subprocess timeout / kill | PASS (TimeoutExpired path) |
| 4 | Coordinator resume | PASS |
| 5 | Orphan RUNNING -> INTERRUPTED | PASS |
| 6 | No double processing of completed fingerprint | PASS |
| 7 | Invalid dataset path | PASS (discover skips / empty) |
| 8 | Duplicate fingerprint | PASS (SKIPPED_DUPLICATE) |
| 9 | Disk below minimum | PASS (FATAL_STOP) |
| 10 | Summary JSON + MD | PASS |

## Production manifest preflight (repo datasets)

Command:

```powershell
python -m tools.arvp_vacation.coordinator --manifest config/arvp/vacation/vacation_autopilot_mvp.yaml --preflight-only
```

Expected datasets (no window_007 duplicate of strict_3091):

- `mexc_strict_window_3091_island_3`
- `mexc_multi_window_3032_window_015`
- `mexc_multi_window_3032_window_020`

Job estimate: **7** (3 datasets x 2 active + 1 parked anchor on strict window)

- Offline `controlled_lab_evidence` only
- No paper runtime queue
- No auto-start on host reboot
- OPERATIONS-GO required before production run (see runbook)
