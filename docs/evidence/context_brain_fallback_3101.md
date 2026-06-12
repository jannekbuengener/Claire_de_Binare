# Context Brain Fallback Classification — #3101

**Date:** 2026-06-12
**Issue:** [#3101](https://github.com/jannekbuengener/Claire_de_Binare/issues/3101)
**Status:** Evidence / Classification
**Class:** Diagnosis (docs-only, no code/runtime/DB change)

---

## 1. Summary

ARVP/CDB agent sessions repeatedly report `brain_source=repo-only` / `brain_status=not-used`
in the Brain Evidence Block. This document diagnoses the root cause, classifies the failure
mode, and confirms that **no code or tool routing fix is required**: the behavior is the
intentional default posture per governance decision #2775.

---

## 2. Brain Evidence

```
brain_source: repo-only
brain_status: used (repo + gh evidence; no DB-backed claims)
tools_or_queries:
  - context.briefing (task_id=cdb-briefing-3101-context-brain-fallback)
  - context.readiness (task_scope + target_issue=3101)
  - gh issue view 3101/3095/3087/1900
  - gh pr list --state open
records_or_results:
  - context.briefing → briefing_id=6464adc0fcd12aa1, brain_source=repo-only, db_claims_allowed=false
  - context.readiness → blocked_missing_context, human_go_required=true
  - All 27 cdb_context MCP tools are registered and callable (in-memory/noop mode)
repo_crosscheck:
  - agents/AGENTS.md § Brain Evidence Gate
  - knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md (#2775)
  - docs/runbooks/surrealdb_context_mcp_access.md §1.5
  - docs/evidence/context_tooling/CDB_CONTEXT_TOOLING_BENCHMARK_2026-06-03.md
  - docs/evidence/arvp_volatility_window_campaign_3095_1r.md (brain_source=repo-only)
impact_on_plan:
  - No code/tool routing change needed — repo-only is the intentional default
  - This document serves as the canonical answer for future "why repo-only?" questions
limitations:
  - No SurrealDB-local query used (adapter_config_path not passed)
  - No enrichment records provided to context.briefing
  - caller-supplied brain_source/metadata.source are not used as evidence
```

---

## 3. Bootloader / Read-Order Evidence

| # | File | Read | Status |
|---|------|------|--------|
| 1 | AGENTS.md (root pointer) | ✓ | Canonical pointer to agents/AGENTS.md |
| 2 | agents/AGENTS.md | ✓ | Brain Evidence Gate + read order |
| 3 | agents/OPEN_CODE_AGENTS.md | ✓ | Skill routing + Brain Evidence contract |
| 4 | knowledge/governance/CDB_CONSTITUTION.md | ✓ | Governance constitution |
| 5 | knowledge/governance/CDB_GOVERNANCE.md | ✓ | Governance rules |
| 6 | knowledge/governance/CDB_AGENT_POLICY.md | ✓ | Agent policy §4 (write gates) |
| 7 | knowledge/governance/SYSTEM_INVARIANTS.md | ✓ | System invariants |
| 8 | knowledge/CDB_KNOWLEDGE_HUB.md | ✓ | Knowledge hub |
| 9 | docs/meta/WORKING_REPO_CANON.md | ✓ | Working repo canon |
| 10 | CURRENT_STATUS.md | ✓ | Ledger (not live truth) |
| 11 | docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md | ✓ | LR NO-GO |
| 12 | docs/runbooks/CONTROL_REGISTER.md | ✓ | Board stage: trade-capable |
| 13 | knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md | ✓ | **Default posture SSOT** |

All required reads from the canonical read order in agents/AGENTS.md were completed.

---

## 4. Live GitHub Evidence

| Issue | # | State | Title |
|-------|---|-------|-------|
| Target | 3101 | **OPEN** | Resolve repo-only Brain fallback in ARVP campaign sessions |
| Parent | 3095 | **CLOSED** | Run scheduled volatility-window campaign for primary_breakout_v1 |
| Blocker | 3087 | **CLOSED** | Produce longer comparison-grade paper reference window(s) |
| Epic | 1900 | **OPEN** | ARVP to its product intent: accelerated replay paper-mode |

- No open PRs on the repo
- HEAD == origin/main (`84f6b77`)

---

## 5. Current Context Tooling Posture

### 5.1 MCP Tool Availability

The `cdb_context` MCP tools are **available and callable** in the active MCP surface:

- **27 tools** registered, all declaring `readOnly=true`
- Tools include: `context.briefing`, `context.readiness`, `context.search`,
  `context.impact`, `cdb_context_evidence_resolve`, `cdb_context_memory_get`, etc.
- Live invocation proof: Benchmark #2 (2026-06-03) confirmed all 27 tools respond to real dispatch

### 5.2 Adapter Mode

The tools operate in **in-memory/noop mode** unless `adapter_config_path` is explicitly
passed. The default adapter is `NoopQueryAdapter`:

| Condition | Adapter | DB-backed claims |
|-----------|---------|-----------------|
| No `adapter_config_path` | `NoopQueryAdapter` (in_memory) | **No** |
| Valid `adapter_config_path` + localhost SurrealDB reachable | `SurrealDBLocalQueryAdapter` (surrealdb-local) | **Yes** (guarded) |

### 5.3 Context Briefing Evidence

A live `context.briefing` call for this task returned:

- `status: ok` — tool is functional
- `brain_source: repo-only` — no DB backing
- `brain_status: not-used` — consistent with default posture
- `db_claims_allowed: false` — in-memory mode
- `operator_trust_level: LOW` — no enrichment records provided
- `trust_limitations`: ["No enrichment records supplied; trust synthesis is incomplete."]

### 5.4 Session Context (from briefing)

```json
{
  "memory_type": "working_memory",
  "session_only": true,
  "brain_source": "repo-only",
  "brain_status": "not-used",
  "db_claims_allowed": false
}
```

---

## 6. Failure Mode Classification

### Primary Classification

| Classification | Evidence | Confidence |
|---|---|---|
| **`intentional_governance_boundary`** | #2775 set `read_only_context_brain = conditional` with default `repo-only`/`not-used` | HIGH |
| **`expected_repo_fallback_behavior`** | Task-scope matrix in CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md confirms: "Normal repo/issue triage → repo-only/not-used" | HIGH |

### Secondary Classifications

| Classification | Evidence | Confidence |
|---|---|---|
| `context_tool_available_but_low_trust` | Tools callable but operator_trust_level=LOW without enrichment records | HIGH |
| `context_tool_available_but_no_evidence_records` | Enrichment fails because `evidence_records`, `claim_records`, `decision_events`, `memory_records` are never populated in normal sessions | HIGH |
| `surrealdb_unavailable_or_not_used` | `adapter_config_path` not passed → NoopQueryAdapter (in_memory); localhost SurrealDB may or may not be running — irrelevant without config path | HIGH |

### NOT Classified

| Classification | Why ruled out |
|---|---|
| `context_tool_unavailable` | All 27 tools are registered and dispatch real handlers |
| `profile_permissions_prevent_usage` | Tools are callable and respond with real JSON |
| `agent_prompt_missing_context_call` | Prompt contract for #3101 explicitly includes context checks |

---

## 7. Expected Brain Evidence Behavior for ARVP Sessions

### 7.1 Current State (Intentional)

ARVP campaign sessions (and all normal CDB agent sessions) are **expected** to report:

```
brain_source: repo-only
brain_status: not-used
```

This is not a regression. It is the governance-ratified default posture from #2775.
The Brain Evidence Gate is still valuable as a governance surface even in repo-only mode:
it forces agents to explicitly state their evidence sources and limitations.

### 7.2 When `brain_status=used` is valid without SurrealDB

Per `CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md` § Brain Evidence status rules:

- `repo-only` + `used` is valid when the agent uses **repo file and GitHub evidence**
  with populated `tools_or_queries` and `records_or_results` (e.g., `gh issue view`,
  `rg` pattern searches, `context.briefing` invocation)
- This has been seen in ARVP evidence docs (e.g., `arvp_option_e_waiver_split_decision_3087_3095.md`
  reports `brain_source=repo-only`, `brain_status=used`)

### 7.3 When `surrealdb-local` would be usable

For agents to report `brain_source=surrealdb-local` with `brain_status=used`:

1. `adapter_config_path` must point to a valid config (e.g.,
   `infrastructure/config/surrealdb/context_query.local.yaml`)
2. Localhost SurrealDB must be running and reachable
3. `adapter.status == "surrealdb-local"` must be verified
4. `metadata.source == "surrealdb-local"` must come from guarded adapter derivation
5. Tool/query/record evidence must populate `tools_or_queries` and `records_or_results`

**This has never been the case for ARVP campaign sessions.** The campaign sessions
did not pass `adapter_config_path`, did not run a local SurrealDB, and did not
populate enrichment records.

### 7.4 When `repo-only` would be incorrect

`repo-only` would be incorrect only if:

- An `adapter_config_path` is passed and `adapter.status == "surrealdb-local"`
- But the agent still reports `brain_source=repo-only`
- This would be a **contradiction** and must fail-closed

This scenario has **not been observed** in any ARVP campaign session.

---

## 8. Decision: Docs Clarification

### 8.1 What was decided

**No code, tool routing, or prompt contract fix is required.**

The `repo-only` fallback is the intentional default posture. The diagnosis confirms:

1. The MCP context tools are available and functional
2. They operate in in-memory mode because no `adapter_config_path` is passed
3. This is the correct behavior per governance decision #2775
4. ARVP campaign sessions are classified as "Normal repo/issue triage" in the
   task-scope matrix → `repo-only`/`not-used` is the expected posture

### 8.2 What this document provides

This document serves as the **canonical answer** for future questions about why
ARVP or other CDB agent sessions fall back to `repo-only`. It can be referenced
in Brain Evidence blocks, session logs, and issue triage.

### 8.3 Follow-up guardrails

If the maintainer decides SurrealDB-backed context should be available for ARVP
campaign sessions, that would require a **separate implementation issue** with:

- `adapter_config_path` wiring in agent prompts/tool calls
- Local SurrealDB startup as part of campaign preflight
- Enrichment record population from DB queries
- Updated task-scope matrix entry
- This is explicitly **not** in scope for #3101

---

## 9. Safety Boundaries

| Boundary | Status |
|----------|--------|
| LR remains NO-GO | ✅ Unchanged |
| No productive SurrealDB writes | ✅ No writes |
| No DB schema changes | ✅ No schema changes |
| No runtime BLUE/RED changes | ✅ No runtime changes |
| No MCP live mutations | ✅ No mutations |
| No Live-Go / Echtgeld-Go | ✅ No GO |
| No secrets in output | ✅ No secrets |
| `PERSIST_ALLOWED=False` unchanged | ✅ Unchanged |
| `MUTATION_ALLOWED=False` unchanged | ✅ Unchanged |

---

## 10. Residual Gaps

| Gap | Severity | Action |
|-----|----------|--------|
| No SurrealDB-local adapter was tested with `adapter_config_path` | Info | Not in scope for #3101; would need separate implementation issue |
| Enrichment records never populated in normal agent sessions | Info | By design — enrichment requires explicit DB opt-in |
| `operator_trust_level=LOW` is inherent in in-memory mode | Info | Not a bug — LOW trust is the correct classification for in-memory mode |

---

## 11. References

- [#3101](https://github.com/jannekbuengener/Claire_de_Binare/issues/3101) — This issue
- [#3095](https://github.com/jannekbuengener/Claire_de_Binare/issues/3095) — ARVP Campaign #1R parent
- [#3087](https://github.com/jannekbuengener/Claire_de_Binare/issues/3087) — comparison-grade paper reference window
- [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900) — ARVP North-Star Epic
- [#2775](https://github.com/jannekbuengener/Claire_de_Binare/issues/2775) — Context Brain Default Posture decision
- [CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md](../../knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md) — Default posture SSOT
- [agents/AGENTS.md](../../agents/AGENTS.md) — Brain Evidence Gate
- [surrealdb_context_mcp_access.md](../runbooks/surrealdb_context_mcp_access.md) — MCP Capability Resolution
- [CDB_CONTEXT_TOOLING_BENCHMARK_2026-06-03.md](context_tooling/CDB_CONTEXT_TOOLING_BENCHMARK_2026-06-03.md) — 27-tool benchmark
