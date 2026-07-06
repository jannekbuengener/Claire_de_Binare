# Session: Context Graph contract tests (#3772)

**Date:** 2026-07-06  
**Issue:** #3772 (child of #3771)  
**Status:** DONE_MERGED_CLOSED  
**Merge:** PR #3806 @ `09d1e8808af8cbf7cfc6a02a7fe3754955e14184`

## Scope

P0 Context Graph contract tests: nodes, edges, deterministic IDs, source refs, hash/fingerprint stability, repo-fallback negative controls. Fixture-only CI; no live SurrealDB; no productive DB writes; no runtime changes.

## Delivered

- `tools/surrealdb/context_graph_contract.py` — read-only contract validators
- `tests/unit/surrealdb/test_context_graph_contract.py` — 19 unit/contract tests

## Validation

- Local: `pytest tests/unit/surrealdb/test_context_graph_contract.py -v` → 19 passed
- `ruff check` on touched files → PASS
- CI (PR #3806): `ci (Unit/Integration + Lint gesammelt)`, `policy-gate`, `surrealdb-validate` → PASS

## GitHub

- #3772 CLOSED (via PR body `Closes #3772`)
- #3771 progress comment posted

## Boundaries

- LR NO-GO; no live/echtgeld go
- No BLUE/RED runtime changes
- No MCP mutations; Context briefing LOW trust → repo-only fallback used

## Follow-ups

- #3773 Evidence Resolver regression tests (next P0 slice per #3771)
- Optional `local_only` SurrealDB traversal smokes (out of scope for #3772)
