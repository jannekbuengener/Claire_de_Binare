# Session: context-query literal normalizer (#2679)

**Date:** 2026-05-29  
**Issue:** [#2679](https://github.com/jannekbuengener/Claire_de_Binare/issues/2679)  
**PR:** [#2680](https://github.com/jannekbuengener/Claire_de_Binare/pull/2680)  
**Refs:** #2604 (epic stays open)

## Problem

`_normalize_statement` in `tools/surrealdb/context_query.py` applied `.upper()` to the full SurrealQL string, including string literals. Effects:

- Benign filter `name CONTAINS "apply"` matched `\bAPPLY\b` → false `WRITE_DENIED`.
- Classification metadata showed `"MD"` / `"DOCS/"` instead of user literals.

## Change

- Added `_SURQL_STRING_LITERAL_RE` and literal-preserving normalization: uppercase only text outside quoted literals.
- Classifier write guards unchanged; executed SQL still built via `_surrealql_string` (unchanged).

## Validation (local)

```bash
pytest tests/unit/surrealdb/test_context_query_classifier.py tests/unit/surrealdb/test_context_query_builders.py -v
ruff check tools/surrealdb/context_query.py tests/unit/surrealdb/test_context_query_classifier.py
black --config pyproject.toml tools/surrealdb/context_query.py tests/unit/surrealdb/test_context_query_classifier.py
```

## Governance

- LR: NO-GO (unchanged)
- Board stage: trade-capable (orthogonal)
- No runtime/MCP/memory/trading scope

## Outcome

PR #2680 squash-merged to `main` (`ad3ddffd`). Issue #2679 closed. Epic #2604 remains open.
