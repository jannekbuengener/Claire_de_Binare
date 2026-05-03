# Context Tool Contracts v1

**Issue**: #2017
**Status**: Contract Defined
**Date**: 2026-05-03
**Agent**: Gemini (Audit & Review)

## Overview

This document defines the v1 contracts for the Context Tools — a set of read-only MCP-compatible tools that provide agents access to the SurrealDB Context Intelligence System without direct table access or write permissions.

## Scope

These contracts define **v1** of the Context Tools, targeting:
- Wave-12 MCP bridge implementation
- Read-only agent access layer
- Evidence and attribution requirements

## Non-Goals

- No tool writes to Repo files
- No tool provides Live-Go
- No tool triggers Runtime actions
- No tool uses Memory as sole truth source

## Tool Contracts v1

### 1. context.search

**Purpose**: Search the Context Intelligence knowledge base using hybrid retrieval (keyword + semantic).

**Input Schema**:
```json
{
  "query": "string (required)",
  "limit": "integer (optional, default: 10)",
  "filters": {
    "source_types": ["decision", "evidence", "memory", "briefing"],
    "date_from": "ISO8601",
    "date_to": "ISO8601"
  }
}
```

**Output Schema**:
```json
{
  "tool": "context.search",
  "status": "ok",
  "results": [
    {
      "id": "string",
      "type": "decision|evidence|memory|briefing",
      "title": "string",
      "summary": "string",
      "source_ref": "string (internal ref)",
      "confidence": "float (0.0-1.0)",
      "warnings": ["string"]
    }
  ],
  "metadata": {
    "query_time_ms": "integer",
    "total_hits": "integer"
  }
}
```

**Failure Modes**:
- `empty_results`: Query valid but no matches
- `invalid_query`: Query malformed or empty
- `timeout`:检索超时

**Guardrails**:
- Read-only (no write to any system)
- Returns SourceRefs for all results
- Includes confidence scores
- Warnings array for edge cases

---

### 2. context.package

**Purpose**: Package context artifacts for handoff between agents or sessions.

**Input Schema**:
```json
{
  "artifacts": ["string (ids)"],
  "format": "json|markdown",
  "include_metadata": "boolean (default: true)"
}
```

**Output Schema**:
```json
{
  "tool": "context.package",
  "status": "ok",
  "package": {
    "format": "json|markdown",
    "items": [...],
    "created_at": "ISO8601",
    "package_id": "string (deterministic)"
  }
}
```

**Failure Modes**:
- `invalid_artifacts`: One or more artifact IDs not found
- `format_unsupported`: Requested format not supported

**Guardrails**:
- Read-only export only
- Package ID is deterministic (reproducible)

---

### 3. context.trace

**Purpose**: Trace decision or event lineage through the Context Intelligence system.

**Input Schema**:
```json
{
  "target_id": "string (required)",
  "depth": "integer (optional, default: 5, max: 20)"
}
```

**Output Schema**:
```json
{
  "tool": "context.trace",
  "status": "ok",
  "trace": {
    "root": { "id": "string", "type": "string", "title": "string" },
    "lineage": [
      {
        "id": "string",
        "type": "string",
        "relationship": "caused_by|related_to|derived_from",
        "depth": "integer"
      }
    ]
  }
}
```

**Failure Modes**:
- `target_not_found`: ID does not exist
- `depth_exceeded`: Requested depth exceeds limit

**Guardrails**:
- Read-only traversal
- Maximum depth cap prevents abuse

---

### 4. context.evidence.resolve

**Purpose**: Resolve evidence references to their full context and provenance.

**Input Schema**:
```json
{
  "evidence_ids": ["string (required)"],
  "include_provenance": "boolean (default: true)"
}
```

**Output Schema**:
```json
{
  "tool": "context.evidence.resolve",
  "status": "ok",
  "evidence": [
    {
      "id": "string",
      "content": "string",
      "source": "string",
      "provenance": {
        "created_by": "string",
        "created_at": "ISO8601",
        "chain": ["string"]
      },
      "confidence": "float"
    }
  ]
}
```

**Failure Modes**:
- `evidence_not_found`: One or more IDs invalid

**Guardrails**:
- Read-only resolution
- Provenance chain required for auditability

---

### 5. context.decision.history

**Purpose**: Retrieve historical decision records with filtering and pagination.

**Input Schema**:
```json
{
  "filters": {
    "agent": "string",
    "date_from": "ISO8601",
    "date_to": "ISO8601",
    "outcome": "approved|rejected|escalated"
  },
  "limit": "integer (default: 20, max: 100)",
  "offset": "integer (default: 0)"
}
```

