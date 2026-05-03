# Context Query CLI Output Contract

**Issue**: #2087
**Status**: Implemented (output already standardized)
**Date**: 2026-05-03

## Overview

The context_query CLI produces standardized output across all query commands. This document captures the output contract for agent-readable (JSON) and human-readable (text/markdown) formats.

## JSON Output Contract

All query commands return a consistent JSON structure:

```json
{
  "schema_version": "context-query/v0",
  "command": "<command-name>",
  "status": "ok",
  "query": "<surrealql-query>",
  "classification": {
    "statement": "...",
    "normalized": "...",
    "allowed": true,
    "operation": "SELECT",
    "reason": "..."
  },
  "count": <number>,
  "results": [...]
}
```

### Standard Fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Version identifier for contract |
| `command` | string | Executed command name |
| `status` | string | "ok" or "error" |
| `query` | string | The SurrealQL query executed |
| `classification` | object | Read-only classification result |
| `classification.statement` | string | Original statement |
| `classification.normalized` | string | Normalized statement |
| `classification.allowed` | boolean | Whether query passes guardrails |
| `classification.operation` | string | SQL operation (SELECT, etc.) |
| `classification.reason` | string | Classification reasoning |
| `count` | integer | Number of results |
| `results` | array | Query results array |

### Command-Specific Fields

Some commands add additional fields:

| Command | Additional Fields |
|---------|-------------------|
| `trace` | `depth` (int) |
| `explain-source` | `warnings` (string[]) |
| `show-drift` | `findings` (object[]) with severity levels |

## Text Output

Human-readable text format includes:
- status
- operation (from classification)
- allowed (from classification)
- query
- count
- results (truncated to 20)
- surrealdb_connection status
- error/message if applicable

## Markdown Output

Markdown format includes:
- Header with command name
- Status as bold element
- Classification details
- Query, count, results formatted
- Error details if applicable

## Empty Result Behavior

When results are empty (`count: 0`):
- JSON returns `"results": []`
- Text renders as "count: 0"
- Markdown renders as "count: 0"

## Error Output

Error responses use consistent structure:
```json
{
  "schema_version": "context-query/v0",
  "status": "error",
  "error": "<ERROR_CODE>",
  "message": "<human-readable-message>"
}
```

Exit codes:
- 0: success
- 1: validation error
- 2: argparse usage error
- 3: input/config not found
- 4: unsupported format
- 5: write denied
- 6: internal error

## Commands Covered

- `classify`
- `find-artifact`
- `find-doc`
- `find-symbol`
- `show-symbol`
- `find-imports`
- `show-imports-for-artifact`
- `trace`
- `explain-source`
- `show-snapshot`
- `show-drift`
- `show-audit`

## Guardrails

- All queries are read-only (SELECT only)
- No trading/risk/execution table access
- Statement classification enforced
- No live DB networking requirement