# Context Intelligence — Agent Briefing Schema v1

**Issue**: [#2104](https://github.com/jannekbuengener/Claire_de_Binare/issues/2104)
**Status**: Schema Defined
**Date**: 2026-05-04
**Epic**: [#1976](https://github.com/jannekbuengener/Claire_de_Binare/issues/1976)
**Parent**: [#2018](https://github.com/jannekbuengener/Claire_de_Binare/issues/2018) (OPEN — broader briefing model; this document delivers the schema slice)
**Dependencies**: [#2097](https://github.com/jannekbuengener/Claire_de_Binare/issues/2097) (CLOSED), [#2098](https://github.com/jannekbuengener/Claire_de_Binare/issues/2098) (CLOSED)
**Guardrail**: This document defines the schema contract only. It does not implement any tool, runtime, or MCP handler.

---

## 1. Purpose & Scope

This document defines the v1 schema for **Agent Briefing Request** and **Agent Briefing Result** — the structured contract for requesting and receiving a task-specific agent briefing from the CDB Context Intelligence System (CIS).

An Agent Briefing is a **task-scoped context product** that answers: _"What does the agent need to know before starting work on this specific task?"_

The Briefing Schema v1 is a **docs-only contract artefact**. It specifies the JSON schemas, field semantics, and human-readable summary format. It does not implement any tool, runtime, or MCP handler.

---

## 2. Non-Goals

- No implementation of #2105 (Agent Briefing Tool v1)
- No Stop-Condition implementation (#2107)
- No MCP tool implementation
- No Runtime-/DB-/Trading-Scope
- No Live-/Echtgeld-Go
- No work on #2284
- No GitHub writes without GO
- No Commit/Push without separate GO

---

## 3. Relationship to #2018

Issue [#2018](https://github.com/jannekbuengener/Claire_de_Binare/issues/2018) ("Define agent briefing request/result model") defines the broader briefing model, including:

- Request/Result schema (abstract)
- Briefing depths (quick / standard / deep)
- Rules for Pflicht-Gates
- Rules for Stop Conditions
- Rules for Human-GO-Hinweise

This document (#2104) delivers the **concrete schema slice** of #2018: the normative field definitions for Briefing Request and Briefing Result v1. It does not close or resolve #2018, which remains OPEN for the remaining scope (depth rules, gate rules, stop-condition rules).

| Aspect | #2018 (Parent) | #2104 (This Document) |
|--------|---------------|----------------------|
| Request/Result schema | Defined abstractly | Defined concretely (JSON) |
| Briefing depths (quick/standard/deep) | Specified | Referenced via `requested_depth` |
| Gate rules | Specified | Referenced via `stop_conditions`, `guardrails` |
| Human-GO rules | Specified | Referenced via `human_go_required` |
| Example briefings | Required | Out of scope (follow-up in #2105) |

**Out-of-scope parent fields**: The following fields appear in #2018's abstract model but are **not** included in the normative v1 schema slice. They remain as future extensions tracked by #2018:

| Field | #2018 Location | Reason for Exclusion |
|-------|---------------|---------------------|
| `relevant_memory` | Briefing Result | Memory-handoff semantics not yet finalised (#2121 OPEN); premature for v1 schema |
| `recommended_validation` | Briefing Result | Superseded by `validation_plan` in #2104 (see §6.2 field semantics) |

---

## 4. Briefing Request Schema

### 4.1 JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Agent Briefing Request v1",
  "type": "object",
  "required": [
    "task_id",
    "task_scope",
    "target_issue",
    "requested_depth",
    "operation_mode"
  ],
  "properties": {
    "task_id": {
      "type": "string",
      "description": "Unique task identifier. Convention: 'cdb-briefing-<issue>-<short-slug>'."
    },
    "target_issue": {
      "type": ["string", "null"],
      "description": "GitHub issue number driving the task, or null for exploratory work."
    },
    "task_scope": {
      "type": "string",
      "description": "What the agent is asked to do (one concise sentence)."
    },
    "target_paths": {
      "type": "array",
      "items": { "type": "string" },
      "description": "File paths or glob patterns in scope. May be empty if task is not path-bound.",
      "default": []
    },
    "target_symbols": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Code symbols (functions, classes, modules) relevant to the task.",
      "default": []
    },
    "target_concepts": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Domain concepts from the CIS ontology relevant to the task.",
      "default": []
    },
    "requested_depth": {
      "type": "string",
      "enum": ["quick", "standard", "deep"],
      "description": "Briefing depth. quick: summary only. standard: summary + key artifacts + stop conditions. deep: full context package."
    },
    "operation_mode": {
      "type": "string",
      "enum": [
        "read_only",
        "dry_run",
        "write (code/docs)",
        "write (config/infra)",
        "write (DB/migration)",
        "write (MCP live)"
      ],
      "description": "Intended agent operation mode. Determines required guardrail surface."
    },
    "agent_type": {
      "type": "string",
      "description": "Agent identifier (e.g. 'OPENCODE/codex', 'GEMINI', 'CLAUDE')."
    },
    "risk_level": {
      "type": "string",
      "enum": ["low", "medium", "high"],
      "description": "Pre-assessed risk level of the task.",
      "default": "medium"
    }
  },
  "additionalProperties": false
}
```

### 4.2 Field Semantics

| Field | Required | Type | Semantics |
|-------|:--------:|------|-----------|
| `task_id` | Yes | `string` | Unique, deterministic task identifier. Used for idempotent briefing generation. Convention: `cdb-briefing-<issue>-<short-slug>`. |
| `target_issue` | Yes | `string \| null` | GitHub issue number (e.g. `"#2104"`) or `null` for exploratory / non-issue tasks. Used to pull issue body as primary scope source. |
| `task_scope` | Yes | `string` | One concise sentence describing the agent's task. This is the primary scope anchor for all downstream checks. |
| `target_paths` | No | `string[]` | File paths or glob patterns the task touches. Empty if task is concept-driven. |
| `target_symbols` | No | `string[]` | Code symbols (function names, class names, module paths) within the task's scope. Drives symbol resolution in the Context Package. |
| `target_concepts` | No | `string[]` | Domain concepts from the CIS ontology. Drives concept-based retrieval in the Context Package. |
| `requested_depth` | Yes | `enum` | `"quick"`: scope summary + required reads + stop conditions. `"standard"`: key artifacts, evidence, guardrails (default for most tasks). `"deep"`: full context package with dependency paths, decisions, evidence bundle. |
| `operation_mode` | Yes | `enum` | Determines guardrail surface. `read_only` and `dry_run` are lower-risk; any `write` mode triggers `human_go_required: true` and mandatory impact report. |
| `agent_type` | No | `string` | Identifies the requesting agent for attribution and trust-score routing. Defaults to agent's self-declared identity. |
| `risk_level` | No | `enum` | Pre-assessed risk. Drives briefing detail and stop-condition sensitivity. Default: `"medium"`. |

---

## 5. Briefing Result Schema

### 5.1 JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Agent Briefing Result v1",
  "type": "object",
  "required": [
    "briefing_id",
    "scope_summary",
    "human_go_required",
    "guardrails",
    "stop_conditions"
  ],
  "properties": {
    "briefing_id": {
      "type": "string",
      "description": "Deterministic briefing identifier. Derived from request fields (hash-based)."
    },
    "scope_summary": {
      "type": "string",
      "description": "Human-readable summary of the task scope, applicable constraints, and briefing coverage."
    },
    "context_package_ref": {
      "type": ["string", "null"],
      "description": "Reference (package_id) to the assembled Context Package (#2016 v1 doc, #2798 v2 envelope), or null if no package was produced. v2 schema: docs/surrealdb/context-package-model-v2.md."
    },
    "required_reads": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Canonical files the agent MUST read before taking any action. Minimum baseline per #2021 §6.3.",
      "default": []
    },
    "relevant_artifacts": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "type": { "type": "string", "enum": ["decision", "evidence", "memory", "briefing", "doc"] },
          "title": { "type": "string" },
          "source_ref": { "type": "string" },
          "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
        },
        "required": ["id", "type", "title", "source_ref"]
      },
      "description": "Key artifacts relevant to the task, drawn from the Context Package.",
      "default": []
    },
    "relevant_symbols": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "symbol_name": { "type": "string" },
          "symbol_type": { "type": "string", "enum": ["function", "class", "variable", "module"] },
          "file_path": { "type": "string" },
          "definition": { "type": "string" },
          "dependents": { "type": "array", "items": { "type": "string" } }
        },
        "required": ["symbol_name", "symbol_type", "file_path"]
      },
      "description": "Code symbols within the task scope, with dependency information.",
      "default": []
    },
    "relevant_docs": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "doc_id": { "type": "string" },
          "title": { "type": "string" },
          "path": { "type": "string" },
          "summary": { "type": "string" }
        },
        "required": ["doc_id", "title", "path"]
      },
      "description": "Technical documentation (runbooks, architecture maps, READMEs) relevant to the task.",
      "default": []
    },
    "relevant_decisions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "decision_id": { "type": "string" },
          "agent": { "type": "string" },
          "decision": { "type": "string" },
          "outcome": { "type": "string", "enum": ["approved", "rejected", "escalated"] },
          "timestamp": { "type": "string", "format": "date-time" }
        },
        "required": ["decision_id", "agent", "decision", "outcome"]
      },
      "description": "Historical governance/audit decisions relevant to the task.",
      "default": []
    },
    "relevant_evidence": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "evidence_id": { "type": "string" },
          "claim": { "type": "string" },
          "strength": { "type": "string", "enum": ["low", "medium", "high"] },
          "source_ref": { "type": "string" }
        },
        "required": ["evidence_id", "claim", "strength", "source_ref"]
      },
      "description": "Evidence-backed claims relevant to core task assumptions.",
      "default": []
    },
    "dependency_paths": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "from": { "type": "string" },
          "to": { "type": "string" },
          "relationship": { "type": "string" }
        },
        "required": ["from", "to", "relationship"]
      },
      "description": "Dependency edges showing how task components relate to each other and to external systems.",
      "default": []
    },
    "known_risks": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Risks identified during context assembly that the agent should be aware of.",
      "default": []
    },
    "guardrails": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Active constraints the agent must obey during task execution.",
      "minItems": 1
    },
    "stop_conditions": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Conditions that would require the agent to abort the task immediately.",
      "minItems": 1
    },
    "validation_plan": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "step": { "type": "string" },
          "method": { "type": "string" },
          "evidence_required": { "type": "string" }
        },
        "required": ["step", "method"]
      },
      "description": "Structured validation plan for task completion. This is the #2104-specific form of the #2018 'recommended_validation' concept — a step-by-step plan instead of a generic recommendation.",
      "default": []
    },
    "unresolved_questions": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Questions that could not be resolved from available context and may affect task outcome.",
      "default": []
    },
    "human_go_required": {
      "type": "boolean",
      "description": "true if the task requires explicit human approval before any write action."
    }
  },
  "additionalProperties": false
}
```

### 5.2 Field Semantics

| Field | Required | Type | Semantics |
|-------|:--------:|------|-----------|
| `briefing_id` | Yes | `string` | Deterministic briefing identifier, derived as a hash of request fields. Enables idempotent retrieval and replay-verifiability. |
| `scope_summary` | Yes | `string` | Human-readable paragraph summarising what the task is about, what context was found, and what constraints apply. |
| `context_package_ref` | No | `string \| null` | Reference (package_id) to the Context Package assembled for this briefing (#2016 v1 model, #2798 v2 envelope — see `docs/surrealdb/context-package-model-v2.md`). `null` if no package was produced (e.g. for quick depth). |
| `required_reads` | No | `string[]` | Ordered list of canonical files the agent must read. Minimum baseline per #2021 §6.3: AGENTS.md, agents/AGENTS.md, agents/OPEN_CODE_AGENTS.md, CONTROL_REGISTER.md, CURRENT_STATUS.md, LR-AUDIT-STATUS. |
| `relevant_artifacts` | No | `object[]` | Key context artefacts matching the task scope. Each artefact carries a source_ref and confidence score. |
| `relevant_symbols` | No | `object[]` | Code symbols (functions, classes, modules) in scope, with file paths and dependency lists. |
| `relevant_docs` | No | `object[]` | Technical documentation files (runbooks, architecture maps, READMEs) relevant to the task. Distinct from decisions (governance) and evidence (test results/run artefacts). |
| `relevant_decisions` | No | `object[]` | Governance decisions from the audit trail that affect or constrain the task. |
| `relevant_evidence` | No | `object[]` | Evidence-backed claims (test results, run artefacts, soak reports) supporting core assumptions. |
| `dependency_paths` | No | `object[]` | Directed edges showing how task components relate. Format: `{from, to, relationship}`. Enables impact analysis. |
| `known_risks` | No | `string[]` | Risks identified during context assembly (e.g. "timeout root cause not confirmed", "test coverage unknown"). |
| `guardrails` | Yes | `string[]` | Non-negotiable constraints. Minimum: "Briefing is context, not authorisation", "No Runtime write", "No Live/Echtgeld Go". |
| `stop_conditions` | Yes | `string[]` | Mandatory abort conditions per #2021 §9. Minimum: Stop on missing scope, missing evidence, scope drift, write without Human-GO. |
| `validation_plan` | No | `object[]` | Structured, step-by-step validation plan with method and evidence requirements per step. This is the #2104-specific form of #2018's `recommended_validation` field — a concrete, actionable plan instead of a generic recommendation. |
| `unresolved_questions` | No | `string[]` | Explicit unknowns that could affect task outcome. Must be surfaced, not suppressed (per #2021 §6.8). |
| `human_go_required` | Yes | `boolean` | `true` if any write operation (`write (code/docs)`, `write (config/infra)`, `write (DB/migration)`, `write (MCP live)`) is requested, if the task touches Trading/Risk/Execution scope, or if LR/Echtgeld claims are involved (#2021 §6.7). |

---

## 6. Human-Readable Summary Template

Every Briefing Result SHOULD include a human-readable summary section, derived from the structured JSON, with this Markdown format:

```markdown
# Agent Briefing: <briefing_id>

**Task**: <task_id> — <task_scope>
**Target Issue**: <target_issue | "exploratory">
**Depth**: <quick | standard | deep>
**Operation Mode**: <operation_mode>
**Human-GO Required**: <true | false>

---

## Scope Summary

<scope_summary>

---

## Required Reads

1. <required_reads[0]>
2. <required_reads[1]>
...

---

## Key Artifacts

| ID | Type | Title | Confidence |
|----|------|-------|------------|
| ... | ... | ... | ... |

---

## Key Symbols

| Symbol | Type | File | Dependents |
|--------|------|------|------------|
| ... | ... | ... | ... |

---

## Relevant Documentation

- <title> — <path>

---

## Relevant Decisions

| Decision | Agent | Outcome | Timestamp |
|----------|-------|---------|-----------|
| ... | ... | ... | ... |

---

## Relevant Evidence

| Claim | Strength | Source |
|-------|----------|--------|
| ... | ... | ... |

---

## Dependency Paths

- `<from>` → `<to>` (`<relationship>`)

---

## Known Risks

- <risk>

---

## Guardrails

- <guardrail>

---

## Stop Conditions

- <stop_condition>

---

## Validation Plan

1. **<step>**: <method> — Evidence: <evidence_required>
2. ...

---

## Unresolved Questions

- <question>
```

---

## 7. Guardrails

This schema is governed by the following non-negotiable guardrails:

| # | Guardrail |
|---|-----------|
| G1 | **Briefing is context, not authorisation.** A briefing result describes what the agent needs to know; it does not grant permission to act. |
| G2 | **No Runtime write.** Briefing generation does not modify any running service, container, or process. |
| G3 | **No MCP tool.** This document defines a schema contract. It does not implement any MCP tool, handler, or endpoint. |
| G4 | **No DB / Migration scope.** Briefing generation does not write to SurrealDB, PostgreSQL, Redis, or any other persistence layer. |
| G5 | **No Trading / Risk / Execution scope.** Briefing content must not make or imply trading, risk, or execution decisions. |
| G6 | **No Live / Echtgeld Go.** Briefing must not derive, suggest, or imply any Live-Readiness or Echtgeld authorisation. |
| G7 | **LR remains NO-GO.** The canonical Live-Readiness verdict is exclusively in `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`. This schema does not modify it. |
| G8 | **Deterministic briefing_id.** `briefing_id` is derived from request field hashes. Same request → same briefing_id. |
| G9 | **Source attribution required.** All artefacts, evidence, and docs in the briefing must carry traceable `source_ref` fields. |
| G10 | **Uncertainty must be surfaced.** Known unknowns must appear in `unresolved_questions`. Suppressing uncertainty is a contract violation. |

---

## 8. LR-Status

**LR remains NO-GO.**

This schema contract is documentation-only. It does not:

- Enable live trading
- Modify risk controls
- Change execution behaviour
- Authorise live capital
- Alter the LR verdict in `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`

---

## 9. References

| Reference | Description |
|-----------|-------------|
| [#2104](https://github.com/jannekbuengener/Claire_de_Binare/issues/2104) | This issue — Land agent briefing schema v1 |
| [#2018](https://github.com/jannekbuengener/Claire_de_Binare/issues/2018) | Parent — Define agent briefing request/result model (OPEN) |
| [#2097](https://github.com/jannekbuengener/Claire_de_Binare/issues/2097) | Dependency — Implement context package v0 (CLOSED) |
| [#2098](https://github.com/jannekbuengener/Claire_de_Binare/issues/2098) | Dependency — Implement agent readiness check v0 (CLOSED) |
| [#2016](https://github.com/jannekbuengener/Claire_de_Binare/issues/2016) | Context Package Model v1 — Package structure referenced by `context_package_ref` |
| [#2017](https://github.com/jannekbuengener/Claire_de_Binare/issues/2017) | Context Tool Contracts v1 — Tool contracts including `context.briefing` |
| [#2021](https://github.com/jannekbuengener/Claire_de_Binare/issues/2021) | Agent Action Readiness Contract — Required inputs, checks, output contract, stop rules |
| [#2032](https://github.com/jannekbuengener/Claire_de_Binare/issues/2032) | Agent OS Readiness Criteria — OS readiness stages and criteria catalogue |
| [#1976](https://github.com/jannekbuengener/Claire_de_Binare/issues/1976) | Epic — CDB Context Intelligence System |
| `docs/surrealdb/context-package-model-v1.md` | Context Package schema, lifecycle, bounds |
| `docs/surrealdb/context-tool-contracts-v1.md` | Context Tool contracts (context.briefing, context.package, etc.) |
| `docs/surrealdb/context-action-readiness-contract.md` | Agent Action Readiness contract (required inputs, output, stop rules, Human-GO rules) |
| `docs/surrealdb/context-agent-os-readiness-criteria.md` | Agent OS Readiness criteria catalogue (7 stages, minimum tooling, gates) |
| `docs/runbooks/CONTROL_REGISTER.md` | Board Stage: `trade-capable`, LR: NO-GO |
| `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | Live-Readiness SSOT: NO-GO |

---

## 10. Validation

This schema was validated against:

| Check | Status | Evidence |
|-------|:------:|----------|
| Field alignment with #2104 body | PASS | All 10 Request fields and 16 Result fields from issue body are present. |
| No #2018-exclusive fields in normative scope | PASS | `relevant_memory` excluded (future extension). `recommended_validation` explained as superseded by `validation_plan`. |
| `validation_plan` explained as #2104-form of `recommended_validation` | PASS | Field semantics in §5.2 explicitly document the relationship. |
| Alignment with #2021 required inputs | PASS | `task_scope`, `target_issue`, `target_paths`, `operation_mode`, `context_package_ref`, `required_reads`, `stop_conditions` all present. |
| Alignment with #2016 context package model | PASS | `context_package_ref` references package; `relevant_artifacts`, `relevant_symbols`, `dependency_paths` match package content types. |
| JSON Schema structural consistency | PASS | Both Request and Result schemas use `additionalProperties: false`, proper `required` arrays, `enum` constraints. |
| Guardrails explicitly documented | PASS | §7 lists 10 non-negotiable guardrails (G1–G10) with explicit No-Live/Echtgeld-Go and LR-NO-GO statements. |
| LR-NO-GO explicitly stated | PASS | §8 reaffirms LR NO-GO; schema does not modify `LR-AUDIT-STATUS`. |
| Human-readable summary template present | PASS | §6 provides Markdown template with all briefing fields mapped. |
| #2018 remains marked as OPEN | PASS | Header and §3 explicitly state #2018 is OPEN; schema does not claim resolution. |

---

## 11. Residual Uncertainties

| # | Uncertainty | Mitigation |
|---|-------------|------------|
| U1 | The `task_id` convention (`cdb-briefing-<issue>-<short-slug>`) is proposed, not ratified by #2018. | Documented as convention. Can be adjusted when #2018 closes. |
| U2 | `requested_depth: "deep"` may require the full Context Package, which may not yet be available for all task domains. | Schema allows `context_package_ref: null` as valid output even for deep depth, with `unresolved_questions` signalling the gap. |
| U3 | The interaction between this schema and the existing `context.briefing` tool (#2017 §8) is not specified. | The `context.briefing` tool generates system-status briefings, not task-specific agent briefings. A future tool (#2105) will implement this schema. |
| U4 | `relevant_memory` is excluded from v1 but referenced in #2018. | Explicitly marked as future extension in §3. Will be added when memory-handoff semantics (#2121) are finalised. |

---

## Files Changed

- `docs/surrealdb/context-agent-briefing-schema-v1.md` (new)
