# Visual Control Room Information Model v0

**Issue:** #2029  
**Parent:** #2024 (Wave-6)  
**Epic:** #1976  
**Wave:** Wave-6 model definition (Wave-19 implements the builder)  
**Status:** model-defined  

---

## 1. Purpose

This document defines the information model for the CDB Visual Control Room.
It is a **data-model-only artefact** — no UI implementation is required.
Wave-19 (#2179–#2187) implements the View Builder on top of this model.

The control room shows signals and relationships. It does **not** grant
releases, authorise trades, or control runtime systems.

---

## 2. `visual_control_view` Object

The canonical information unit for a control room view.

```
visual_control_view {
    view_id          : string          -- stable, deterministic identifier (SHA256-based)
    view_type        : ViewType        -- one of VIEW_TYPES (see §3)
    view_label       : string          -- human-readable title
    target_scope     : string          -- scope qualifier, e.g. "all", "domain:risk", "issue:2029"
    data_sources     : [DataSourceRef] -- ordered list of SurrealDB tables / tools queried
    filters          : record          -- optional filter map (key → value)
    required_queries : [string]        -- SurrealQL or tool calls needed to populate this view
    display_entities : [string]        -- node types to render (e.g. "doc_chunk", "decision_event")
    display_edges    : [string]        -- edge/relation types to render (e.g. "supersedes", "contradicts")
    warnings         : [string]        -- view-level warnings (e.g. "stale source detected")
    generated_at     : datetime        -- timestamp of last generation
    generated_by     : string          -- tool or service that produced this view
    export_formats   : [ExportFormat]  -- supported output formats (see §5)
    guardrails       : [string]        -- embedded guardrails (always populated)
}
```

**All fields are read-only after generation.** No view object modifies repo, runtime, or trading state.

---

## 3. View Types (`VIEW_TYPES`)

| `view_type` | Description | Primary Source Tables |
|-------------|-------------|----------------------|
| `knowledge_graph_view` | Full context graph: artifacts, symbols, edges, concepts | `repo_artifact`, `code_symbol`, `dependency_edge`, `doc_chunk` |
| `architecture_map` | Service topology, dependency graph, ownership map | `code_symbol`, `dependency_edge`, `repo_artifact` |
| `decision_chain_view` | Ordered decision events, supersession chains, open decisions | `decision_event`, `claim`, `evidence_ref` |
| `evidence_map` | Evidence coverage per domain, claim–evidence binding | `evidence_ref`, `claim`, `audit_observation` |
| `risk_surface_report` | Scope drift events, blocking findings, quality weak spots | `scope_drift_event`, `contradiction`, `knowledge_quality_score` |
| `stale_knowledge_view` | Stale contexts, refresh recommendations, TTL violations | `stale_context`, `agent_memory`, `doc_chunk` |
| `scope_drift_events` | Logged scope drift findings, severity, required actions | `scope_drift_event` |
| `agent_memory_view` | Memory entries, trust levels, TTL status | `agent_memory` |
| `quality_score_dashboard` | Per-dimension quality scores, grade bands, warnings | `knowledge_quality_score` |

---

## 4. Minimum Data Per View

Each view type defines its minimum viable data set for v1:

### 4.1 `knowledge_graph_view`
- Minimum: at least one `repo_artifact` node with linked `doc_chunk` entries
- Edges: `dependency_edge` records between artifacts
- Required queries: `SELECT * FROM repo_artifact LIMIT 100`, `SELECT * FROM dependency_edge LIMIT 200`

### 4.2 `architecture_map`
- Minimum: `code_symbol` records of type `module` or `class`
- Edges: import/dependency `dependency_edge` records
- Required queries: `SELECT * FROM code_symbol WHERE symbol_type IN ["module","class"]`

### 4.3 `decision_chain_view`
- Minimum: at least one `decision_event` record
- Edges: `supersedes` and `references` relations on decision records
- Required queries: `SELECT * FROM decision_event ORDER BY created_at DESC LIMIT 50`

### 4.4 `evidence_map`
- Minimum: at least one `evidence_ref` with a linked `claim`
- Required queries: `SELECT * FROM evidence_ref`, `SELECT * FROM claim`

### 4.5 `risk_surface_report`
- Minimum: latest `scope_drift_event` and `contradiction` findings (blocking severity first)
- Required queries: scan outputs from `scope_drift_firewall.py` and `contradiction_scan.py`
- Enrichment: `knowledge_quality_score` for grade-band summary

### 4.6 `stale_knowledge_view`
- Minimum: `stale_context` findings with `severity >= warning`
- Required queries: scan output from `stale_knowledge_scan.py`
- Enrichment: `recommended_refresh` from `stale_refresh_plan.py`

### 4.7 `scope_drift_events`
- Minimum: all `scope_drift_event` records from current session context
- Required queries: `SELECT * FROM scope_drift_event ORDER BY created_at DESC`

### 4.8 `agent_memory_view`
- Minimum: all `agent_memory` records with `trust_level` and TTL fields
- Required queries: `SELECT * FROM agent_memory ORDER BY created_at DESC`

### 4.9 `quality_score_dashboard`
- Minimum: latest `knowledge_quality_score` per target scope
- Required queries: `SELECT * FROM knowledge_quality_score ORDER BY computed_at DESC LIMIT 20`
- Display: dimension scores as bar chart rows, overall grade badge

---

## 5. Export Formats (`ExportFormat`)

| `export_format` | Description |
|-----------------|-------------|
| `json` | Machine-readable JSON export (canonical) |
| `markdown` | Human-readable Markdown table/list report |
| `html` | Static HTML with embedded CSS (no JS runtime) |
| `mermaid` | Mermaid graph diagram (graph/flowchart) for graph-type views |

No UI framework is required. v1 targets `json` and `markdown` as mandatory formats.

---

## 6. Relationship to Surrealist

- **Surrealist** (official SurrealDB GUI) serves as the early DB/graph viewer
  for raw table inspection and ad-hoc SurrealQL queries.
- The **CDB Visual Control Room** builds domain-specific, context-intelligence-aware
  views on top of the same SurrealDB backend.
- These are complementary, not competing surfaces.
- No dependency on Surrealist at runtime; Surrealist is an operator tool.

---

## 7. `DataSourceRef` Sub-Object

```
DataSourceRef {
    source_type    : "surrealdb_table" | "tool_output" | "file"
    source_ref     : string   -- table name, tool name, or file path
    query_hint     : string   -- optional SurrealQL or CLI hint
    write_allowed  : bool     -- always false for control room sources
}
```

All `DataSourceRef` entries have `write_allowed = false`.

---

## 8. Guardrails (always embedded in every view)

Every `visual_control_view` object includes the following `guardrails` list:

```
[
  "Control Room shows signals and relationships, not release authorisations.",
  "No view object modifies SurrealDB, the repo, runtime, or trading state.",
  "No view grants Live-Readiness-Go or Echtgeld-Go.",
  "No Trading-Konsole. No Runtime-Steuerung.",
  "Scores and signals are explanatory context hints, not truth.",
  "Human-GO is required before any write or live action.",
]
```

---

## 9. Validation Examples

The following examples demonstrate how each view resolves to data:

| Example Scenario | View Type | Expected Output |
|-----------------|-----------|-----------------|
| Decision A superseded by Decision B | `decision_chain_view` | Chain showing A → superseded_by → B |
| Impact of changing `risk_service.py` | `architecture_map` | Affected downstream symbols highlighted |
| Stale `CURRENT_STATUS.md` | `stale_knowledge_view` | Entry with `stale_type: stale_doc_chunk`, `severity: warning` |
| Scope drift to live trading surface | `scope_drift_events` | Entry with `drift_type: trading_surface_touched`, `severity: blocking` |

---

## 10. Acceptance Criteria (from #2029)

| Criterion | Met by this doc |
|-----------|-----------------|
| Visualisation is prepared on the data-model side | ✓ — `visual_control_view` object fully defined |
| No UI implementation required | ✓ — export formats, no UI framework |
| Each view has clear data sources | ✓ — `data_sources: [DataSourceRef]`, §4 Minimum Data |
| Control Room shows signals, not releases | ✓ — §8 Guardrails embedded in every object |

---

## 11. Related Artefacts

| Artefact | Purpose |
|----------|---------|
| `infrastructure/surrealdb/context_intelligence_v0.surql` | Schema — `DEFINE TABLE visual_control_view` |
| `docs/surrealdb/context-intelligence-roadmap.md` | Maps this model to Wave-19 |
| `docs/surrealdb/context-intelligence-system.md` | Overall CIS architecture |
| Issue #2180 | Implement Control Room View Builder v1 (Wave-19, depends on this model) |
| Issue #2181–#2184 | Per-view report generators (Wave-19) |
| Issue #2185–#2187 | Tests, runbook, completion gates (Wave-19) |
