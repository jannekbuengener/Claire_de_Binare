# Context Intelligence — Briefing Enrichment Model v1

**Issue**: [#2122](https://github.com/jannekbuengener/Claire_de_Binare/issues/2122)
**Status**: Schema Defined
**Date**: 2026-05-05
**Epic**: [#1976](https://github.com/jannekbuengener/Claire_de_Binare/issues/1976)
**Parent**: [#2115](https://github.com/jannekbuengener/Claire_de_Binare/issues/2115)
**Dependencies**: [#2105](https://github.com/jannekbuengener/Claire_de_Binare/issues/2105) (CLOSED), [#2116](https://github.com/jannekbuengener/Claire_de_Binare/issues/2116) (OPEN), [#2117](https://github.com/jannekbuengener/Claire_de_Binare/issues/2117) (OPEN), [#2118](https://github.com/jannekbuengener/Claire_de_Binare/issues/2118) (OPEN), [#2119](https://github.com/jannekbuengener/Claire_de_Binare/issues/2119) (OPEN), [#2120](https://github.com/jannekbuengener/Claire_de_Binare/issues/2120) (OPEN), [#2121](https://github.com/jannekbuengener/Claire_de_Binare/issues/2121) (OPEN)
**Guardrail**: This document defines the enrichment model contract only. It does not implement any tool, runtime, MCP handler, or DB query.

---

## 1. Purpose & Scope

This document defines the v1 model for **Briefing Enrichment** — extending the base Briefing Result from the Agent Briefing Builder (#2105) with Evidence, Decision History, and scoped Memory.

The Enrichment Model is a **docs-only contract artefact**. It specifies the enrichment input/output schemas, field semantics, and integration points with existing context tools.

---

## 2. Non-Goals

- No implementation of Evidence Resolution (#2020)
- No implementation of Decision History lookup
- No implementation of Memory retrieval (#2121)
- No MCP handler implementation
- No DB migration
- No Live/Echtgeld Go
- No Trading/Risk/Execution decision
- No Write operations (evidence, decision, memory)
- No Report Generator implementation
- No dependency on unauthenticated #2337 PR

---

## 3. Relationship to Existing Briefings

The Enrichment Model extends the **Agent Briefing Result Schema v1** from [#2104](https://github.com/jannekbuengener/Claire_de_Binare/issues/2104):

| Base Field (#2104) | Enrichment Extension (#2122) |
|--------------------|----------------------------|
| `relevant_decisions: []` | `enriched_decisions: [...]` (populated) |
| `relevant_evidence: []` | `enriched_evidence: [...]` (populated) |
| (none) | `enriched_memory: [...]` (read-only) |
| (none) | `trust_summary: string` (confidence synthesis) |
| `stop_conditions` | `enriched_stop_conditions` (with evidence-aware flags) |

---

## 4. Enrichment Input Schema

### 4.1 JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Briefing Enrichment Input v1",
  "type": "object",
  "required": [
    "base_briefing",
    "task_scope",
    "requested_enrichment_depth"
  ],
  "properties": {
    "base_briefing": {
      "type": "object",
      "description": "Output from Agent Briefing Builder v1 (#2105)",
      "required": ["briefing_id", "scope_summary", "task_id"]
    },
    "task_scope": {
      "type": "string",
      "description": "What the agent is asked to do (mirrored from base briefing)"
    },
    "target_issue": {
      "type": ["string", "null"],
      "description": "GitHub issue number driving the task"
    },
    "target_paths": {
      "type": "array",
      "items": { "type": "string" },
      "description": "File paths in scope",
      "default": []
    },
    "target_concepts": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Domain concepts from CIS ontology",
      "default": []
    },
    "requested_enrichment_depth": {
      "type": "string",
      "enum": ["minimal", "standard", "deep"],
      "description": "Enrichment depth. minimal: evidence only. standard: evidence + decisions. deep: full enrichment with memory hints."
    },
    "allowed_context_surfaces": {
      "type": "array",
      "items": { "type": "string" },
      "enum": ["evidence", "decisions", "memory", "all"],
      "default": ["evidence", "decisions"]
    }
  },
  "additionalProperties": false
}
```

### 4.2 Field Semantics

| Field | Required | Type | Semantics |
|-------|:--------:|------|-----------|
| `base_briefing` | Yes | `object` | Output from Agent Briefing Builder v1 (#2105). Must contain `briefing_id`, `scope_summary`, `task_id`. |
| `task_scope` | Yes | `string` | Mirrored from base briefing for context routing |
| `target_issue` | No | `string \| null` | GitHub issue driving the task |
| `target_paths` | No | `string[]` | File paths in scope for evidence routing |
| `target_concepts` | No | `string[]` | Domain concepts for concept-based retrieval |
| `requested_enrichment_depth` | Yes | `enum` | `minimal`: evidence refs only. `standard`: evidence + decisions. `deep`: full enrichment with memory hints. |
| `allowed_context_surfaces` | No | `string[]` | Context surfaces to include. Defaults to evidence+decisions. Memory requires explicit opt-in. |

---

## 5. Enrichment Output Schema

### 5.1 JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Briefing Enrichment Result v1",
  "type": "object",
  "required": [
    "enrichment_id",
    "enriched_briefing_id",
    "trust_summary",
    "enriched_decisions",
    "enriched_evidence",
    "enriched_stop_conditions"
  ],
  "properties": {
    "enrichment_id": {
      "type": "string",
      "description": "Deterministic enrichment identifier. Derived from base briefing_id + enrichment params."
    },
    "enriched_briefing_id": {
      "type": "string",
      "description": "Reference to the base briefing being enriched."
    },
    "trust_summary": {
      "type": "string",
      "description": "Human-readable synthesis of evidence quality, decision status, and memory hints."
    },
    "enriched_required_reads": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Expanded required reads with evidence-aware additions.",
      "default": []
    },
    "enriched_decisions": {
      "type": "array",
      "items": { "$ref": "#/definitions/DecisionRef" },
      "description": "Governance/audit decisions relevant to the task.",
      "default": []
    },
    "enriched_evidence": {
      "type": "array",
      "items": { "$ref": "#/definitions/EvidenceRef" },
      "description": "Evidence-backed claims supporting core assumptions.",
      "default": []
    },
    "enriched_memory": {
      "type": "array",
      "items": { "$ref": "#/definitions/MemoryRef" },
      "description": "Read-only memory hints (session context, prior work, relevant precedents).",
      "default": []
    },
    "enriched_stop_conditions": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Stop conditions with evidence-aware severity flags.",
      "default": []
    },
    "dependency_paths": {
      "type": "array",
      "items": { "type": "object" },
      "description": "Dependency edges added by enrichment.",
      "default": []
    },
    "stale_evidence_notice": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Evidence refs marked as stale (>30 days).",
      "default": []
    },
    "contradictory_evidence_notice": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Evidence refs flagged as contradictory.",
      "default": []
    },
    "missing_evidence_notice": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Evidence categories with no resolution.",
      "default": []
    }
  },
  "definitions": {
    "DecisionRef": {
      "type": "object",
      "properties": {
        "decision_id": { "type": "string" },
        "decision_type": { "type": "string", "enum": ["governance", "audit", "technical", "strategic"] },
        "decision": { "type": "string" },
        "outcome": { "type": "string", "enum": ["approved", "rejected", "escalated", "deferred"] },
        "status": { "type": "string", "enum": ["active", "superseded", "expired"] },
        "rationale_summary": { "type": "string" },
        "source_ref": { "type": "string" },
        "timestamp": { "type": "string", "format": "date-time" },
        "superseded_by": { "type": ["string", "null"] }
      },
      "required": ["decision_id", "decision", "outcome", "status", "timestamp"]
    },
    "EvidenceRef": {
      "type": "object",
      "properties": {
        "evidence_id": { "type": "string" },
        "claim": { "type": "string" },
        "strength": { "type": "string", "enum": ["weak", "medium", "strong"] },
        "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
        "source_ref": { "type": "string" },
        "source_type": { "type": "string", "enum": ["test_result", "run_artefact", "soak_report", "audit_log", "doc"] },
        "freshness": { "type": "string", "enum": ["fresh", "stale", "unknown"] },
        "contradiction_flag": { "type": "boolean" },
        "stale_flag": { "type": "boolean" }
      },
      "required": ["evidence_id", "claim", "strength", "source_ref"]
    },
    "MemoryRef": {
      "type": "object",
      "properties": {
        "memory_id": { "type": "string" },
        "memory_type": { "type": "string", "enum": ["session", "precedent", "context_hinweis"] },
        "relevance": { "type": "string", "enum": ["high", "medium", "low"] },
        "summary": { "type": "string" },
        "source": { "type": "string" },
        "source_ref": { "type": "string" },
        "freshness": { "type": "string", "enum": ["current", "historic"] },
        "privacy_constraint": { "type": ["string", "null"] }
      },
      "required": ["memory_id", "memory_type", "relevance", "summary"]
    }
  },
  "additionalProperties": false
}
```

### 5.2 Field Semantics

| Field | Required | Type | Semantics |
|-------|:--------:|------|-----------|
| `enrichment_id` | Yes | `string` | Deterministic ID: `hash(base_briefing_id + requested_enrichment_depth + timestamp)` |
| `enriched_briefing_id` | Yes | `string` | Reference to base briefing |
| `trust_summary` | Yes | `string` | Synthesis: "X evidence items (Y strong, Z weak), A decisions (B active), memory hints available" |
| `enriched_required_reads` | No | `string[]` | Additional canonical files based on evidence/decision findings |
| `enriched_decisions` | No | `object[]` | Governance/audit decisions. Status: `active` (current) or `superseded` (replace with newer) |
| `enriched_evidence` | No | `object[]` | Evidence refs with strength, confidence, freshness, contradiction flags |
| `enriched_memory` | No | `object[]` | Read-only hints only. No Memory Write. |
| `enriched_stop_conditions` | No | `string[]` | Stop conditions with evidence-aware severity (e.g., "S5: stale evidence blocks deep scope") |
| `stale_evidence_notice` | No | `string[]` | Explicit list of stale evidence IDs |
| `contradictory_evidence_notice` | No | `string[]` | Explicit list of contradictory evidence IDs |
| `missing_evidence_notice` | No | `string[]` | Missing evidence categories |

---

## 6. Error / Partial Result Behaviour

| Scenario | Behaviour |
|----------|-----------|
| **Missing evidence** | `enriched_evidence: []`, `missing_evidence_notice` populated, `trust_summary` reflects gap |
| **Stale evidence** | `stale_flag: true` per evidence item, `stale_evidence_notice` populated, stop condition added if critical |
| **Contradictory evidence** | `contradiction_flag: true`, `contradictory_evidence_notice` populated, escalation hint in stop_conditions |
| **Missing decision context** | `enriched_decisions: []`, rationale in `trust_summary` |
| **Decision superseded** | `status: superseded`, `superseded_by` reference included |
| **Memory unavailable** | `enriched_memory: []`, no error, read-only Hinweis in `trust_summary` |
| **Permission denied** | `enriched_memory: []`, `privacy_constraint` surfaced, no error |
| **Partial enrichment** | Return partial result with explicit `unresolved_questions` |

---

## 7. Security & Privacy Boundaries

| # | Boundary |
|---|----------|
| S1 | **No Memory Write** — Enrichment is read-only for memory hints |
| S2 | **No Decision Write** — Enrichment surfaces decisions, does not create them |
| S3 | **No Evidence Write** — Enrichment resolves evidence, does not create new evidence |
| S4 | **Privacy preserved** — Memory hints with `privacy_constraint` are surfaced but not expanded |
| S5 | **Stale blocks critical path** — Stale evidence on core assumptions triggers stop condition |
| S6 | **No Live Go** — Enrichment does not authorize trading/risk/execution |
| S7 | **Source attribution required** — All enrichment refs must carry `source_ref` |

---

## 8. Determinism & Audit Requirements

- **Deterministic ID**: `enrichment_id` derived from `base_briefing_id` + `requested_enrichment_depth` + hash of input params
- **Replayable**: Same input → same enrichment_id
- **Audit trail**: All evidence/decision/memory refs carry `source_ref` for traceability
- **Timestamp**: ISO 8601 ` timestamp` on decisions for freshness calculation
- **No auto-created state**: Enrichment does not write to any DB

---

## 9. Example Input

```json
{
  "base_briefing": {
    "briefing_id": "cdb-briefing-2122-enrich-v1",
    "task_id": "cdb-briefing-2122-enrich-v1",
    "scope_summary": "Enrich agent briefing with evidence, decisions, and memory",
    "task_id": "cdb-briefing-2122"
  },
  "task_scope": "Enrich agent briefing with evidence, decisions, and memory",
  "target_issue": "#2122",
  "target_paths": ["docs/surrealdb/", "tools/mcp/"],
  "target_concepts": ["briefing", "evidence", "decision", "context"],
  "requested_enrichment_depth": "standard",
  "allowed_context_surfaces": ["evidence", "decisions"]
}
```

---

## 10. Example Output

```json
{
  "enrichment_id": "cdb-enrich-2122-v1-abc123",
  "enriched_briefing_id": "cdb-briefing-2122-enrich-v1",
  "trust_summary": "3 evidence items (2 strong, 1 weak), 2 decisions (1 active, 1 superseded), no memory hints (opt-in required). Core assumptions supported by strong evidence. 1 weak evidence on secondary path.",
  "enriched_required_reads": [
    "docs/surrealdb/context-agent-briefing-schema-v1.md",
    "docs/surrealdb/context-tool-contracts-v1.md"
  ],
  "enriched_decisions": [
    {
      "decision_id": "D-2026-04-15-001",
      "decision_type": "governance",
      "decision": "Approve Agent Briefing Schema v1",
      "outcome": "approved",
      "status": "active",
      "rationale_summary": "Schema contract aligns with #2018 requirements",
      "source_ref": "issuecomment-4350000001",
      "timestamp": "2026-04-15T10:00:00Z"
    },
    {
      "decision_id": "D-2026-04-10-002",
      "decision_type": "technical",
      "decision": "Defer Memory Handoff to #2121",
      "outcome": "deferred",
      "status": "superseded",
      "rationale_summary": "Memory semantics not finalised",
      "source_ref": "issuecomment-4340000002",
      "timestamp": "2026-04-10T14:30:00Z",
      "superseded_by": "D-2026-04-20-001"
    }
  ],
  "enriched_evidence": [
    {
      "evidence_id": "EV-2026-05-01-001",
      "claim": "Briefing Schema v1 aligns with #2018 abstract model",
      "strength": "strong",
      "confidence": 0.95,
      "source_ref": "docs/surrealdb/context-agent-briefing-schema-v1.md",
      "source_type": "doc",
      "freshness": "fresh",
      "contradiction_flag": false,
      "stale_flag": false
    },
    {
      "evidence_id": "EV-2026-04-20-002",
      "claim": "Context Package v0 implementation complete",
      "strength": "medium",
      "confidence": 0.70,
      "source_ref": "docs/surrealdb/context-package-model-v1.md",
      "source_type": "doc",
      "freshness": "fresh",
      "contradiction_flag": false,
      "stale_flag": false
    },
    {
      "evidence_id": "EV-2026-03-15-003",
      "claim": "Legacy evidence resolution approach",
      "strength": "weak",
      "confidence": 0.40,
      "source_ref": "docs/archive/legacy-evidence.md",
      "source_type": "doc",
      "freshness": "stale",
      "contradiction_flag": false,
      "stale_flag": true
    }
  ],
  "enriched_memory": [],
  "enriched_stop_conditions": [
    "S1: scope ambiguous — clarify before proceeding",
    "S5: stale evidence on secondary path — validate before deep execution"
  ],
  "dependency_paths": [
    {"from": "briefing", "to": "evidence", "relationship": "supported_by"},
    {"from": "evidence", "to": "decision", "relationship": "governed_by"}
  ],
  "stale_evidence_notice": ["EV-2026-03-15-003"],
  "contradictory_evidence_notice": [],
  "missing_evidence_notice": []
}
```

---

## 11. Acceptance Criteria for #2122

| # | Criterion | Validation |
|---|-----------|------------|
| AC1 | Briefing shows evidence quality (strong/medium/weak) | `enriched_evidence` has `strength` and `confidence` fields |
| AC2 | Decisions marked as active/superseded | `enriched_decisions` has `status` field with proper enum |
| AC3 | Memory is read-only Hinweis | `enriched_memory` is read-only, no write operations |
| AC4 | Missing evidence visible | `missing_evidence_notice` populated when evidence gaps exist |
| AC5 | Stale evidence visible | `stale_evidence_notice` populated for evidence >30 days |
| AC6 | Contradictory evidence visible | `contradictory_evidence_notice` populated |
| AC7 | Trust summary synthesizes quality | `trust_summary` includes evidence/decision/memory synthesis |
| AC8 | No Write operations | Source code shows no memory/decision/evidence writes |
| AC9 | Deterministic IDs | Same input → same `enrichment_id` |
| AC10 | Source attribution | All refs carry `source_ref` |

---

## 12. Integration Points

| Point | Description | Status |
|-------|-------------|--------|
| Input: Base Briefing | Consumes output from #2105 (context_briefing_handler) | Implemented |
| Output: Enriched Briefing | Extends base briefing with enrichment fields | This model |
| Evidence Resolution | Interface to #2020 (context.evidence_resolve) | Future (opt-in) |
| Decision History | Interface to decision lookup | Future (opt-in) |
| Memory Retrieval | Interface to #2121 (memory handoff) | Future (opt-in) |

---

## 13. Guardrails

| # | Guardrail |
|---|----------|
| G1 | **Enrichment is read-only.** No memory, decision, or evidence writes. |
| G2 | **No Live/Echtgeld Go.** Enrichment does not authorize trading or capital. |
| G3 | **No Runtime write.** Enrichment runs in-process, no DB writes. |
| G4 | **Deterministic IDs.** Enrichment ID derived from input hash. |
| G5 | **Source attribution.** All refs must carry traceable `source_ref`. |
| G6 | **Stale blocks critical path.** Stale evidence on core assumptions triggers stop condition. |
| G7 | **Privacy preserved.** Memory hints with `privacy_constraint` not expanded. |
| G8 | **Uncertainty surfaced.** Missing context appears in `trust_summary`. |

---

## 14. LR-Status

**LR remains NO-GO.**

This enrichment model is documentation-only. It does not enable live trading, modify risk controls, change execution behaviour, or authorize live capital.

---

## 15. References

| Reference | Description |
|-----------|-------------|
| [#2122](https://github.com/jannekbuengener/Claire_de_Binare/issues/2122) | This issue |
| [#2105](https://github.com/jannekbuengener/Claire_de_Binare/issues/2105) | Agent Briefing Builder v1 (CLOSED) |
| [#2104](https://github.com/jannekbuengener/Claire_de_Binare/issues/2104) | Agent Briefing Schema v1 (CLOSED) |
| [#2018](https://github.com/jannekbuengener/Claire_de_Binare/issues/2018) | Agent Briefing Request/Result Model (CLOSED) |
| [#2020](https://github.com/jannekbuengener/Claire_de_Binare/issues/2020) | Evidence Resolution Tool Contract (OPEN) |
| [#2121](https://github.com/jannekbuengener/Claire_de_Binare/issues/2121) | Memory Handoff (OPEN) |
| [#2115](https://github.com/jannekbuengener/Claire_de_Binare/issues/2115) | Parent Epic |
| [#1976](https://github.com/jannekbuengener/Claire_de_Binare/issues/1976) | Context Intelligence Epic |
| `docs/surrealdb/context-agent-briefing-schema-v1.md` | Base briefing schema |
| `tools/mcp/context_bridge.py` | Briefing Builder implementation (lines ~1187-1210) |

---

## 16. Files Changed

- `docs/surrealdb/context-briefing-enrichment-model-v1.md` (new)