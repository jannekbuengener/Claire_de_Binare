# CDB Verdict Classes

Use exactly one primary verdict.

## PASS
Use only when the claim is directly supported by the relevant canon and evidence.

## PASS WITH EXPLICIT LIMITS
Use when the claim is acceptable only with named boundaries that must stay visible.

## NON-BLOCKING GAP
Use when a real gap exists, but it does not block the decision surface under review.
Keep the residual explicit.

## BLOCKED
Use when a required condition, proof basis, or source-of-truth boundary is unresolved.
Do not soften this into narrative.

## OUT OF SCOPE
Use when the finding is real but not part of the current decision surface.
Do not silently absorb it into the verdict.

## Fast checks
- If proof depends on memory, use `BLOCKED` or `NON-BLOCKING GAP`.
- If Stage is acceptable but LR is still `NO-GO`, do not use `PASS` for LR.
- If code is fixed but closure proof is incomplete, prefer `PASS WITH EXPLICIT LIMITS` or `NON-BLOCKING GAP`.
