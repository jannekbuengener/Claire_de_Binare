# Session: G3a MCP operation_mode fail-closed scaffold (#2741)

**Date:** 2026-05-30  
**Issue:** [#2741](https://github.com/jannekbuengener/Claire_de_Binare/issues/2741)  
**Parent:** [#2606](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606) (OPEN)  
**Branch:** `feat/g3a-mcp-operation-mode-scaffold`

## Goal

Implement G2 refusal semantics in `cdb_context_memory_write_intent` without
productive persist, SQL, or `PERSIST_ALLOWED` flip.

## Changes

| File | Change |
| --- | --- |
| `tools/mcp/memory_write_intent_tools.py` | `operation_mode` resolution; `_refused_response`; G2 codes |
| `tools/mcp/memory_output_contract.py` | Skip full contract validation for `status: refused` |
| `tools/mcp/registry.py` | Input schema: `operation_mode`, `memory_record` |
| `tests/unit/tools/mcp/test_memory_write_intent_tool.py` | Refusal matrix (+12 tests) |
| `docs/surrealdb/mcp-memory-write-surface-v1.md` | Phase 2 G3a status |
| `docs/surrealdb/memory-reality-slice1-audit.md` | §22.4 G3a addendum |

## Verification

```bash
pytest tests/unit/tools/mcp/test_memory_write_intent_tool.py -v  # 20 passed
ruff check tools/mcp/memory_write_intent_tools.py tools/mcp/memory_output_contract.py tools/mcp/registry.py tests/unit/tools/mcp/test_memory_write_intent_tool.py
```

## Boundaries preserved

- LR: **NO-GO**
- `PERSIST_ALLOWED=False`
- `MUTATION_ALLOWED=False`
- Registry `read_only=True`
- #2606 not closed

## Merge (2026-05-30)

- PR [#2742](https://github.com/jannekbuengener/Claire_de_Binare/pull/2742) **MERGED** (squash) → main @ `ce44cd38`
- CI: `ci (Unit/Integration + Lint gesammelt)` + `policy-gate` green; no review threads
- #2741 **CLOSED** (expected)
- **Anomaly:** GitHub auto-closed #2606 despite PR body `Refs #2606` / explicit non-close boundary — operator reopen may be required

## Next

- G3b: `memory_write_path_productive` module + mock tests
- G3c: HG-P operator proof (separate GO)
- Reconcile #2606 state if parent epic must remain OPEN
