# CDB MCP Access Boundary

Machine-readable access boundary for CDB Context/MCP/SurrealDB tooling.

## Summary

- Total tools in matrix: 42
- Exposed CDB context tools: 27
- Repo-present but not exposed: 3
- Allowed read-only: 27
- Forbidden mutation: 7
- Future: 3
- Blocked: 5
- Unknown: 0
- Live DB claims proven: 0

## Decision Meaning

- `ALLOWED_READONLY`: read-only use is allowed with registry/guard evidence.
- `FORBIDDEN_MUTATION`: mutative tool surface is not allowed for CDB agents.
- `FUTURE`: repo-documented target alias, not exposed today.
- `BLOCKED`: upstream or raw surface is intentionally not adopted by CDB.
- `UNKNOWN`: classification gap; `gap_reason` required.

## Allowed Read-only

- `cdb_agent_os_readiness`
- `cdb_context_architect_signals`
- `cdb_context_briefing`
- `cdb_context_claim_resolve`
- `cdb_context_contradictions`
- `cdb_context_decision_history`
- `cdb_context_decision_replay`
- `cdb_context_evidence_resolve`
- `cdb_context_impact`
- `cdb_context_memory_get`
- `cdb_context_memory_write_intent`
- `cdb_context_quality_score`
- `cdb_context_scope_drift`
- `cdb_context_stale`
- `cdb_context_trust_summary`
- `cdb_control_room_view`
- `context.briefing`
- `context.explain_source`
- `context.package`
- `context.readiness`
- `context.required_reads`
- `context.search`
- `context.self_explain`
- `context.show_audit`
- `context.show_snapshot`
- `context.stop_resolver`
- `context.trace`

## Forbidden Mutation

- `create`
- `delete`
- `insert`
- `relate`
- `run`
- `update`
- `upsert`

## Repo-Present Not Exposed

- `cdb_context_package`
- `cdb_context_search`
- `cdb_context_trace`

## Blocked Raw MCP

- `info`
- `list`
- `query`
- `select`
- `use`

## #3481 Acceptance / Evidence Reconcile

This document is the canonical #3481 boundary surface. It now also carries the
explicit reconcile mapping between the safety boundary delivered in PR #3497 and
the later surface-parity evidence delivered for #3493 in PR #3534.

| #3481 acceptance surface | Repo-backed truth | Delivery source | Reconcile status |
|---|---|---|---|
| MCP access boundary | Boundary matrix exists as a canonical doc and machine artifact. | PR #3497; `tools/mcp_access_boundary.py`; `artifacts/mcp/mcp_access_boundary_matrix.{json,md}` | delivered |
| Raw upstream MCP blocking | `query`, `select`, `list`, `use`, `info` stay blocked raw MCP tools. | PR #3497 boundary matrix | delivered |
| Forbidden mutation list | `create`, `insert`, `upsert`, `update`, `delete`, `relate`, `run` stay forbidden. | PR #3497 boundary matrix | delivered |
| Curated read-only surface | 27 exposed CDB context tools are classified `ALLOWED_READONLY`. | PR #3497 boundary matrix | delivered |
| Unknown-gap control | `UNKNOWN=0` in the boundary matrix. | PR #3497 boundary matrix + tests | delivered |
| Surface parity / every-surface check | Repo-backed inventory truth shows `repo_surface_configured=27` across the configured agent surfaces. | PR #3534; `artifacts/context_tool_inventory/tool_inventory.{json,md}` | reconciled |
| Session callability | Only `context.required_reads` and `context.readiness` are proven `session_callable=2`. | PR #3534 inventory truth | reconciled with explicit limits |
| Operational proof boundary | `operationally_proven=0`; no tool is promoted to operational proof by this reconcile. | PR #3534 inventory truth | unchanged by design |
| DB-backed proof boundary | `DB_BACKED=0`; no `DB_BACKED_READONLY_PROVEN` claim is added here. | PR #3534 inventory truth + boundary guardrails | unchanged by design |

### Boundary Truth vs. Surface Truth

- **PR #3497** delivered the #3481 safety core: allowed read-only tools,
  forbidden mutation tools, blocked raw MCP tools, FUTURE aliases, and
  `UNKNOWN=0`.
