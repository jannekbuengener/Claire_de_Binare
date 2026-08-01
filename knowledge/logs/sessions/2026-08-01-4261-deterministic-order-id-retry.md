# Session: #4261 DETERMINISTIC_ORDER_ID_RETRY

Date: 2026-08-01
Issue: #4261
PR: #4262
Residual: DETERMINISTIC_ORDER_ID_RETRY

## Summary

Hardened PAPER_AUTO_UNWIND deterministic order-id retry semantics by separating
stable `logical_operation_key` from concrete attempt `order_id`
(`uuid5("<key>:attempt:<N>")`). Terminal retryable `REJECTED` (zero fill,
`REDUCE_ONLY_REJECTED`) may advance one generation; active/success/unclear
states remain fail-closed. Claim-before-dispatch retained.

## Validation

- pytest targeted retry/claim/reduce-only suites: PASS
- ruff / black / git diff --check: PASS
- No compose, migration, or filled_quantity changes

## Boundaries

- LR NO-GO; no merge; no issue close; no cdb-local-ci; no R1–R10
