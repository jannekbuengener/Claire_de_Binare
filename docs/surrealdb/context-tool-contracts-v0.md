# Context Tool Contracts v0

**Issue**: #2092
**Status**: Contract Landed
**Date**: 2026-05-03
**Agent**: Gemini (Audit & Review)

## Overview

This document defines the v0 contracts for the Context Tools — a set of read-only tools that provide agents access to the SurrealDB Context Intelligence System without direct table access or write permissions.

## Scope

These contracts define **v0** of the Context Tools:
- Read-only agent access layer
- Documentation of tool contracts
- No runtime/MCP implementation

## Non-Goals

- No tool writes to Repo files
- No tool provides Live-Go
- No tool triggers Runtime actions
- No tool uses Memory as sole truth source

## Tool Contracts v0

### 1. context.search

**Purpose**: Search the Context Intelligence knowledge base using keyword and structured queries.

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
- `timeout`: Retrieval timeout

**Guardrails**:
- Read-only (no write to any system)
- Returns SourceRefs for all results
- Includes confidence scores
- Warnings array for edge cases

**Example**:
```bash
context-tool search --query "policy_hash" --limit 10
```

---

### 2. context.trace

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
- SourceRefs in lineage

**Example**:
```bash
context-tool trace --target-id "evt_abc123" --depth 10
```

---

### 3. context.explain_source

**Purpose**: Explain the provenance and reasoning behind a specific source or evidence item.

**Input Schema**:
```json
{
  "source_ref": "string (required)",
  "include_chain": "boolean (optional, default: true)"
}
```

**Output Schema**:
```json
{
  "tool": "context.explain_source",
  "status": "ok",
  "explanation": {
    "source_ref": "string",
    "provenance": {
      "created_by": "string",
      "created_at": "ISO8601",
      "chain": ["string"]
    },
    "reasoning": "string",
    "confidence": "float",
    "supporting_evidence": ["string"],
    "warnings": ["string"]
  }
}
```

**Failure Modes**:
- `source_not_found`: Source reference does not exist
- `chain_incomplete`: Provenance chain is incomplete

**Guardrails**:
- Read-only explanation
- Shows provenance chain
- Includes confidence and warnings

**Example**:
```bash
context-tool explain-source --source-ref "doc:LR-AUDIT-STATUS-2026-03-05"
```

---

### 4. context.show_snapshot

**Purpose**: Show a point-in-time snapshot of the context state.

**Input Schema**:
```json
{
  "snapshot_id": "string (required)",
  "include_details": "boolean (optional, default: true)"
}
```

**Output Schema**:
```json
{
  "tool": "context.show_snapshot",
  "status": "ok",
  "snapshot": {
    "snapshot_id": "string",
    "created_at": "ISO8601",
    "scope": "string",
    "items": [
      {
        "id": "string",
        "type": "string",
        "state": "string"
      }
    ],
    "metadata": {}
  }
}
```

**Failure Modes**:
- `snapshot_not_found`: Snapshot ID does not exist

**Guardrails**:
- Read-only snapshot retrieval
- Timestamps included

**Example**:
```bash
context-tool show-snapshot --snapshot-id "snap_2026-05-01"
```

---

### 5. context.show_audit

**Purpose**: Show audit trail for a specific entity or action.

**Input Schema**:
```json
{
  "entity_id": "string (required)",
  "audit_type": "string (optional, default: all)",
  "limit": "integer (optional, default: 50)"
}
```

**Output Schema**:
```json
{
  "tool": "context.show_audit",
  "status": "ok",
  "audit": {
    "entity_id": "string",
    "entries": [
      {
        "entry_id": "string",
        "timestamp": "ISO8601",
        "action": "string",
        "actor": "string",
        "result": "string",
        "source_ref": "string"
      }
    ]
  }
}
```

**Failure Modes**:
- `entity_not_found`: Entity ID does not exist

**Guardrails**:
- Read-only audit access
- Full action history

**Example**:
```bash
context-tool show-audit --entity-id "decision:trade-capable"
```

---

### 6. context.package

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
- Package ID is deterministic

**Example**:
```bash
context-tool package --artifacts "art_001,art_002" --format markdown
```

---

### 7. context.readiness

**Purpose**: Show read-only readiness evaluation metadata for a specific component or system.

**Input Schema**:
```json
{
  "component": "string (required)",
  "include_details": "boolean (optional, default: false)"
}
```

**Output Schema**:
```json
{
  "tool": "context.readiness",
  "status": "ok",
  "readiness": {
    "component": "string",
    "evaluated_at": "ISO8601",
    "status": "not_ready|partial|ready",
    "checks": [
      {
        "name": "string",
        "status": "pass|fail|skip",
        "details": "string"
      }
    ],
    "confidence": "float (0.0-1.0)",
    "warnings": ["string"]
  }
}
```

**Failure Modes**:
- `component_not_found`: Component does not exist
- `evaluation_unavailable`: Readiness data not available

**Guardrails**:
- Read-only evaluation metadata only
- **Does NOT imply Live Readiness or Echtgeld readiness**
- Status is evaluation metadata, not authorization
- Warnings clarify when status is partial

**Important**: The `status` field indicates evaluation state for tooling purposes only. It does NOT provide:
- Live trading authorization
- Echtgeld permission
- Risk approval
- Execution clearance

This tool provides read-only context metadata for tooling, not operational authorization.

**Example**:
```bash
context-tool readiness --component "risk-service" --include-details
```

---

## Common Contract Elements

All v0 tools include:

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

All v0 tools are **read-only**:

- No tool writes to the knowledge base
- No tool modifies memory state
- No tool triggers runtime actions
- No tool provides Live-Go authorization
- No tool makes trading/risk/execution decisions

---

## Guardrails Summary

| Guardrail | Applied |
|-----------|---------|
| No DB writes | ✅ |
| No Memory writes | ✅ |
| No Live-Go | ✅ |
| No Echtgeld implication | ✅ |
| SourceRefs required | ✅ |
| Confidence included | ✅ |
| Warnings when applicable | ✅ |

---

## LR Status

**LR remains NO-GO**.

These contracts are documentation-only. They do not:
- Enable live trading
- Modify risk controls
- Change execution behavior
- Alter LR status
- Provide operational authorization

---

## Files Changed

- `docs/surrealdb/context-tool-contracts-v0.md` (new)

---

## References

- Epic: #1976 (CDB Context Intelligence System)
- Parent: #2091 (Wave-12 MCP bridge)
- Depends on: #2017 (Tool Vision), #2080 (Query Surface), #2087 (Output Contract)
- Follow-up: #2102 (Wave-12 completion gates)