- **PR #3534** delivered the later repo-backed surface-truth needed to reconcile
  #3481's parity question without inflating runtime truth:
  `repo_surface_configured=27`, `session_callable=2`,
  `operationally_proven=0`, `DB_BACKED=0`.
- Surface parity here means the configured repo surface is now mapped back to
  #3481. It does **not** mean that every exposed tool is live-proven callable,
  operationally proven, or DB-backed.
- `session_callable` is intentionally narrower than repo surface exposure and is
  not a DB-backed claim.
- `operationally_proven=0` remains the canonical status for this surface.
- `DB_BACKED_READONLY_PROVEN` remains out of scope for #3481 and requires
  separate adapter/record evidence.

## Matrix

| Tool | Family | Repo | Exposed | Callable | Operational | Decision | Allowed Mode | Mutation Risk | Handler |
|------|--------|------|---------|----------|-------------|----------|--------------|---------------|---------|
| cdb_agent_os_readiness | cdb_context_registry | Y | Y | CALLABLE | DB_BACKED_READONLY_UNPROVEN | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| cdb_context_architect_signals | cdb_context_registry | Y | Y | CALLABLE | DB_BACKED_READONLY_UNPROVEN | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| cdb_context_briefing | cdb_context_registry | Y | Y | CALLABLE | DB_BACKED_READONLY_UNPROVEN | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| cdb_context_claim_resolve | cdb_context_registry | Y | Y | CALLABLE | DB_BACKED_READONLY_UNPROVEN | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| cdb_context_contradictions | cdb_context_registry | Y | Y | CALLABLE | DB_BACKED_READONLY_UNPROVEN | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| cdb_context_decision_history | cdb_context_registry | Y | Y | CALLABLE | DB_BACKED_READONLY_UNPROVEN | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| cdb_context_decision_replay | cdb_context_registry | Y | Y | CALLABLE | DB_BACKED_READONLY_UNPROVEN | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| cdb_context_evidence_resolve | cdb_context_registry | Y | Y | CALLABLE | DB_BACKED_READONLY_UNPROVEN | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| cdb_context_impact | cdb_context_registry | Y | Y | CALLABLE | CONTRACT_READONLY | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| cdb_context_memory_get | cdb_context_registry | Y | Y | CALLABLE | DB_BACKED_READONLY_UNPROVEN | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| cdb_context_memory_write_intent | cdb_context_registry | Y | Y | CALLABLE | DB_BACKED_READONLY_UNPROVEN | ALLOWED_READONLY | dry_run_only | dry_run_gate | tools/mcp/context_bridge.py |
| cdb_context_quality_score | cdb_context_registry | Y | Y | CALLABLE | DB_BACKED_READONLY_UNPROVEN | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| cdb_context_scope_drift | cdb_context_registry | Y | Y | CALLABLE | DB_BACKED_READONLY_UNPROVEN | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| cdb_context_stale | cdb_context_registry | Y | Y | CALLABLE | DB_BACKED_READONLY_UNPROVEN | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| cdb_context_trust_summary | cdb_context_registry | Y | Y | CALLABLE | DB_BACKED_READONLY_UNPROVEN | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| cdb_control_room_view | cdb_context_registry | Y | Y | CALLABLE | DB_BACKED_READONLY_UNPROVEN | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| context.briefing | cdb_context_registry | Y | Y | CALLABLE | DB_BACKED_READONLY_UNPROVEN | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| context.explain_source | cdb_context_registry | Y | Y | CALLABLE | IN_MEMORY_READONLY | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| context.package | cdb_context_registry | Y | Y | CALLABLE | IN_MEMORY_READONLY | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| context.readiness | cdb_context_registry | Y | Y | CALLABLE | IN_MEMORY_READONLY | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| context.required_reads | cdb_context_registry | Y | Y | CALLABLE | CONTRACT_READONLY | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| context.search | cdb_context_registry | Y | Y | CALLABLE | CONTRACT_READONLY | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| context.self_explain | cdb_context_registry | Y | Y | CALLABLE | CONTRACT_READONLY | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| context.show_audit | cdb_context_registry | Y | Y | CALLABLE | CONTRACT_READONLY | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| context.show_snapshot | cdb_context_registry | Y | Y | CALLABLE | CONTRACT_READONLY | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| context.stop_resolver | cdb_context_registry | Y | Y | CALLABLE | CONTRACT_READONLY | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| context.trace | cdb_context_registry | Y | Y | CALLABLE | IN_MEMORY_READONLY | ALLOWED_READONLY | read_only | none | tools/mcp/context_bridge.py |
| cdb_context_package | cdb_repo_contract_alias | Y | - | NOT_EXPOSED | NOT_EXPOSED | FUTURE | read_only | none | - |
| cdb_context_search | cdb_repo_contract_alias | Y | - | NOT_EXPOSED | NOT_EXPOSED | FUTURE | read_only | none | - |
| cdb_context_trace | cdb_repo_contract_alias | Y | - | NOT_EXPOSED | NOT_EXPOSED | FUTURE | read_only | none | - |
| create | surrealdb_builtin_mcp | - | - | FORBIDDEN | FORBIDDEN_MUTATION | FORBIDDEN_MUTATION | none | direct_mutation | - |
| delete | surrealdb_builtin_mcp | - | - | FORBIDDEN | FORBIDDEN_MUTATION | FORBIDDEN_MUTATION | none | direct_mutation | - |
| info | surrealdb_builtin_mcp | - | - | NOT_EXPOSED | BLOCKED_RAW_MCP | BLOCKED | none | raw_read_surface | - |
| insert | surrealdb_builtin_mcp | - | - | FORBIDDEN | FORBIDDEN_MUTATION | FORBIDDEN_MUTATION | none | direct_mutation | - |
| list | surrealdb_builtin_mcp | - | - | NOT_EXPOSED | BLOCKED_RAW_MCP | BLOCKED | none | raw_read_surface | - |
| query | surrealdb_builtin_mcp | - | - | NOT_EXPOSED | BLOCKED_RAW_MCP | BLOCKED | none | raw_query_write_capable | - |
| relate | surrealdb_builtin_mcp | - | - | FORBIDDEN | FORBIDDEN_MUTATION | FORBIDDEN_MUTATION | none | direct_mutation | - |
| run | surrealdb_builtin_mcp | - | - | FORBIDDEN | FORBIDDEN_MUTATION | FORBIDDEN_MUTATION | none | function_execution | - |
| select | surrealdb_builtin_mcp | - | - | NOT_EXPOSED | BLOCKED_RAW_MCP | BLOCKED | none | raw_read_surface | - |
| update | surrealdb_builtin_mcp | - | - | FORBIDDEN | FORBIDDEN_MUTATION | FORBIDDEN_MUTATION | none | direct_mutation | - |
| upsert | surrealdb_builtin_mcp | - | - | FORBIDDEN | FORBIDDEN_MUTATION | FORBIDDEN_MUTATION | none | direct_mutation | - |
| use | surrealdb_builtin_mcp | - | - | NOT_EXPOSED | BLOCKED_RAW_MCP | BLOCKED | none | session_context_switch | - |

## Evidence Sources

- Repo: `tools/mcp/registry.py`, `tools/mcp/context_bridge.py`, `tools/mcp/permission_guard.py`
- Inventory: `artifacts/context_tool_inventory/tool_inventory.json`
- Contracts: `docs/surrealdb/context-intelligence-permission-matrix-v0.md`, `docs/surrealdb/context-mcp-bridge-contract.md`
- Official SurrealDB MCP: `https://surrealdb.com/docs/build/ai-agents/mcp`
- Official SurrealDB Agent Skills: `https://surrealdb.com/docs/build/ai-agents/agent-skills`
- Official SurrealDB Agent Rules: `https://surrealdb.com/docs/build/ai-agents/agent-rules`

## Guardrails

- No DB/MCP writes are authorized by this document.
- `callable_status`, `exposed`, `repo_present`, and `operational_status` stay separate fields.
- No `DB_BACKED_READONLY_PROVEN` claim is emitted without adapter evidence.
- LR remains NO-GO.