**Output Schema**:
```json
{
  "tool": "context.decision.history",
  "status": "ok",
  "decisions": [
    {
      "id": "string",
      "agent": "string",
      "decision": "string",
      "outcome": "approved|rejected|escalated",
      "timestamp": "ISO8601",
      "context": "string"
    }
  ],
  "pagination": {
    "total": "integer",
    "limit": "integer",
    "offset": "integer"
  }
}
```

**Failure Modes**:
- `invalid_filters`: Malformed filter criteria

**Guardrails**:
- Read-only historical access
- Pagination prevents large result sets

---

### 6. context.memory.get

**Purpose**: Retrieve agent memory state for current or recent sessions.

**Input Schema**:
```json
{
  "session_id": "string (optional, default: current)",
  "memory_type": "working|shortterm|longterm"
}
```

**Output Schema**:
```json
{
  "tool": "context.memory.get",
  "status": "ok",
  "memory": {
    "session_id": "string",
    "type": "working|shortterm|longterm",
    "entries": [
      {
        "key": "string",
        "value": "string",
        "updated_at": "ISO8601"
      }
    ]
  }
}
```

**Failure Modes**:
- `session_not_found`: Requested session does not exist

**Guardrails**:
- Read-only access to memory state
- No memory modification via this tool

---

### 7. context.impact

**Purpose**: Assess potential impact of a decision or action on other system components.

**Input Schema**:
```json
{
  "target": {
    "type": "decision|signal|order|evidence",
    "id": "string"
  },
  "scope": "internal|external|all"
}
```

**Output Schema**:
```json
{
  "tool": "context.impact",
  "status": "ok",
  "impact": {
    "affected_components": ["string"],
    "risk_level": "low|medium|high",
    "cascade_risk": "boolean",
    "recommendations": ["string"]
  }
}
```

**Failure Modes**:
- `target_not_found`: Target does not exist

**Guardrails**:
- Read-only impact assessment
- Risk level requires human review for high

---

### 8. context.briefing

**Purpose**: Generate a structured briefing for agent handoff or session start.

**Input Schema**:
```json
{
  "focus_areas": ["string (optional)"],
  "depth": "summary|detailed",
  "include_recent_decisions": "boolean (default: true)"
}
```

**Output Schema**:
```json
{
  "tool": "context.briefing",
  "status": "ok",
  "briefing": {
    "generated_at": "ISO8601",
    "focus_areas": ["string"],
    "sections": {
      "system_status": "string",
      "recent_decisions": [...],
      "pending_items": ["string"],
      "context_summary": "string"
    }
  }
}
```

**Failure Modes**:
- `insufficient_data`: Not enough data for briefing

**Guardrails**:
- Read-only briefing generation
- No system state modification

---

## Common Contract Elements

All v1 tools include:

| Element | Required | Description |
|---------|----------|-------------|
| `tool` | Yes | Tool identifier |
| `status` | Yes | "ok" or "error" |
| `error` | If error | Error type and message |
| `source_ref` | Where applicable | Internal reference for audit |

### Error Response Schema

```json
{
  "tool": "<tool-name>",
  "status": "error",
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```

### Confidence & Warnings

All tools that return results include:
- `confidence`: Float 0.0-1.0
- `warnings`: Array of strings (may be empty)

This enables agents to make informed decisions about result quality.

---

## Read-Only Posture

All v1 tools are **read-only by default**:

- No tool writes to the knowledge base
- No tool modifies memory state
- No tool triggers runtime actions
- No tool provides Live-Go authorization
- No tool makes trading/risk/execution decisions

Future versions may introduce write-capable tools, but v1 is strictly read-only.

---

## MCP Compatibility

All tool contracts are designed for MCP (Model Context Protocol) exposure:

- JSON input/output
- Explicit schemas
- Clear error codes
- Idempotent operations

---

## Handoff Criteria to #2092

The contract in this document provides the foundation for #2092 "Land context tool contracts v0".

#2092 can proceed once:
1. This contract (v1) is accepted
2. MCP bridge implementation is ready
3. Tool implementations follow these contracts

---

## Validation

These contracts were validated against:
- Existing contract patterns in `docs/surrealdb/context-*-contract.md`
- SurrealDB context-intelligence system design
- MCP protocol requirements

---

## Out of Scope

- Runtime implementation (MCP server)
- Database migrations
- Memory write operations
- Trading/risk/execution integration
- Live trading enablement

---

## LR Status

**LR remains NO-GO**.

These contracts are documentation-only. They do not:
- Enable live trading
- Modify risk controls
- Change execution behavior
- Alter LR status

---

## Files Changed

- `docs/surrealdb/context-tool-contracts-v1.md` (new)

---

## References

- Epic: #1976 (CDB Context Intelligence System)
- Parent: #2014
- Wave-12: #2091
- Tool Implementation: #2092