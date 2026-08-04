# Session: #4336 CDB-049 File/DB Window Parity

- **Date**: 2026-08-04
- **Base**: `origin/main` @ `09f60faa9c6a07ac2edb66cf7641329877919b15`
- **Branch**: `batch/validation-research-issue-4336`
- **Worktree**: `D:\Dev\Workspaces\Repos\cdb-wt-4336-cdb049`

## Delivered (CDB-049 only)

- Shared `enforce_exact_window` / `warmup_start_ms` / discover sentinel in `dataset_provider.py`
- File provider enforces exact window unless discover `(0,0)`
- DB provider uses shared exact-window helper
- `binance_window` adapter rebinds live start after warmup; fail-closed on end/start mismatch
- Runner file-discover re-validates exact window after bound rebound (#4335 FP path unchanged)

## Validation

- 63 targeted unit tests PASS (`test_dataset_provider`, adapter, Fingerprints4335)
- ruff / black PASS on touched files

## Status

`DONE_SLICE_ADDED_TO_BATCH_PR` (after push/PR)

## Residuals (Issue #4336 remains OPEN)

- CDB-050 — DQ verdict ↔ content fingerprint
- CDB-051 — Replay-vs-Runtime contract / register drift
- CDB-052 — Rankability / stale-manifest fail-closed (`FROZEN_UNTIL_CONTRACT`)

## Boundaries

- no campaign (#4153)
- no merge / no issue close
- no Risk / Live / Echtgeld
- LR NO-GO
- READY_FOR_REPLAY_SENSITIVITY ≠ CDB-049..052 closed
