# Session Log: 2026-07-01 — Issue #3634 Coordinator Sleep-Stall Fix

## Scope

Root-cause and harden the 72h Evidence Harvester so a run no longer ends after
`sleep_started` without `sleep_completed` (Slice-B/C/D INCONCLUSIVE pattern).
Deliver a resume-safe coordinator + testable supervisor, unit/regression tests,
docs. No new 72h run; no runtime mutation beyond local/test.

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - Read tools/evidence_harvester/coordinator.py (run_fixture_window, _sleep_with_interval_check)
  - Read tools/evidence_harvester/ops_validation.py (_check_inconclusive_run, _check_sleep_lifecycle_completeness)
  - pytest tests/unit/tools/evidence_harvester/
records_or_results:
  - root cause: completed_cycles=0 re-init per launch; blocking sleep between durable sleep_started/sleep_completed
  - tests: 29 targeted PASS; 260 harvester-suite PASS; ruff clean
repo_crosscheck:
  - tools/evidence_harvester/coordinator.py (resume path, _prepare_resume, _last_event_is_stalled_sleep)
  - tools/evidence_harvester/supervisor.py (decide_supervision, supervise_loop)
impact_on_plan:
  - resume clears O264/O303 without a real 288-cycle run
limitations:
  - no >=72h PASS produced; #3362 remains OPEN; external subprocess supervision deferred to Slice-E (Runtime-GO)
```

## Root cause (code-backed)

`run_fixture_window` re-initialised `completed_cycles = 0` on every launch and
looped `while completed_cycles < iterations`. The durable events `sleep_started`
and `sleep_completed` bracket a single in-process blocking
`_sleep_with_interval_check`. A process death inside that sleep left no
`sleep_completed`, no `final_validation_*`, and no resume path → O264 warn +
O303 INCONCLUSIVE.

## Delivered

- **Coordinator resume** (`tools/evidence_harvester/coordinator.py`): new
  `resume-fixture-window` subcommand + `resume=True`; `_prepare_resume`
  (fail-closed on missing state / `run_id` mismatch / terminal status);
  `_last_event_is_stalled_sleep`; `sleep_resumed` lifecycle event + audited
  `recovery_event` (`failure_source="sleep_stall"`, `action="resume_cycle_window"`);
  `completed_cycles` seeded from `runner_state.total_cycles_completed`.
- **Supervisor** (`tools/evidence_harvester/supervisor.py`, new): pure
  `decide_supervision` (`WAIT|RELAUNCH_RESUME|DONE|STOP_FATAL|STOP_LIMIT`) +
  injectable bounded `supervise_loop`; read-only `status` CLI; `supervise` CLI
  fail-closed behind `--explicit`. No process spawn, scheduler, or Docker.
- **Tests**: `test_coordinator.py` (resume seeding/no double-count, interrupted
  sleep → `final_validation_completed`, resume-of-completed → final only,
  fail-closed x3, interrupt propagation, O264/O303 validator consistency);
  `test_supervisor.py` (decision matrix, relaunch→DONE, STOP_LIMIT,
  WAIT_TIMEOUT, arg parsing).
- **Docs**: runbook `CDB_EVIDENCE_HARVESTER_OPS.md` (resume + supervisor
  section, schema `resuming`, related docs); evidence doc `#3634` section +
  Slice-E plan; `CURRENT_STATUS.md` entry.

## Validation

```powershell
python -m pytest tests/unit/tools/evidence_harvester/test_coordinator.py tests/unit/tools/evidence_harvester/test_supervisor.py -q
# 29 passed

python -m pytest tests/unit/tools/evidence_harvester/ -q
# 260 passed

ruff check tools/evidence_harvester/coordinator.py tools/evidence_harvester/supervisor.py `
  tests/unit/tools/evidence_harvester/test_coordinator.py tests/unit/tools/evidence_harvester/test_supervisor.py
# All checks passed!
```

## Boundaries

LR NO-GO. No Live/Echtgeld-Go. No Docker/DB/Redis/secrets. No new 72h run; no
72h-PASS claim. #3362 and #3345 remain OPEN.

## Status

`DONE` (engineering) — resume + supervisor + tests + docs delivered; PR/merge and
#3634 close tracked in the delivery step.
