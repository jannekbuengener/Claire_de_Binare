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

## Phase 2 (G2 design — #2739; G3a scaffold — #2741)

Spec: [`productive-memory-audit-trail-mcp-phase2-design-v1.md`](productive-memory-audit-trail-mcp-phase2-design-v1.md)

**G3a (#2741): refusal scaffold implemented on `main` (after merge).** Handler
`memory_write_intent_tools.py` resolves `operation_mode` and refuses non-dry-run
modes per G2 (`productive_audit_not_activated`, `local_audit_mcp_not_activated`,
`agent_memory_write_not_activated`, `hg_p_required`, `operation_mode_invalid`).
Dry-run path unchanged; registry remains `read_only=True`; no SQL; no
`PERSIST_ALLOWED` flip.

G2 also defines (not yet implemented):

- Permission model extensions (registry / PermissionGuard — G3b/G3c)
- Wiring intent to G1 governed endpoint via `memory_write_path_productive` (G3b)

Any future mutation or registry `read_only=False` change requires maintainer GO,
contract evidence, and a separate issue/PR — not implied by Phase 1, G2, or G3a.

### Legacy Phase 2 stub (pre-G2)

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
| G1 | Non-local audit endpoint design — [`productive-memory-audit-trail-endpoint-design-v1.md`](productive-memory-audit-trail-endpoint-design-v1.md) ([#2735](https://github.com/jannekbuengener/Claire_de_Binare/issues/2735); design only) |
| G2 | MCP Phase 2 design — [`productive-memory-audit-trail-mcp-phase2-design-v1.md`](productive-memory-audit-trail-mcp-phase2-design-v1.md) ([#2739](https://github.com/jannekbuengener/Claire_de_Binare/issues/2739); design only) |
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
- G1 endpoint design: [`productive-memory-audit-trail-endpoint-design-v1.md`](productive-memory-audit-trail-endpoint-design-v1.md) (#2735)
- G2 MCP Phase 2 design: [`productive-memory-audit-trail-mcp-phase2-design-v1.md`](productive-memory-audit-trail-mcp-phase2-design-v1.md) (#2739)
- G3a MCP operation_mode scaffold: #2741 (handler refusal codes; no persist)

## Validation

```bash
pytest tests/unit/tools/mcp/test_memory_write_intent_tool.py -v
ruff check tools/mcp/memory_write_intent_tools.py tests/unit/tools/mcp/test_memory_write_intent_tool.py
```
