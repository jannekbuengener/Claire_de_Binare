# Context Package Model v1

**Issue**: #2016
**Status**: Contract Defined
**Date**: 2026-05-03
**Agent**: Gemini (Audit & Review)

## Overview

This document defines the Context Package Model v1 for the SurrealDB Context Intelligence System. A Context Package is a standardized work product that packages retrieval results for agent consumption, ensuring usable, bounded, and attributable context delivery.

## Purpose

The Context Package model provides:
- Structured output from the hybrid retrieval strategy (#2015)
- Bounded context delivery (not a data dump)
- Source attribution for all included content
- Confidence and freshness metadata
- Explicit uncertainty and stop-condition signaling

## Non-Goals

- No Context Package without SourceRefs
- No unchecked Memory as hard truth
- No clearance/Live-Go derivation
- No DB writes
- No Memory writes
- No trading/risk/execution/strategy effects

---

## Package Lifecycle

The Context Package follows this lifecycle:

```
┌─────────────────────────────────────────────────────────────────┐
│  1. REQUEST          →  2. RETRIEVAL      →  3. ASSEMBLY       │
│  - query params      →  - hybrid search   →  - result binding   │
│  - scope definition →  - mode selection   │  - evidence attach  │
│  - format prefs     │  - ranking          │  - confidence calc │
└─────────────────────────────────────────────────────────────────┘
            │                         │
            ▼                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. OUTPUT           →  5. VALIDATION                          │
│  - agent format      →  - schema check                         │
│  - human format      →  - completeness                          │
│                     →  - guardrail verify                      │
└─────────────────────────────────────────────────────────────────┘
```

### Stage Details

| Stage | Description | Agent Involvement |
|-------|-------------|-------------------|
| 1. REQUEST | Agent requests context with query, scope, format | Client |
| 2. RETRIEVAL | System executes hybrid retrieval (#2015) | System |
| 3. ASSEMBLY | Results packaged with metadata | System |
| 4. OUTPUT | Formatted for agent or human | System |
| 5. VALIDATION | Verify completeness and guardrails | System |

---

## Package Object Schema

```json
{
  "package_id": "string (deterministic)",
  "version": "v1",
  "request": {
    "query": "string",
    "query_type": "keyword|artifact|symbol|concept|decision|evidence|scope",
    "scope": "string",
    "requested_modes": ["string"],
    "format_preference": "agent|human|both"
  },
  "generated_at": "ISO8601",
  "source_refs": ["string"],
  "bounds": {
    "max_artifacts": 50,
    "max_symbols": 100,
    "max_doc_chunks": 20,
    "max_evidence_refs": 30,
    "max_decisions": 20,
    "max_memory_refs": 10
  },
  "contents": {
    "artifacts": [
      {
        "id": "string",
        "type": "decision|evidence|memory|briefing|doc",
        "title": "string",
        "summary": "string",
        "source_ref": "string",
        "confidence": "float",
        "freshness": "float"
      }
    ],
    "document_chunks": [
      {
        "doc_id": "string",
        "chunk_index": "integer",
        "content": "string",
        "source_ref": "string"
      }
    ],
    "symbols": [
      {
        "symbol_name": "string",
        "symbol_type": "function|class|variable|module",
        "file_path": "string",
        "definition": "string",
        "dependents": ["string"]
      }
    ],
    "graph_paths": [
      {
        "path_id": "string",
        "nodes": ["string"],
        "relationships": ["string"]
      }
    ],
    "evidence_refs": [
      {
        "evidence_id": "string",
        "claim": "string",
        "strength": "low|medium|high",
        "source_ref": "string"
      }
    ],
    "decisions": [
      {
        "decision_id": "string",
        "agent": "string",
        "decision": "string",
        "outcome": "approved|rejected|escalated",
        "timestamp": "ISO8601"
      }
    ],
    "memory_refs": [
      {
        "memory_id": "string",
        "session_id": "string",
        "content": "string",
        "memory_type": "working|shortterm|longterm",
        "trust_score": "float"
      }
    ]
  },
  "dependency_paths": [
    {
      "from": "string",
      "to": "string",
      "relationship": "string"
    }
  ],
  "confidence_summary": {
    "overall": "float (0.0-1.0)",
    "by_type": {
      "artifacts": "float",
      "evidence": "float",
      "decisions": "float",
      "memory": "float"
    },
    "low_confidence_items": ["string"]
  },
  "freshness_summary": {
    "overall": "float (0.0-1.0)",
    "oldest_item": "ISO8601",
    "newest_item": "ISO8601"
  },
  "warnings": [
    {
      "code": "string",
      "message": "string",
      "affected_items": ["string"]
    }
  ],
  "omissions": [
    {
      "reason": "string",
      "omitted_type": "string",
      "count": "integer"
    }
  ],
  "required_next_reads": [
    {
      "item_id": "string",
      "rationale": "string"
    }
  ],
  "stop_conditions": [
    {
      "condition": "string",
      "action": "string"
    }
  ]
}
```

---

## Required Fields

All Context Packages **must** include:

| Field | Required | Reason |
|-------|----------|--------|
| `package_id` | Yes | Unique identification |
| `version` | Yes | Contract versioning |
| `request.query` | Yes | Traceability |
| `generated_at` | Yes | Temporal context |
| `source_refs` | Yes | Attribution |
| `contents` | Yes | Core payload |
| `confidence_summary.overall` | Yes | Quality signal |
| `warnings` | Yes (array) | Even if empty |

---

## Max Sizes (Bounds)

| Content Type | Max | Rationale |
|--------------|-----|-----------|
| Artifacts | 50 | Prevent overload |
| Symbols | 100 | Cover essential refs |
| Document Chunks | 20 | Representative sample |
| Evidence Refs | 30 | Core evidence only |
| Decisions | 20 | Recent history |
| Memory Refs | 10 | Working memory only |

If bounds are exceeded:
- Priority by confidence (highest first)
- Add omission record
- Include warning

---

## Prioritization Within Package

When results exceed bounds:

1. **Confidence** (primary) - highest confidence first
2. **Freshness** (secondary) - more recent items preferred
3. **Evidence strength** (tertiary) - strong evidence prioritized
4. **Scope match** (quaternary) - direct matches preferred

Priority order by content type:
1. Evidence (strongest binding)
2. Decisions (audit trail)
3. Artifacts (direct matches)
4. Document chunks (context)
5. Symbols (code reference)
6. Memory refs (lowest priority)

---

## Format Options

### Agent-Readable Format

JSON with all fields, designed for programmatic consumption.

```json
{
  "package_id": "...",
  "contents": { ... },
  "confidence_summary": { ... }
}
```

### Human-Readable Format

Markdown with structured sections:

```markdown
# Context Package

**Generated**: 2026-05-03T12:00:00Z
**ID**: pkg_abc123

## Summary
- Confidence: 0.75
- Freshness: 0.82

## Contents

### Decisions (5)
- [D001] Risk limit approved by codex
- [D002] ...

### Evidence (12)
- [E001] Trade validation complete
- [E02] ...
```

### Format Selection

- Default: `agent` format
- Override via `request.format_preference`

---

## Uncertainty Rules

### Confidence Thresholds

| Range | Classification | Agent Action |
|-------|---------------|--------------|
| 0.8-1.0 | High | Use directly |
| 0.5-0.79 | Medium | Verify before use |
| 0.3-0.49 | Low | Flag in warnings |
| < 0.3 | Very Low | Exclude or heavy warning |

### Uncertainty Signals

1. **Low confidence items** - Must be listed in `confidence_summary.low_confidence_items`
2. **Memory references** - Must include `trust_score`, default to low confidence
3. **Inferred results** - Must include warning with "inferred" code
4. **Missing evidence** - Must include omission record

---

## Missing Evidence Rules

When evidence is incomplete or unavailable:

| Scenario | Required Action |
|----------|----------------|
| No evidence found | Add omission with `reason: no_evidence_found` |
| Evidence partial | Add warning with `code: partial_evidence` |
| Evidence inferred | Add warning with `code: inferred_evidence`, set confidence <= 0.6 |
| Memory unchecked | Add warning with `code: unverified_memory`, default confidence <= 0.4 |

---

## Failure Modes / Fail-Closed Behavior

| Mode | Condition | Behavior |
|------|-----------|----------|
| `query_empty` | No results | Return empty package with warning |
| `query_timeout` | Timeout | Return partial package with `timeout` warning |
| `bounds_exceeded` | Too many results | Apply prioritization, add omission |
| `invalid_request` | Malformed query | Return error package, no contents |
| `source_unavailable` | Source down | Skip source, add warning |

### Error Package Schema

```json
{
  "package_id": "error_<hash>",
  "status": "error",
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```

---

## Source Attribution Requirements

Every content item must be attributable through the fields modeled for its content type. The specific attribution fields vary by content type:

| Content Type | source_ref | confidence | freshness | Other |
|--------------|:----------:|:----------:|:---------:|-------|
| `artifacts` | Required | Required | Required | - |
| `document_chunks` | Required | - | - | - |
| `symbols` | - | - | - | `file_path` |
| `graph_paths` | - | - | - | `path_id`, `nodes` |
| `evidence_refs` | Required | - | - | `strength` |
| `decisions` | - | - | - | `timestamp`, `agent` |
| `memory_refs` | - | - | - | `trust_score` (Required) |

Aggregate confidence and freshness are represented by `confidence_summary` and `freshness_summary` at package level. If a content type does not model item-level confidence/freshness, validators must not require those fields at item level.

**Important**: `dependency_paths` is a top-level package field and **MUST NOT** be nested under `contents`.

---

## Evidence Binding Rules

1. **Strong binding**: Evidence directly supports artifact → confidence >= 0.7
2. **Weak binding**: Evidence inferred → confidence <= 0.6
3. **No binding**: No evidence → confidence <= 0.4, warning required

Evidence must reference:
- Source document
- Claim being supported
- Strength level

---

## Relationship to #2015 (Hybrid Retrieval)

The Context Package builds on the Hybrid Retrieval Strategy:

| Retrieval Output | Package Input |
|-----------------|---------------|
| Result objects | `contents.artifacts`, `contents.document_chunks` |
| Ranking factors | `confidence_summary` calculation |
| Graph paths | Top-level `dependency_paths` |
| Evidence refs | `contents.evidence_refs` |
| Decision history | `contents.decisions` |
| Memory lookup | `contents.memory_refs` |

The package assembles retrieval results into a bounded, attributed delivery format.

---

## Handoff Criteria

### Unblocks #2017 (Tool Contracts)

The package model provides:
- Structured input for `context.package` tool
- Clear schema for tool output
- Confidence/freshness for tool reliability signals

### How #2016, #2017, #2092 Remain Separate

| Issue | Focus | Output |
|-------|-------|--------|
| #2016 | Package model/structure | `context-package-model-v1.md` |
| #2017 | Tool contracts | `context-tool-contracts-v1.md` |
| #2092 | Land tool contracts v0 | Implementation |

The package model (#2016) defines what a package IS.
The tool contracts (#2017) define tools that USE packages.
#2092 lands the actual tool implementations.

---

## Example Packages

### Example 1: Doku-Slice

```json
{
  "package_id": "pkg_doku_slice_001",
  "request": {
    "query": "Live-Readiness evaluation process",
    "query_type": "concept",
    "scope": "docs",
    "format_preference": "agent"
  },
  "contents": {
    "artifacts": [
      {
        "id": "A001",
        "type": "doc",
        "title": "LR-AUDIT-STATUS-2026-03-05.md",
        "confidence": 0.92,
        "source_ref": "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md"
      }
    ],
    "document_chunks": [
      { "doc_id": "D001", "chunk_index": 0, "source_ref": "..." }
    ]
  },
  "confidence_summary": { "overall": 0.85 },
  "warnings": []
}
```

### Example 2: Code-Symbol-Slice

```json
{
  "package_id": "pkg_symbol_slice_001",
  "request": {
    "query": "RiskManager symbol",
    "query_type": "symbol",
    "scope": "code",
    "format_preference": "agent"
  },
  "contents": {
    "symbols": [
      {
        "symbol_name": "RiskManager",
        "symbol_type": "class",
        "file_path": "services/risk/manager.py",
        "dependents": ["OrderValidator", "ExposureCalculator"]
      }
    ],
    "graph_paths": [
      {
        "path_id": "GP001",
        "nodes": ["RiskManager", "OrderValidator", "ExecutionService"]
      }
    ]
  }
}
```

### Example 3: Decision-Replay-Slice

```json
{
  "package_id": "pkg_decision_slice_001",
  "request": {
    "query": "trade-capable decision",
    "query_type": "decision",
    "format_preference": "both"
  },
  "contents": {
    "decisions": [
      {
        "decision_id": "D001",
        "agent": "codex",
        "decision": "stage:trade-capable approved",
        "outcome": "approved",
        "timestamp": "2026-04-08T10:00:00Z"
      }
    ],
    "evidence_refs": [
      {
        "evidence_id": "E001",
        "claim": "All mandatory criteria met",
        "strength": "high",
        "source_ref": "docs/runbooks/CONTROL_REGISTER.md"
      }
    ]
  }
}
```

### Example 4: Impact-Slice

```json
{
  "package_id": "pkg_impact_slice_001",
  "request": {
    "query": "impact of signal change",
    "query_type": "scope",
    "format_preference": "agent"
  },
  "contents": {
    "artifacts": [...],
    "evidence_refs": [...]
  },
  "dependency_paths": [
    { "from": "signal", "to": "risk", "relationship": "affects" }
  ],
  "confidence_summary": { "overall": 0.78 }
}
```

---

## Read-Only Guardrails

All Context Package operations are **read-only**:

1. Package is assembled from retrieval results only
2. No DB write
3. No Memory write
4. No trading/risk/execution/strategy changes
5. No Live-Go derivation

---

## LR Status

**LR remains NO-GO**.

This contract defines package model only. It does not:
- Enable live trading
- Modify risk controls
- Change execution behavior
- Alter LR status

---

## Validation

This contract was validated against:
- Issue #2016 requirements (all fields, bounds, prioritization, formats, examples)
- Owner comment: "weiterhin offen", missing contract artifact now provided
- Alignment with #2015 retrieval strategy
- Guardrails from issue requirements

---

## Files Changed

- `docs/surrealdb/context-package-model-v1.md` (new)

---

## References

- Epic: #1976 (CDB Context Intelligence System)
- Parent: #2014
- Related: #2015 (Hybrid Retrieval Strategy)
- Follow-up: #2017 (Tool contracts), #2092 (Tool implementation)