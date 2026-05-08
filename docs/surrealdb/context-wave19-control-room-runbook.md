# Wave-19 Visual Control Room — Runbook

> **Status**: `wave-19-complete` — artefacts delivered  
> **LR Status**: `NO-GO` — no real trades, no Echtgeld-Go  
> **Issues**: #2179 (anchor), #2180–#2185  
> **Epic**: #1976  
> **Branch**: `feat/wave19-visual-control-room-reporting`  

---

## 1. Overview

Wave-19 delivers the **Visual Control Room View Builder**: a pure, deterministic,
read-only domain service that renders inspection-oriented views of the CDB
knowledge context.  The builder is a signal surface — not an authorization
layer, not a trading console, and not a live-readiness gate.

The 9 view types are defined in the Wave-6 information model
(`docs/surrealdb/visual-control-room-model-v0.md`) and are served as
`visual_control_view`-conformant objects suitable for JSON serialization or
SurrealDB insertion.

---

## 2. Artefacts

| File | Purpose |
|------|---------|
| `tools/surrealdb/control_room_view_builder.py` | Domain service: `build_control_room_view_v1`, `build_all_views_v1` |
| `tools/mcp/control_room_tools.py` | MCP adapter: `handle_control_room_view` |
| `tests/unit/surrealdb/test_control_room_view_builder.py` | 72 unit tests for domain service |
| `tests/unit/tools/mcp/test_control_room_tools.py` | 24 unit tests for MCP adapter |
| `tests/fixtures/surrealdb/control_room/sample_bundle.json` | Canonical test fixture |

---

## 3. View Types

| View Type | Label | Primary Data Key |
|-----------|-------|-----------------|
| `knowledge_graph_view` | Knowledge Graph View | `sources`, `dependency_edges` |
| `architecture_map` | Architecture Map | `sources`, `dependency_edges` |
| `decision_chain_view` | Decision Chain View | `decisions`, `evidence_items` |
| `evidence_map` | Evidence Map | `evidence_items`, `decisions` |
| `risk_surface_report` | Risk Surface Report | `scope_drift_findings`, `contradiction_findings`, `quality_scores` |
| `stale_knowledge_view` | Stale Knowledge View | `stale_findings`, `memory_items` |
| `scope_drift_events` | Scope Drift Events | `scope_drift_findings` |
| `agent_memory_view` | Agent Memory View | `memory_items` |
| `quality_score_dashboard` | Quality Score Dashboard | `quality_scores` |

---

## 4. Input Bundle Shape

All view types consume the same in-memory bundle shape:

```json
{
  "meta": {
    "scope_id": "string (required, non-empty)",
    "level": "artifact|domain|issue|system"
  },
  "sources": [
    {
      "source_path": "string",
      "has_documentation": true,
      "has_tests": true,
      "status": "current|stale|unknown",
      "owner": "string"
    }
  ],
  "decisions": [
    {
      "decision_id": "string",
      "status": "current|open|superseded|invalidated",
      "evidence_refs": ["ev-id"],
      "superseded_by": "dec-id (optional)"
    }
  ],
  "evidence_items": [
    {"evidence_id": "string", "strength": "strong|moderate|weak", "expired": false}
  ],
  "dependency_edges": [
    {
      "edge_id": "string",
      "from_source": "string",
      "to_source": "string",
      "confidence": "high|medium|low|unknown"
    }
  ],
  "contradiction_findings": [
    {"contradiction_id": "string", "severity": "blocking|watch|info", "status": "open|resolved|false_positive"}
  ],
  "stale_findings": [
    {"finding_id": "string", "stale_type": "string", "status": "open|refreshed|accepted_risk"}
  ],
  "scope_drift_findings": [
    {
      "finding_id": "string",
      "drift_type": "string",
      "severity": "blocking|watch|info",
      "status": "open|resolved|accepted_risk|false_positive",
      "required_action": "string",
      "human_go_required": true
    }
  ],
  "memory_items": [
    {"memory_id": "string", "trust_level": "strong|moderate|weak", "ttl_expired": false}
  ],
  "quality_scores": [
    {
      "scope_id": "string",
      "overall_grade": "good|weak|watch|blocking",
      "overall_score": 0.85,
      "blocking_dimensions": [],
      "watch_dimensions": [],
      "scored_at": "ISO-8601"
    }
  ]
}
```

