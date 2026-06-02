# Control Room Read-Only Signal Layer v1

**Issue**: #2802  
**Status**: Contract Defined  
**Date**: 2026-06-02  
**Parent**: #2778 (Phase-2 epic)  
**Epic**: #1976

## Overview

The control-room signal layer aggregates operator-visible status, warnings, and
guardrails from in-memory Phase-2 artifacts into a single deterministic envelope.
It is a **data layer only** — no UI, no dashboard, no runtime wiring.

Implementation: [`tools/surrealdb/control_room_signal_layer.py`](../../tools/surrealdb/control_room_signal_layer.py)

## Purpose

- Single read-only operator signal surface for Context/Memory/Operator readiness
- Compose signals from Context Package v2, hybrid ranking, decision replay v2,
  Agent OS readiness, and operator certification payloads
- Fail-closed severity aggregation (`PASS` / `WARN` / `FAIL` / `BLOCKED` / `SKIPPED` / `UNKNOWN`)
- Deterministic `content_hash` for audit and replay
- Redact secret-like fields before card serialization

## Non-Goals

- No authorization, Live-Go, or Echtgeld-Go derivation
- No productive SurrealDB writes; `PERSIST_ALLOWED=False`, `MUTATION_ALLOWED=False`
- No MCP tool handler in this slice (deferred follow-up)
- No UI/dashboard/Grafana/front-end buildout
- No replacement of Wave-19 visual view builder (see below)

## Relationship to Wave-19 View Builder

| Surface | Role |
|---------|------|
| [`control_room_view_builder.py`](../../tools/surrealdb/control_room_view_builder.py) | Nine `visual_control_view` types from legacy in-memory **bundles** (#2179) |
| MCP `cdb_control_room_view` | Adapter for view builder |
| **Signal layer v1** | Operator **signal envelope** from Phase-2 artifact dicts (#2802) |

The signal layer does not call `build_control_room_view_v1`. Future work may compose
both surfaces for a unified operator panel.

## Input Artifact Classes

All inputs are **optional** except `generated_for_scope`. Pass already-built payloads
(no DB, no network, no re-invocation of upstream evaluators inside the signal layer).

| Input | Typical source module |
|-------|----------------------|
| `context_package` | `build_context_package_v2()` |
| `ranked_results` | `rank_retrieval_results()` or `context_package.ranked_context.results` |
| `decision_replay` | `build_decision_replay_v2()` (preferred) or v1 |
| `agent_os_readiness` | `evaluate_agent_os_readiness_v1().to_dict()` |
| `operator_certification` | `CertifyReport` subset / `make context-certify` output |

## Severity Model

| Severity | Meaning |
|----------|---------|
| `PASS` | No adverse signals in aggregated cards |
| `WARN` | Caveats, weak matches, unresolved refs, or missing optional inputs |
| `FAIL` | Certification or gate failure (non-blocked adoption) |
| `BLOCKED` | Readiness blocked or certification blocked/fail adoption |
| `SKIPPED` | Certification explicitly skipped (with `skip_reason` when known) |
| `UNKNOWN` | Missing inputs or insufficient evidence to assert pass |

Rules:

- `FAIL` / `BLOCKED` from certification or readiness are **never downgraded**
- `WARN` requires visible `warnings` and/or `required_validation` where applicable
- Empty/minimal inputs yield `UNKNOWN` or `WARN`, never default `PASS`

## Output Envelope (summary)

| Field | Description |
|-------|-------------|
| `schema_version` | `control-room-signal-layer/v1` |
| `generated_for_scope` | Operator scope id (e.g. `issue:2802`) |
| `source_artifacts` | Present/missing status per input class (stable sort) |
| `summary_status` | Aggregated severity |
| `signal_cards` | Sorted cards with `card_id`, `source`, `severity`, `title`, `detail` |
| `blocking_findings` | Flat list of blocking messages |
| `warnings` | Flat list of warnings |
| `required_validation` | Operator validation steps (not authorization) |
| `guardrails` | Merged static + upstream guardrails |
| `limitations` | Missing inputs and upstream limitations |
| `determinism` | `content_hash` (wall-clock excluded from hash input) |

## Operator Consumption Semantics

- Signals are **orientation**, not approval to trade, deploy runtime, or write to SurrealDB
- `summary_status=PASS` does not change LR-SSOT (`NO-GO` remains in force)
- Board stage `trade-capable` is orthogonal and must not be read as live capital approval
- Weak/inferred ranking and unresolved replay evidence stay visible as warnings

## API Example

```python
from tools.surrealdb.control_room_signal_layer import (
    ControlRoomSignalLayerRequest,
    build_control_room_signal_layer_v1,
)

envelope = build_control_room_signal_layer_v1(
    ControlRoomSignalLayerRequest(
        generated_for_scope="issue:2802",
        context_package=package_dict,
        ranked_results=ranked_list,
        decision_replay=replay_dict,
        agent_os_readiness=readiness_dict,
        operator_certification=cert_dict,
        generated_at_or_as_of="2026-06-02T12:00:00+00:00",
    )
)
```

## Validation

```bash
pytest -q tests/unit/surrealdb/test_control_room_signal_layer.py
ruff check tools/surrealdb/control_room_signal_layer.py tests/unit/surrealdb/test_control_room_signal_layer.py
```

## Deferred Follow-Ups

- MCP expose (`cdb_control_room_signal_layer` or bridge handler)
- UI / control-room dashboard wiring
- Optional composition with Wave-19 view builder for unified panels
