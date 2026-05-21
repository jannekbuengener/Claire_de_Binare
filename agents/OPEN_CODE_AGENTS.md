
---
relations:
  role: doc
  domain: agents
  upstream:
    - agents/AGENTS.md
    - knowledge/governance/CDB_AGENT_POLICY.md
    - knowledge/governance/CDB_TRUST_SCORE_POLICY.md
  downstream: []
  status: active
  tags: [opencode, agents, trust]
---
# OpenCode Agents — Shared Contract

Gilt für **alle** OpenCode Agents (egal welcher Provider).

## Pflicht
- `agent_id` Format: `OPENCODE/<agent-name>`
- `provider`: `opencode`
- Decision Events nach `knowledge/agent_trust/ledger/`
- Unsicherheit markieren statt durchentscheiden

## Nicht verhandelbar
- Canon-Governance ist read-only
- Delivery-Gate / Tresor-Regeln gelten identisch

## OpenCode Skill Routing

- Bootloader immer zuerst: `AGENTS.md` -> `agents/AGENTS.md` -> `agents/OPEN_CODE_AGENTS.md`
- Für CDB-Repo-Arbeit danach `cdb-session-start`
- Danach `cdb-control-intake`
- Bei Issue-Arbeit danach `cdb-issue-to-session-plan`
- Bei Context-, SurrealDB-, MCP-Tool-, ContextBridge- oder DB-backed-Memory-Scope: MCP Capability Resolution Gate ausführen vor Implementierung oder toolabhängiger Planung — Repo-Präsenz ist nicht gleich MCP-Verfügbarkeit. Referenz: `docs/runbooks/surrealdb_context_mcp_access.md` § 1.5.
- Bei Strategy-, Runtime-, Module-, Service-, Contract-, Context-, SurrealDB-, MCP-, Memory- oder Evidence-Scope: **Brain Evidence Gate** aus `agents/AGENTS.md` § Brain Evidence Gate ausführen **vor jeder Planung** — der Agent MUSS den vollständigen Brain-Evidence-Block mit `brain_source`, `brain_status`, `tools_or_queries`, `records_or_results`, `repo_crosscheck`, `impact_on_plan` und `limitations` ausgeben.
- Danach nur task-spezifische Skills laden
- Keine pauschale Skill-Massenladung
- Third-Party-/Cybersecurity-Skills nur bei explizitem Bedarf und nur defensiv/prüfend
- Keine Writes ohne Human-GO
