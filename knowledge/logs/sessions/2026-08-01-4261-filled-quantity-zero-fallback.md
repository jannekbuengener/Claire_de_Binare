# Session: #4261 FILLED_QUANTITY_ZERO_FALLBACK

Date: 2026-08-01
Issue: #4261
PR: #4262
Residual: FILLED_QUANTITY_ZERO_FALLBACK

## Summary

Replaced falsy `filled_quantity or quantity` chains in `DatabaseWriter` with
explicit presence/null/zero/positive/invalid resolution. Explicit numeric 0 is
preserved and skips trade/position mutation (no phantom fills). Legacy fallback
to requested `quantity`/`size` only when primary fill keys are absent.

## Validation

- pytest `tests/unit/db_writer/test_filled_quantity_zero_fallback.py` + existing
  db_writer/claim/retry suites: PASS
- ruff / black / diff-check: PASS

## Boundaries

- LR NO-GO; no merge; no issue close; no compose/migration; Claim/Attempt-ID
  unchanged
