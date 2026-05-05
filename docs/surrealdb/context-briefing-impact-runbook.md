# Context Briefing & Impact Radar Runbook

## 1. Purpose and Scope
- Part of Wave 13 (#2103–#2114) of Epic #1976 (Context Intelligence System)
- Operator/agent-facing guide for safe use of briefing and impact radar tools
- Scope: SurrealDB Context Intelligence only, no runtime/trading/live components
- Prerequisite: Completed #2110 (context briefing MCP), #2111 (impact radar MCP), #2112 (tests/fixes) — all CLOSED

## 2. Tool Overview
### context.briefing / cdb_context_briefing
- Read-only MCP tools (handlers in `tools/mcp/context_bridge.py`)
- Generates task-scoped agent briefings answering: *What does the agent need to know before starting work?*
- Schema: `docs/surrealdb/context-agent-briefing-schema-v1.md`
- `cdb_context_briefing` is an alias rewriting the tool name in output, delegates to same handler

### cdb_context_impact
- Read-only MCP tool (handler in `tools/mcp/context_bridge.py`)
- Wraps Impact Radar v1 (`tools/surrealdb/context_impact_radar.py`)
- Answers: *If I touch this, what else could break?*
- Contract: `docs/surrealdb/context-impact-radar-contract-v1.md`

## 3. When to Use Briefing vs Impact
| Use Case | Tool | Timing |
|----------|------|--------|
| Prepare for task/issue work | context.briefing | Before starting any work |
| Assess downstream change effects | cdb_context_impact | Before implementing, committing, or opening PRs |
| Get validation steps | Combine with Validation Plan (from impact output) | After impact analysis |

Recommended order: Readiness Check → Briefing → Impact Radar → Validation Plan

## 4. Required Inputs and Safe Defaults
### context.briefing
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| task_scope | str | Yes | None | Task description or issue number (e.g., "2113") |
| operation_mode | str | No | "standard" | One of: "quick", "standard", "deep" |
| target_paths | list[str] | No | [] | Specific files/symbols to focus on |
| target_issue | str | No | None | GitHub issue number (e.g., "2113") |

### cdb_context_impact
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| target_paths | list[str] | Yes | None | Paths/symbols to analyze |
| target_issue | str | No | None | Related GitHub issue |
| operation_mode | str | No | "standard" | One of: "quick", "standard", "deep" |

## 5. Example Requests
### Briefing Examples
#### Quick Briefing
```json
{
  "tool": "context.briefing",
  "task_scope": "2113",
  "operation_mode": "quick"
}
```

#### Standard Briefing (Default)
```json
{
  "tool": "context.briefing",
  "task_scope": "2113",
  "target_issue": "2113"
}
```

#### Deep Briefing
```json
{
  "tool": "context.briefing",
  "task_scope": "Implement runbook for #2113",
  "operation_mode": "deep",
  "target_paths": ["docs/surrealdb/", "tools/mcp/context_bridge.py"],
  "target_issue": "2113"
}
```

### Impact Examples
#### Low Impact (non-critical docs)
```json
{
  "tool": "cdb_context_impact",
  "target_paths": ["docs/surrealdb/context-briefing-impact-runbook.md"]
}
```

#### Medium Impact (core libraries/tests)
```json
{
  "tool": "cdb_context_impact",
  "target_paths": ["tools/surrealdb/context_required_reads.py", "tests/unit/tools/surrealdb/test_required_reads.py"]
}
```

#### High Impact (services/contracts)
```json
{
  "tool": "cdb_context_impact",
  "target_paths": ["services/risk/", "core/contracts/"]
}
```

#### Blocking Impact (governance/secrets)
```json
{
  "tool": "cdb_context_impact",
  "target_paths": ["knowledge/governance/CDB_CONSTITUTION.md", "secrets/"]
}
```

## 6. Output Interpretation
### Common Fields (Both Tools)
- **required_reads**: Prioritized list from `tools/surrealdb/context_required_reads.py` (path, priority, reason, source_ref, available, warning)
- **guardrails**: Hard limits (no live trades, no Echtgeld, no runtime writes)
- **stop_conditions**: Typed conditions (S1-S10, H1-H8) from `tools/surrealdb/context_stop_resolver.py` (type, severity, reason, required_action, human_go_required)
- **known_risks**: Pre-identified risks for the task scope
- **human_go_required**: Boolean, true if explicit human approval is needed

### Impact-Specific Fields
- **affected_items**: Artifacts/symbols/tests/docs affected by the change
- **graph_paths**: Dependency graph paths between targets and affected items
- **gate_risks**: Detected governance/risk/execution/secrets surface touches (from `context_impact_radar.py`)
- **required_validation**: ValidationPlan from `tools/surrealdb/context_validation_plan.py` (required_checks, suggested_tests, docs_to_review, evidence_to_collect)

## 7. Fail-Closed Behavior
All tools fail closed on invalid input:
- **Invalid operation_mode**: Rejects with error, no fallback to default
- **Missing/invalid task scope**: Briefing returns `available=false` + warning
- **Payload too large**: `cdb_context_briefing` truncates response with explicit warning (byte limit enforced)
- **Unknown/unparseable stop conditions**: Resolved as `scope_drift_risk` + warning (from `context_stop_resolver.py`)
- **Blocking paths touched**: Impact radar returns `impact_level=blocking` + associated gate risks

## 8. Human-GO Boundaries
- Briefing/impact tools are read-only, no writes to repo, SurrealDB, or GitHub
- Human-GO required for:
  - Any commit, push, PR creation, or label change
  - Modifying governance, risk, execution, or secrets paths
  - Overriding stop conditions or gate risks
- Tools never auto-approve, auto-commit, or auto-deploy

## 9. No Live-Go / No Echtgeld-Go / No Runtime Authorization
- These tools provide context only, no runtime/trading/live authorization
- Board-Stage `trade-capable` (ratified #1492) is orthogonal, not Live-Readiness approval
- Live-Readiness remains NO-GO per `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- No tool output implies live/paper/execution readiness

## 10. Validation Commands
```bash
# Run unit tests for briefing/impact tools
pytest -v tests/unit/tools/mcp/test_mcp_briefing_tool.py tests/unit/tools/mcp/test_mcp_impact_tool.py

# Verify tool registration in MCP bridge
rg "context.briefing|cdb_context_impact" tools/mcp/context_bridge.py

# Validate runbook covers required guardrails
rg "human_go_required|gate_risks|stop_conditions|trade-capable" docs/surrealdb/context-briefing-impact-runbook.md
```

## 11. Troubleshooting
- **Missing required reads**: Verify `AGENTS.md` → `agents/AGENTS.md` read order is followed
- **Impact level higher than expected**: Check impact directory thresholds in `tools/surrealdb/context_impact_radar.py`
- **Stop conditions not recognized**: Verify condition strings against `tools/surrealdb/context_stop_resolver.py` rule maps
- **Payload too large**: Reduce `target_paths` or use `operation_mode=quick`

## 12. Relationship to #2110, #2111, #2112
- #2110 (CLOSED): Implements `context.briefing` and `cdb_context_briefing` MCP tools
- #2111 (CLOSED): Implements `cdb_context_impact` MCP tool
- #2112 (CLOSED): Adds unit tests and fixtures for both tools
- This runbook documents operational use of the implemented tools from #2110–#2112

## 13. Explicit Statement
Board-Stage `trade-capable` is not Live-Readiness approval. Live-Readiness is governed by `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` and remains NO-GO until explicitly changed by human approval.

---

**Guardrails**: No writes, no live/echtgeld-go, no runtime authorization. This runbook is docs-only, no production code changes.
