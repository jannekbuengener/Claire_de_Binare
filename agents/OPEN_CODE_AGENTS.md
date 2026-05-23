
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
- Für `context.briefing`-basierte Handoffs ist `briefing.session_context` die bevorzugte Kurzzeit-/Session-Handoff-Fläche für Context-, MCP-, Memory- und Evidence-Scope. Diese Fläche ist immer `working_memory` mit `session_only=true`, ist nicht als persistente DB-Memory zu behandeln und erlaubt DB-backed Brain-Claims nur bei `brain_source=surrealdb-local` und nutzbarem `brain_status` (`used` oder `partial`). `blocked` und `not-used` bleiben fail-closed.
- Brain-Evidence-Mapping aus `briefing.session_context`: `brain_source <- session_context.brain_source`, `brain_status <- session_context.brain_status`, `records_or_results <- session_context.repo_state + session_context.github_state`, `impact_on_plan <- session_context.working_assumptions + session_context.limitations`, `limitations <- session_context.limitations`. `tools_or_queries` kommen aus Caller-Tooling oder konservativ aus Session-Limitations; `repo_crosscheck` kommt aus `session_context.repo_state` plus `briefing.required_reads` und gegebenenfalls Request-Scope/Target-Pfaden.
- CDB Context MCP Capability Baseline gilt für alle Agenten-Surfaces (Codex, OpenCode, Claude/Cloud Code, Gemini, Onboarding). Die kanonische Agent-MCP-Matrix steht in `docs/runbooks/surrealdb_context_mcp_access.md` § 1.5.1 mit fünf Bewertungsebenen (Config existiert → Host kennt Config → Server startet → Tool-Inventar → Aufruf funktioniert) und den konkreten Status pro Surface.
- Danach nur task-spezifische Skills laden
- Keine pauschale Skill-Massenladung
- Third-Party-/Cybersecurity-Skills nur bei explizitem Bedarf und nur defensiv/prüfend
- Keine Writes ohne Human-GO
