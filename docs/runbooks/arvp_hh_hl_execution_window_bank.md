# hh_hl execution window-bank wiring (#4395)

Status: Canonical operator note  
Scope: Offline-replay campaign execution surfaces for `hh_hl_continuation_v1`  
Parent: #4374 / follow-up #4395

## Problem

Exact-SHA git worktrees often have **no** local `artifacts/market_data`.
Dataset prove can still PASS against the parent Claire_de_Binare bank, while
`hh_hl_campaign_execute` historically defaulted to
`repo_root/artifacts/market_data/...` and terminalized the first run as
`BLOCKED` (`HOLD_EXECUTION_DATASET_LOAD_FAILED`). Preflight previously returned
`ok=true` because it only checked receipt digests.

## Deterministic resolution (read-only)

```powershell
python -m tools.arvp_vacation.hh_hl_execution_window_bank --repo-root <EXEC_ROOT> resolve
python -m tools.arvp_vacation.hh_hl_execution_window_bank --repo-root <EXEC_ROOT> assert
```

Preference order:

1. `CDB_WINDOW_BANK_ROOT` / `CDB_DATASET_ROOT`
2. `<EXEC_ROOT>/artifacts/market_data` (local tree or junction)
3. Parent Claire_de_Binare checkout `artifacts/market_data` (`.worktrees/<name>` layout)

All 39 locked Batch-A development windows must be present. No candle copy.
No dataset content mutation.

`preflight` / `status` / production `execute` call the same assert and fail closed
with `HOLD_EXECUTION_WINDOW_BANK_UNAVAILABLE` when unresolved.

## Optional operator link

To materialize the contract path under the worktree (junction on Windows,
symlink elsewhere):

```powershell
python -m tools.arvp_vacation.hh_hl_execution_window_bank --repo-root <EXEC_ROOT> ensure-link
```

This never replaces a conflicting real directory.

## Clean restart after `STATE_TERMINAL_BLOCKED`

When a run is terminal `BLOCKED` (including dataset-load safety HOLDs):

1. **Do not** edit, delete, or “repair” `run_envelope.json` / campaign envelopes.
2. **Do not** reuse the blocked evidence namespace for a forced resume.
3. Prepare a **clean** exact-SHA execution surface (resolved/linked bank + empty
   evidence root for the *new* authorization fingerprint).
4. Issue a **new Owner Execution-GO** bound to the intended SHA/bindings.
5. Dual-preflight → status → execute under the new GO only.

Old Owner-GO comment bodies must not be edited. Analyzer / paper / live /
echtgeld remain out of scope. LR stays NO-GO.
