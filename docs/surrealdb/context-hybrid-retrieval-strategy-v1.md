# Hybrid Retrieval Strategy v1

**Issue**: #2015
**Status**: Contract Defined
**Date**: 2026-05-03
**Agent**: Gemini (Audit & Review)

## Overview

This document defines the Hybrid Retrieval Strategy v1 for the SurrealDB Context Intelligence System. It provides a multi-modal retrieval approach that combines keyword, structured, graph-based, evidence-based, decision history, and memory lookup capabilities.

## Purpose

The hybrid retrieval strategy enables agents to query the Context Intelligence knowledge base through multiple retrieval modes, combining results with weighted ranking to provide contextually relevant results.

## Non-Goals

- Retrieval results are context, not truth
- No retrieval result implies Live-Go
- No DB write
- No Memory write
- No trading/risk/execution/strategy change
- Vector search is optional (not required for baseline)

---

## Retrieval Modes

The strategy supports 8 retrieval modes, which can be combined in `hybrid_ranked` mode:

| Mode | Description | Dependencies |
|------|-------------|---------------|
| `full_text` | Full-text keyword search across indexed content | None |
| `structured_filter` | Query with structured filters (date, type, source) | None |
| `graph_traversal` | Navigate entity relationships via graph edges | Graph schema |
| `evidence_lookup` | Find evidence by reference or claim | Evidence model (#2005) |
| `decision_history` | Query historical decision records | Decision schema |
| `memory_lookup` | Retrieve agent memory state | Memory schema |
| `optional_vector_search` | Semantic similarity search (optional) | Vector index (optional) |
| `hybrid_ranked` | Combine multiple modes with weighted ranking | Depends on modes used |

---

## Query Types

The strategy defines 7 query types, each mapping to one or more retrieval modes:

### 1. keyword query

Search full-text using keywords or phrases.

```json
{
  "type": "keyword",
  "query": "policy_hash",
  "modes": ["full_text"]
}
```

### 2. artifact query

Retrieve specific artifact types by ID or attributes.

```json
{
  "type": "artifact",
  "artifact_type": "decision|evidence|memory|briefing",
  "filters": { "date_from": "2026-01-01" },
  "modes": ["structured_filter"]
}
```

### 3. symbol query

Find code symbols (functions, classes, variables) with context.

```json
{
  "type": "symbol",
  "symbol_name": "RiskManager",
  "include_dependents": true,
  "modes": ["graph_traversal", "full_text"]
}
```

### 4. concept query

Search by semantic concept rather than keywords.

```json
{
  "type": "concept",
  "concept": "Live-Readiness",
  "modes": ["optional_vector_search", "full_text"]
}
```

### 5. decision query

Query decision history with filtering.

```json
{
  "type": "decision",
  "filters": { "outcome": "rejected", "agent": "codex" },
  "modes": ["decision_history"]
}
```

### 6. evidence query

Find evidence by claims or references.

```json
{
  "type": "evidence",
  "claim": "trade-capable stage approved",
  "modes": ["evidence_lookup"]
}
```

### 7. scope query

Query by scope or containment relationships.

```json
{
  "type": "scope",
  "scope_path": "/services/risk",
  "include_children": true,
  "modes": ["graph_traversal", "structured_filter"]
}
```

---

## Ranking Factors

When combining results from multiple modes, the following ranking factors are applied:

| Factor | Weight | Description |
|--------|--------|--------------|
| `source_match` | 0.20 | Direct match to query source/type |
| `graph_distance` | 0.15 | Proximity in entity graph (closer = higher) |
| `evidence_strength` | 0.15 | Quality of supporting evidence |
| `freshness` | 0.15 | Recency of the result (decay over time) |
| `confidence` | 0.20 | Confidence score of the result |
| `scope_match` | 0.10 | Match to query scope/path |
| `memory_trust` | 0.05 | Trust score of memory source |

### Freshness Decay

```
score = base_score * (1.0 - 0.05 * days_since_creation)
```

- Freshness is calculated from `created_at` timestamp
- Maximum decay: 50% after 10 days
- Adjustable via config

---

## Result Object

All retrieval results follow this schema:

```json
{
  "result_id": "string (deterministic)",
  "result_type": "decision|evidence|memory|briefing|artifact|symbol|scope",
  "source_ref": "string (internal reference)",
  "title": "string",
  "summary": "string (truncated to 200 chars)",
  "score": "float (0.0-1.0, weighted aggregate)",
  "confidence": "float (0.0-1.0)",
  "freshness": "float (0.0-1.0, time-decayed)",
  "graph_path": ["string"] | null,
  "evidence_refs": ["string"] | null,
  "warnings": ["string"],
  "retrieval_mode": "full_text|structured_filter|graph_traversal|evidence_lookup|decision_history|memory_lookup|optional_vector_search",
  "matched_on": ["keyword"|"concept"|"symbol"|"scope"|"evidence"|"decision"|"memory"]
}
```

### Result Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `result_id` | string | Deterministic ID based on content hash |
| `result_type` | enum | Type of retrieved item |
| `source_ref` | string | Internal reference for provenance |
| `title` | string | Human-readable title |
| `summary` | string | Truncated content summary |
| `score` | float | Weighted aggregate score (0.0-1.0) |
| `confidence` | float | Confidence of retrieval (0.0-1.0) |
| `freshness` | float | Time-decayed relevance (0.0-1.0) |
| `graph_path` | array | Graph traversal path if applicable |
| `evidence_refs` | array | Supporting evidence IDs |
| `warnings` | array | Warnings about result quality |
| `retrieval_mode` | enum | Primary mode used |
| `matched_on` | array | Query types that matched |

---

## Confidence Rules

1. **Explicit evidence**: If result has direct evidence references, confidence >= 0.7
2. **Inferred result**: If result is inferred (no direct evidence), confidence <= 0.6
3. **Graph traversal**: Graph-only results have confidence <= 0.5 unless evidence-linked
4. **Memory lookup**: Memory results have confidence based on memory_trust score
5. **Weak match**: Any result with confidence < 0.3 must include warning

### Confidence Thresholds

| Range | Classification | Action |
|-------|---------------|--------|
| 0.8-1.0 | High confidence | Use directly |
| 0.5-0.79 | Medium confidence | Use with verification |
| 0.3-0.49 | Low confidence | Flag for review |
| < 0.3 | Weak match | Exclude or warn heavily |

---

## Freshness Rules

1. Default freshness calculated from `created_at` timestamp
2. Items without timestamp default to freshness = 0.5
3. Configurable decay rate (default: 5% per day)
4. Maximum freshness: 1.0 (items < 1 day old)
5. Minimum freshness: 0.1 (items > 18 days old)

---

## Optional Vector Search

Vector search is **optional** and not required for baseline retrieval:

- **Default**: disabled
- **Enabling**: requires `VECTOR_SEARCH_ENABLED=true`
- **Dependency**: requires vector index on supported fields
- **Impact**: adds `concept` query capability
- **Fallback**: if vector search fails or disabled, falls back to `full_text`

### Vector Search Constraints

- No new hard dependencies
- Graceful degradation if vector index unavailable
- Optional in `hybrid_ranked` mode

---

## Example Queries

### Example 1: "policy_hash"

```json
{
  "type": "keyword",
  "query": "policy_hash",
  "modes": ["full_text", "graph_traversal"],
  "limit": 10
}
```

Expected result: decisions/documents mentioning policy hash.

### Example 2: "Live-Readiness"

```json
{
  "type": "concept",
  "concept": "Live-Readiness",
  "modes": ["optional_vector_search", "full_text", "evidence_lookup"],
  "limit": 15
}
```

Expected result: evidence and decisions related to Live-Readiness evaluation.

### Example 3: "welche Tests validieren Symbol X"

```json
{
  "type": "symbol",
  "symbol_name": "RiskManager",
  "include_dependents": true,
  "filters": { "artifact_type": "test" },
  "modes": ["graph_traversal", "full_text"],
  "limit": 20
}
```

Expected result: test artifacts related to Symbol X.

### Example 4: "warum ist Scope Y blockiert"

```json
{
  "type": "scope",
  "scope_path": "/services/scopeY",
  "include_children": false,
  "modes": ["graph_traversal", "decision_history", "evidence_lookup"],
  "limit": 10
}
```

Expected result: decisions and evidence explaining why Scope Y is blocked.

---

## Read-Only Guardrails

All retrieval operations are **read-only**:

1. **No retrieval result is automatically truth** — agents must validate
2. **No retrieval result implies Live-Go** — Live-Go requires separate authorization
3. **No DB write** — retrieval only reads from SurrealDB
4. **No Memory write** — retrieval only reads memory, doesn't modify
5. **No trading/risk/execution/strategy change** — retrieval has no side effects

---

## LR Status

**LR remains NO-GO**.

This contract defines retrieval strategy only. It does not:
- Enable live trading
- Modify risk controls
- Change execution behavior
- Alter LR status

---

## Handoff Criteria

### Unblocks #2016 (Context Package Model)

The retrieval strategy provides:
- Structured result objects for packaging
- Confidence and freshness data for package metadata
- Multi-modal results that can be combined in context packages
- Query types that map to package request types

### How #2015, #2016, #2017 Remain Separate

| Issue | Focus | Output |
|-------|-------|--------|
| #2015 | Retrieval strategy + query types | `context-hybrid-retrieval-strategy-v1.md` |
| #2016 | Package model + structure | Separate contract |
| #2017 | Tool contracts | Separate contract |

Each issue has distinct scope and output. #2015 defines the underlying retrieval mechanism; #2016 uses that to create package structures; #2017 exposes tools based on both.

---

## Validation

This contract was validated against:
- Issue #2015 requirements (query types, ranking, result object, examples)
- Owner comment: missing artifact now provided
- Existing contract patterns in `docs/surrealdb/context-*-contract.md`

---

## Files Changed

- `docs/surrealdb/context-hybrid-retrieval-strategy-v1.md` (new)

---

## References

- Epic: #1976 (CDB Context Intelligence System)
- Parent: #2014
- Related: #1992 (Query CLI contract), #2002 (Graph query examples), #2005 (Evidence model), #2006 (Claims model)
- Follow-up: #2016 (Context package model), #2017 (Tool contracts)