Keys that are absent default to empty lists; the builder never errors on missing
optional keys (only `meta.scope_id` is required).

---

## 5. Usage

### Build a single view (Python)

```python
from tools.surrealdb.control_room_view_builder import build_control_room_view_v1

bundle = {...}  # in-memory context bundle
view = build_control_room_view_v1("risk_surface_report", bundle)
print(view.to_dict())
```

### Build all 9 views

```python
from tools.surrealdb.control_room_view_builder import build_all_views_v1

views = build_all_views_v1(bundle)
for v in views:
    print(v.view_type, v.payload)
```

### Via MCP adapter

```python
from tools.mcp.control_room_tools import handle_control_room_view

# Single view
result = handle_control_room_view(bundle=bundle, view_type="evidence_map")

# All views
result = handle_control_room_view(bundle=bundle)
```

---

## 6. Output Structure

Every `ControlRoomView` carries:

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | `str` | `"control-room-view-builder/v1"` |
| `view_id` | `str` | `"view:" + SHA256(view_type:scope:generated_at)[:32]` — deterministic |
| `view_type` | `str` | One of 9 VIEW_TYPES |
| `view_label` | `str` | Human-readable label |
| `target_scope` | `str` | `bundle.meta.scope_id` |
| `data_sources` | `list[DataSourceRef]` | Always `write_allowed=False` |
| `filters` | `dict` | Caller-supplied filter map |
| `required_queries` | `list[str]` | Suggested SurrealQL queries |
| `display_entities` | `list[str]` | Entities to surface in UI |
| `display_edges` | `list[str]` | Edge types to surface in UI |
| `warnings` | `list[str]` | Non-empty when findings detected |
| `generated_at` | `str` | ISO-8601 |
| `generated_by` | `str` | `"control_room_view_builder/v1"` |
| `export_formats` | `list[str]` | `["json","markdown","html","mermaid"]` |
| `guardrails` | `tuple[str,...]` | Always 5 non-empty guardrails |
| `payload` | `dict` | View-type-specific rendered content |

---

## 7. Guardrails

Every view carries these 5 embedded guardrails (see `GUARDRAILS` in the module):

1. View Builder is signal surface, not authorization layer.
2. No trading console. No runtime control. No Live-Freigabe.
3. No Live-Readiness-Go. No Echtgeld-Go.
4. read-only: no mutations anywhere in the view build path.
5. Human-GO required for any action after blocking findings.

---

## 8. Error Handling

`ControlRoomError` (subclass of `ValueError`) is raised for:
- `bundle` is not a `Mapping`
- `bundle.meta` is `None` or not a `Mapping`
- `bundle.meta.scope_id` is missing or empty
- `view_type` is not in `VIEW_TYPES`

The MCP adapter (`handle_control_room_view`) catches all `ControlRoomError`
instances and returns a structured error dict (`status="error"`) — no exceptions
propagate to callers.

---

## 9. Testing

```bash
# Unit tests only (fast, no containers)
pytest -q tests/unit/surrealdb/test_control_room_view_builder.py
pytest -q tests/unit/tools/mcp/test_control_room_tools.py

# Both together
pytest -q tests/unit/surrealdb/test_control_room_view_builder.py tests/unit/tools/mcp/test_control_room_tools.py
```

Expected: **96 passed**.

---

## 10. Invariants

- `write_allowed` is always `False` on all `DataSourceRef` instances.
- `guardrails` is always a non-empty tuple.
- `view_id` is deterministic for same `(view_type, scope_id, generated_at)`.
- No file I/O. No DB access. No network. No side effects.
- `build_control_room_view_v1` and `build_all_views_v1` are idempotent.
- Blocking findings produce warnings but never block view construction.
  Human-GO is required before acting on blocking findings — not automated here.
