# Session: #4335 Runner FP propagation

- **Date**: 2026-08-04
- **Base**: `origin/main` @ `10ddcc09`
- **Branch**: `batch/validation-research-issue-4335`
- **Commit**: `850722101e4e532bcc33ff6a8ae2a74a7f199a02`
- **PR**: [#4337](https://github.com/jannekbuengener/Claire_de_Binare/pull/4337) open

## Delivered

- `strategy_replay_runner`: file + `binance_window` propagate/recompute request/content fingerprints
- Regression tests for fingerprint propagation

## Validation

- 6 targeted tests pass
- ruff / black pass
- preflight READY (readiness only)

## Status

`DONE_SLICE_ADDED_TO_BATCH_PR`

## Residuals

- #4336 open
- #4153 / #4147 open
- no merge
- LR NO-GO

## Boundaries

- no campaign
- no #4336
- no live / echtgeld
