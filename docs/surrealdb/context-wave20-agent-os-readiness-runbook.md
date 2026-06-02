# Agent OS Readiness Runtime v1 — Runbook

**Status:** `wave-20-complete`  
**Live-Readiness:** `NO-GO` (orthogonal to this runbook)  
**Board Stage:** `trade-capable` (ratified 2026-04-08 via Issue #1492 — orthogonal to LR; no live capital)  
**Issues:** #2191, #2192, #2193, #2194, #2195 | Parent: #2188 (Wave-20 anchor) | Epic: #1976  
**Branch:** `feat/wave20-agent-os-readiness-runtime`

---

## Purpose

The Agent OS Readiness Evaluator v1 evaluates the **health and readiness of the
Agent OS context intelligence system itself** — not the readiness of a specific
agent task.

This is orthogonal to the Wave-13 `context.readiness` MCP tool, which asks
"Is this agent task ready to proceed?"  
This evaluator asks: **"Is the Agent OS context intelligence system healthy?"**

It aggregates signals from all existing quality, trust, scope-drift, stale,
contradiction, and architect-signal modules and emits a **readiness level**
(signal only — not an authorization).

---

## Artefacts

| Artefact | Path | Issue |
|---|---|---|
| Evaluator | `tools/surrealdb/agent_os_readiness.py` | #2191 |
| MCP adapter | `tools/mcp/agent_os_readiness_tools.py` | #2192 |
| Report method | `AgentOsReadinessResult.to_report_markdown()` | #2193 |
| Evaluator tests | `tests/unit/surrealdb/test_agent_os_readiness.py` | #2194 |
| MCP tests | `tests/unit/tools/mcp/test_agent_os_readiness_tools.py` | #2194 |
| Fixture | `tests/fixtures/surrealdb/agent_os_readiness/sample_bundle.json` | #2194 |
| Runbook | `docs/surrealdb/context-wave20-agent-os-readiness-runbook.md` | #2195 |
| Gates | `docs/surrealdb/context-wave20-completion-gates.md` | #2196 |

Registry modified: `tools/mcp/registry.py`  
PermissionGuard modified: `tools/mcp/permission_guard.py`  
Bridge modified: `tools/mcp/context_bridge.py`

---

## Readiness Levels

| Level | Meaning | Confidence |
|---|---|---|
| `blocked` | One or more blocking findings present. Action required before proceeding. | ≤ 0.30 |
| `weak` | No blockers, but ≥3 watch-level findings or missing bundle inputs. | 0.35–0.55 |
| `acceptable` | No blockers, 1–2 weak findings. Proceed with caution. | 0.60–0.80 |
| `strong` | No blockers, no weak findings. System healthy. | ≈ 0.95 |

**These levels are signals, not authorizations.**  
A `strong` readiness level does NOT mean Live-Readiness-Go.  
Live-Readiness remains `NO-GO` regardless.

---

## Blocking Trigger Conditions

A finding contributes a **blocking finding** if any of the following is true:

| Source | Condition |
|---|---|
| Quality scoring | `overall_grade == "blocking"` |
| Scope drift findings | Open finding with `severity == "blocking"` |
| Contradiction findings | Open finding with `severity == "blocking"` |
| Stale findings | Open finding with `stale_type == "source_deleted"` OR `severity == "blocking"` |
| Architect signals | Open signal with `severity == "blocking"` |

Findings with `status` in `{"resolved", "accepted_risk", "accepted_stale", "false_positive"}` are excluded.

---

## Input Bundle Shape

Same shape as used in all prior waves (Wave-15 through Wave-19).  
Only `meta.scope_id` is required; all other keys default to `[]`.

```json
{
  "meta": {
    "scope_id": "my-scope",        // required, non-empty string
    "level": "artifact|domain|issue|system"
  },
  "sources": [...],                // optional
  "decisions": [...],              // optional
  "evidence_items": [...],         // optional
  "contradiction_findings": [...], // optional
  "stale_findings": [...],         // optional
  "scope_drift_findings": [...],   // optional
  "memory_items": [...],           // optional
  "dependency_edges": [...],       // optional
  "operator_certification": {...}  // optional (#2801); alias: context_certification
}
```

---

## Operator certification integration (#2801)

Optional bundle field `operator_certification` carries a subset of the
`make context-certify` proof pack (`CertifyReport.to_dict()`). The evaluator
reads it in-memory only — no file, DB, or network access.

Example (certified with expected skipped checks):

```json
{
  "meta": {"scope_id": "phase2-adoption", "level": "domain"},
  "operator_certification": {
    "final_verdict": "certified",
    "gate_matrix": [
      {
        "check_id": "registry_all_read_only",
        "status": "pass",
        "blocking": true,
        "detail": "ok"
      }
    ],
    "skipped_checks_with_reason": [
      {
        "check": "context-smoke-db",
        "reason": "not run by certification (operator-only)"
      }
    ],
    "safety_flags": {
      "PERSIST_ALLOWED": false,
      "MUTATION_ALLOWED": false
    }
  }
}
```

PASS / WARN / FAIL / BLOCKED / SKIPPED semantics and adoption-claim rules:
see [SurrealDB Context MCP Access Runbook](../runbooks/surrealdb_context_mcp_access.md)
(certification adoption matrix, #2801).

---

## Output Structure

`AgentOsReadinessResult` fields:

| Field | Type | Description |
|---|---|---|
| `readiness_id` | `str` | SHA-256(scope_id\|generated_at)[:16] — deterministic |
| `target_scope` | `str` | Value of `meta.scope_id` |
| `readiness_level` | `str` | `blocked / weak / acceptable / strong` |
| `blocking_findings` | `tuple[str, ...]` | Descriptions of all blocking findings |
| `weak_findings` | `tuple[str, ...]` | Descriptions of all watch/weak findings |
| `missing_inputs` | `tuple[str, ...]` | Empty or absent bundle keys |
| `recommended_next_reads` | `tuple[str, ...]` | Minimum recommended reads (6 items) |
| `required_validation` | `tuple[str, ...]` | Steps required based on readiness level |
| `guardrails` | `tuple[str, ...]` | Always 6 items, always non-empty |
| `confidence` | `float` | 0.0–1.0; capped at 0.30 when blocked |
| `generated_at` | `str` | ISO-8601 UTC timestamp |
| `schema_version` | `str` | `"agent-os-readiness/v1"` |

---

## Report Output (#2193)

The `to_report_markdown()` method renders a human-readable Markdown report.

Accessible via:
- **Python:** `result.to_report_markdown()`
- **MCP:** `handle_agent_os_readiness(bundle=..., include_report=True)` → `result["report_markdown"]`

The report includes: readiness level, confidence, blocking findings, weak findings,
missing inputs, required validation, recommended next reads, guardrails, and an
explicit statement that readiness ≠ Live-Go.

---

## Usage Examples

### Python — direct evaluator

```python
from tools.surrealdb.agent_os_readiness import evaluate_agent_os_readiness_v1

bundle = {
    "meta": {"scope_id": "my-scope", "level": "domain"},
    "sources": [...],
    "evidence_items": [...],
    # ... other keys optional
}

result = evaluate_agent_os_readiness_v1(bundle)
print(result.readiness_level)       # "strong" / "acceptable" / "weak" / "blocked"
print(result.confidence)            # 0.0–1.0
print(result.blocking_findings)     # () if healthy
print(result.to_report_markdown())  # full Markdown report
```

### Python — MCP adapter

```python
from tools.mcp.agent_os_readiness_tools import handle_agent_os_readiness

response = handle_agent_os_readiness(bundle=bundle, include_report=True)
print(response["status"])           # "ok" or "error"
print(response["readiness_level"])  # "strong" / ...
print(response["report_markdown"])  # Markdown string
```

### ContextBridge

```python
from tools.mcp.context_bridge import ContextBridge

bridge = ContextBridge()
result = bridge.execute_tool(
    "cdb_agent_os_readiness",
    {"bundle": bundle, "as_of": "2026-05-08T12:00:00+00:00"}
)
```

---

## Guardrails

These 5 guardrails are embedded in every `AgentOsReadinessResult` and every
MCP response (including error responses):

1. **Agent OS Readiness is a signal, not an authorization.**
2. **No trading console. No runtime control. No Live-Freigabe.**
3. **No Live-Readiness-Go. No Echtgeld-Go.**
4. **read-only: no mutations anywhere in the readiness evaluation path.**
5. **Human-GO required for any action after blocking findings.**

---

## Readiness Signal ≠ Live-Go

> A `strong` readiness level confirms that the Agent OS context intelligence
> system is healthy based on the provided bundle.  
> **It is not a Live-Readiness-Go.**  
> **It is not an Echtgeld-Go.**  
> **It is not a trading authorization of any kind.**
>
> Live-Readiness status is controlled exclusively via
> `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` and associated
> LR-STATE.yaml files.  Current status: **NO-GO**.

---

## Error Handling

`AgentOsReadinessError` (subclass of `ValueError`) is raised by the evaluator when:
- `bundle` is `None` or not a mapping
- `bundle.meta` is not a mapping
- `bundle.meta.scope_id` is absent or empty

The MCP adapter catches all exceptions and returns `status="error"` with an
appropriate error code (`missing_bundle`, `invalid_bundle`, `evaluator_error`,
`internal_error`).  The MCP adapter never propagates exceptions to the caller.

---

## Invariants

- `write_allowed` is never set anywhere in the evaluation path.
- `guardrails` is always a 5-element tuple matching the module constant `GUARDRAILS`.
- `readiness_id` is deterministic: same `scope_id` + same `as_of` → same ID.
- No file I/O, DB access, network calls, or side-effects anywhere in the path.
- The evaluator is idempotent: calling it multiple times with the same inputs
  produces identical outputs.
- Blocking findings always produce `readiness_level == "blocked"` and
  `confidence ≤ 0.30`.
- Resolved / accepted_risk / accepted_stale / false_positive findings are
  excluded from all counts.

---

## Testing

```bash
# Wave-20 evaluator tests (new)
pytest -q tests/unit/surrealdb/test_agent_os_readiness.py

# Wave-20 MCP adapter tests (new)
pytest -q tests/unit/tools/mcp/test_agent_os_readiness_tools.py

# Full SurrealDB suite (must stay green)
pytest -q tests/unit/surrealdb/

# Full MCP suite (must stay green)
pytest -q tests/unit/tools/mcp/

# Ruff lint
ruff check tools/surrealdb/agent_os_readiness.py \
           tools/mcp/agent_os_readiness_tools.py \
           tests/unit/surrealdb/test_agent_os_readiness.py \
           tests/unit/tools/mcp/test_agent_os_readiness_tools.py
```
