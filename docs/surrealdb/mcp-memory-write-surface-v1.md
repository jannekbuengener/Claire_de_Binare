# MCP Memory Write Surface v1 — Design (#2704)

Status: Phase 1 delivered (dry-run default, mutation fail-closed)  
Parent: [#2606](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606)  
Issue: [#2704](https://github.com/jannekbuengener/Claire_de_Binare/issues/2704)

LR remains **NO-GO**. Board stage `trade-capable` does not authorize live memory
mutation or Echtgeld operations.

## Purpose

Expose a gated **memory write intent** MCP tool so agents can evaluate Human-GO
authorization and memory contract validity without executing persistence.

## Tool

| Field | Value |
|-------|-------|
| Tool ID | `cdb_context_memory_write_intent` |
| Registry | `read_only=True` |
| Module constant | `MUTATION_ALLOWED = False` |
| Handler | `tools/mcp/memory_write_intent_tools.py` |

## Phase 1 (this delivery)

- Default path: **`evaluate_memory_write_gate()`** only (implicit dry-run).
- Response wraps gate envelope + agent output contract fields (`memory_id`,
  `limitations`, `metadata.source=in_memory`).
- Mutation flags (`mutation_requested`, `execute_write`, `execute`, `persist`,
  `audit_persist_local`) → **`mutation_blocked_by_default`**.
- Optional `query` / `sql` / `surql` / `statement` parameters with SQL keywords
  → **`unsafe_input`** (handler-level; record body exempt from blanket scan).
- No SQL client, no adapter import, no `agent_memory` UPSERT.

## Phase 2 (future — separate Human-GO)

Not implemented in this slice:

- Registry `read_only=False` for a mutation-capable tool variant.
- Permission-guard extension for audited write execution.
- Wiring to `memory_write_path_v1` audit persist or Slice 6 smoke paths.

Any future mutation surface requires explicit operator GO, contract evidence, and
a separate issue/PR — not implied by this design doc.

### Readiness gates (productive audit trail #2730)

Before MCP Phase 2 mutation design proceeds, these gates apply (spec-only on
`main` until separate implementation issues):

| Gate | Requirement |
| --- | --- |
| G0 | [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md) landed |
| G1 | Non-local audit endpoint design (future issue) |
| G2 | MCP Phase 2 design aligned with T3 audit semantics |
| G3 | `PERSIST_ALLOWED` code flip — **not** MCP-only |
| G4 | Productive `agent_memory` write — separate from MCP dry-run |

MCP dry-run (Phase 1) remains default; `MUTATION_ALLOWED = False`. Operator
checklist: [`productive-memory-write-readiness-runbook-v1.md`](productive-memory-write-readiness-runbook-v1.md).

## Cross-refs

- Gate: [`memory_write_gate.py`](../../tools/surrealdb/memory_write_gate.py)
- Write path v1: [`memory_write_path_v1.py`](../../tools/surrealdb/memory_write_path_v1.py)
- Operator runbook: [`memory-write-path-v1-runbook.md`](memory-write-path-v1-runbook.md)
- Output contract: [`memory_output_contract.py`](../../tools/mcp/memory_output_contract.py) (#2701)
- Bridge contract: [`context-mcp-bridge-contract.md`](context-mcp-bridge-contract.md)
- Productive audit trail: [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md) (#2730)

## Validation

```bash
pytest tests/unit/tools/mcp/test_memory_write_intent_tool.py -v
ruff check tools/mcp/memory_write_intent_tools.py tests/unit/tools/mcp/test_memory_write_intent_tool.py
```
