# CDB Context Tool Inventory

Generated: 27 tools discovered from repo sources.

## Summary

| Signal | Count |
|--------|-------|
| Total tools | 27 |
| DB_BACKED | 0 |
| IN_MEMORY | 4 |
| CONTRACT_ONLY | 23 |
| REPO_ONLY | 0 |
| PROOF_ONLY | 0 |
| UNKNOWN | 0 |
| repo_surface_configured | 27 |
| session_callable | 2 |
| operationally_proven | 0 |

Session-callable means the tool was proven callable in this session. It is not a DB-backed or operational claim.

## Matrix

| Tool | Purpose | Handler | Registry | Handler status | Exposure | Callable | Operational | Evidence level | Backing | ChatGPT | OpenCode | Cursor | Claude | Codex |
|------|---------|---------|----------|----------------|----------|----------|-------------|----------------|---------|---------|----------|--------|-------|-------|
| cdb_agent_os_readiness | Wave-20 Agent OS Readiness Evaluator v1. Evaluates | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| cdb_context_architect_signals | Detect proactive architect signals from a context  | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| cdb_context_briefing | Alias for context.briefing. Generate a task-specif | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| cdb_context_claim_resolve | Wave-14 claim resolve MCP tool. Resolves claims ov | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| cdb_context_contradictions | Wave-15 contradiction scan MCP tool. Detects contr | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| cdb_context_decision_history | Wave-14 decision history MCP tool. Queries decisio | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| cdb_context_decision_replay | Wave-14 decision replay MCP tool. Builds a decisio | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| cdb_context_evidence_resolve | Wave-14 evidence resolve MCP tool. Resolves eviden | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| cdb_context_impact | Impact Radar v1 MCP tool. Analyses downstream effe | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| cdb_context_memory_get | Wave-14 scoped memory read MCP tool. Reads agent m | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| cdb_context_memory_write_intent | Memory write intent gate MCP tool (dry-run default | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| cdb_context_quality_score | Score the quality of a knowledge context bundle ac | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| cdb_context_scope_drift | Wave-17-C scope drift MCP tool. Detects scope drif | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| cdb_context_stale | Wave-16-C stale context MCP tool. Detects stale kn | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| cdb_context_trust_summary | Wave-14 trust summary MCP tool. Builds a trust ass | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| cdb_control_room_view | Wave-19 Visual Control Room View Builder v1. Build | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| context.briefing | Generate a task-specific Agent Briefing v1 from Br | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| context.explain_source | Explain the provenance and reasoning behind a spec | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | IN_MEMORY | - | Y | Y | Y | - |
| context.package | Package context artifacts for handoff between agen | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | IN_MEMORY | - | Y | Y | Y | - |
| context.readiness | Assess agent action readiness for a given task sco | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | session_callable | not_proven | session_live_call | IN_MEMORY | - | Y | Y | Y | - |
| context.required_reads | Resolve prioritized required reads from task scope | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | session_callable | not_proven | session_live_call | CONTRACT_ONLY | - | Y | Y | Y | - |
| context.search | Search the Context Intelligence knowledge base usi | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| context.self_explain | Generate a structured self-explanation for governa | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| context.show_audit | Show deterministic registry audit snapshot for a t | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| context.show_snapshot | Show a point-in-time snapshot of the context state | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| context.stop_resolver | Resolve flat stop-condition strings to typed stop  | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | CONTRACT_ONLY | - | Y | Y | Y | - |
| context.trace | Trace decision or event lineage through the Contex | tools/mcp/registry.py | registered | not_implemented | repo_surface_configured | not_proven | not_proven | repo_surface_config | IN_MEMORY | - | Y | Y | Y | - |

## Classification
- **present**: cdb_agent_os_readiness, cdb_context_architect_signals, cdb_context_briefing, cdb_context_claim_resolve, cdb_context_contradictions, cdb_context_decision_history, cdb_context_decision_replay, cdb_context_evidence_resolve, cdb_context_impact, cdb_context_memory_get, cdb_context_memory_write_intent, cdb_context_quality_score, cdb_context_scope_drift, cdb_context_stale, cdb_context_trust_summary, cdb_control_room_view, context.briefing, context.explain_source, context.package, context.readiness, context.required_reads, context.search, context.self_explain, context.show_audit, context.show_snapshot, context.stop_resolver, context.trace
- **exposed**: cdb_agent_os_readiness, cdb_context_architect_signals, cdb_context_briefing, cdb_context_claim_resolve, cdb_context_contradictions, cdb_context_decision_history, cdb_context_decision_replay, cdb_context_evidence_resolve, cdb_context_impact, cdb_context_memory_get, cdb_context_memory_write_intent, cdb_context_quality_score, cdb_context_scope_drift, cdb_context_stale, cdb_context_trust_summary, cdb_control_room_view, context.briefing, context.explain_source, context.package, context.readiness, context.required_reads, context.search, context.self_explain, context.show_audit, context.show_snapshot, context.stop_resolver, context.trace
- **callable**: context.readiness, context.required_reads
- **operational**: 

## Gaps
- 0 tools have UNKNOWN backing status.
- `session_callable` is intentionally narrower than `repo_surface_configured` and narrower than any operational or DB-backed claim.
