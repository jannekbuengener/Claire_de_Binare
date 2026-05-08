# Scope Drift Firewall Runbook

**Status**: Operational  
**Authority**: Issue #2168 / Wave-17 / Epic #1976  
**Parent**: #2162

This runbook describes how operators and agents use the Scope Drift Firewall
(Wave-17) to scan, read, interpret, and act on scope drift findings.

**LR-Status: NO-GO** — this runbook covers read-only detection tooling only.
No live capital, no Echtgeld-Go, no trading implication.

---

## 1. Purpose and Scope

The Scope Drift Firewall detects when an agent or operator's current work
deviates from a defined, authorised scope. Detected findings cover nine
drift types:

| Drift type | Meaning |
|------------|---------|
| `path_out_of_scope` | A file or directory path is outside the allowed scope |
| `domain_out_of_scope` | A domain or conceptual area is outside the allowed scope |
| `issue_out_of_scope` | A referenced GitHub issue is outside the issue scope |
| `parked_topic_activated` | A parked or restricted topic has been activated without GO |
| `runtime_surface_touched` | A runtime or service surface has been touched |
| `trading_surface_touched` | A trading, risk, or execution surface has been touched |
| `unexpected_dependency_expansion` | Dependency graph expanded beyond allowed scope |
| `unauthorized_write_intent` | Write operation attempted without Human-GO token |
| `missing_human_go` | A Human-GO gate is required but not present |

**Detection is signal, not action authority.** No finding authorises any
automated action, write, deployment, trade, or live-go.

---

## 2. Non-Goals

The following are explicitly out of scope for this system:

- **No auto-fix** — the firewall detects and reports; it never corrects automatically.
- **No auto-write** — no DB, filesystem, GitHub, or runtime write from any of these tools.
- **No auto-merge** — the firewall does not open, approve, or merge pull requests.
- **No auto-close** — the firewall does not close issues or milestones.
- **No Live-Readiness-Go** — scope drift findings do not change the LR verdict.
  The current verdict remains **NO-GO**.
- **No Echtgeld-Go** — scope drift findings do not authorise real capital operations.
- **No runtime enable** — the firewall does not enable, start, or configure any
  runtime service or container.
- **No CI gate on its own** — `--fail-on-blocking` is available for operator-controlled
  CI integration but is not automatically enforced in any active workflow.

---

## 3. Tool Overview

### 3.1 Scan Service — `scan_scope_drift_v1`

- **Module**: `tools/surrealdb/scope_drift_firewall.py`
- **Schema version**: `scope-drift-firewall/v1`
- **API**: `scan_scope_drift_v1(bundle, as_of=None) → ScopeDriftScanResult`
- **Read-only**. No DB access. No network. No file output. No writes.
- **Deterministic**: SHA256[:16]-based `drift_id` generation, clock via
  `core.utils.clock.utcnow` (no direct wall-clock calls).
- **Input**: a `Mapping[str, Any]` bundle with scope context and work items.
- **Output**: `ScopeDriftScanResult` containing `findings`, `blocking_count`,
  `overall_status`, `severity_summary`, and `guardrails`.

### 3.2 CLI — `scope_drift_cli.py`

- **Module**: `tools/surrealdb/scope_drift_cli.py`
- **Invocation**: `python -m tools.surrealdb.scope_drift_cli`

Three subcommands:

| Command | Purpose |
|---------|---------|
| `scan-scope-drift` | Scan input bundle, output all scope drift findings |
| `show-scope-drift` | Show a single finding by `--drift-id` |
| `report-scope-drift` | Generate a structured summary report |

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | Success (no blocking findings, or `--fail-on-blocking` not set) |
| `1` | Blocking findings present and `--fail-on-blocking` flag was set |
| `2` | CLI or input/validation error |
| `3` | `show-scope-drift`: `drift_id` not found in bundle |

Output formats: `--format json` (default) or `--format markdown`.

### 3.3 MCP Tool — `cdb_context_scope_drift`

- **Handler**: `tools/mcp/scope_drift_tools.py`
- **Tool name**: `cdb_context_scope_drift`
- **Schema version**: `scope-drift-mcp/v1`
- **Bundle-driven**: a `bundle` object must be supplied in the request — the tool
  never reads from a database, filesystem, or network.
- **Read-only**. No DB. No network. No GitHub calls.

Supported filter parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `bundle` | Input scan bundle (required) | — |
| `severity` | Filter by severity: `info`, `warning`, `blocking` | all |
| `scope_type` | Filter by drift type (any of the 9 types) | all |
| `target_ref` | Filter by target artifact reference | all |
| `blocking` | If `true`, return blocking findings only | `false` |
| `limit` | Maximum findings returned | `100` (max `500`) |
| `as_of` | Advisory ISO-8601 UTC timestamp | from bundle `meta` |

### 3.4 Blocking Output Helper — `build_blocking_output`

- **Module**: `tools/surrealdb/scope_drift_blocking.py`
- **Schema version**: `scope-drift-blocking/v1`
- **API**: `build_blocking_output(scan_result) → dict`
- Always safe to call. Returns `blocking: false` and empty `findings` when
  no blocking findings are present.
- **Rendered in CLI** via `report-scope-drift` (when `blocking_count > 0`).
- **Returned in MCP** under the `blocking_output` key (when `blocking_count > 0`).

---

## 4. How to Run a Scope Check

### 4.1 Prepare a Bundle

A bundle is a JSON object describing the current work scope. Minimum structure:

```json
{
  "meta": {
    "as_of": "2026-05-08T00:00:00+00:00",
    "task_id": "task-example-001"
  },
  "scope": {
    "task_scope": "Human-readable description of the allowed scope",
    "allowed_issue_refs": ["#2162", "#2167", "#2168", "#2169"],
    "allowed_paths": ["docs/surrealdb/", "tests/"],
    "allowed_domains": ["surrealdb", "context-intelligence"],
    "operation_mode": "write (code/docs)"
  },
  "work_items": [
    {
      "item_id": "work-item-001",
      "description": "Create scope drift runbook",
      "target_path": "docs/surrealdb/scope-drift-runbook.md",
      "domain": "surrealdb",
      "issue_ref": "#2168"
    }
  ]
}
```

A deterministic fixture is available at:
`tests/fixtures/surrealdb/scope_drift/sample_bundle.json`

### 4.2 CLI Scan

```bash
# Full scan — JSON output (default)
python -m tools.surrealdb.scope_drift_cli scan-scope-drift --bundle <path/to/bundle.json>

# Full scan — Markdown output
python -m tools.surrealdb.scope_drift_cli scan-scope-drift \
    --bundle <path/to/bundle.json> \
    --format markdown

# Full scan with blocking exit code (for operator-controlled CI)
python -m tools.surrealdb.scope_drift_cli scan-scope-drift \
    --bundle <path/to/bundle.json> \
    --fail-on-blocking

# Structured report including blocking output section
python -m tools.surrealdb.scope_drift_cli report-scope-drift \
    --bundle <path/to/bundle.json> \
    --format markdown

# Show a specific finding by drift_id
python -m tools.surrealdb.scope_drift_cli show-scope-drift \
    --bundle <path/to/bundle.json> \
    --drift-id <16-char-hex>
```

### 4.3 MCP Tool Call

```python
result = bridge.execute_tool("cdb_context_scope_drift", {
    "bundle": bundle_dict,           # required
    "severity": "blocking",          # optional filter
    "blocking": True,                # optional: blocking findings only
    "limit": 50                      # optional: cap findings returned
})
```

The response includes `status`, `summary` (counts, severity breakdown),
`findings`, `guardrails`, `scan_status`, `scanned_at`, and `blocking_output`
(when blocking findings are present).

---

## 5. Reading a Finding

Each `ScopeDriftFinding` has the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `drift_id` | str | Deterministic SHA256[:16] identifier |
| `drift_type` | str | One of the 9 drift types (see Section 1) |
| `severity` | str | `info`, `warning`, or `blocking` |
| `allowed_scope` | str | Human-readable description of what was allowed |
| `observed_scope` | str | Human-readable description of what was observed |
| `required_action` | str | `stop`, `review`, `split_scope`, or `request_go` |
| `target_ref` | str | The artifact, path, or item that triggered the finding |
| `human_go_required` | bool | Whether Human-GO is required before proceeding |
| `detected_by` | str | Schema version string of the detecting component |
| `detected_at` | str | ISO-8601 UTC timestamp |
| `status` | str | `open`, `acknowledged`, `false_positive`, `accepted_risk`, `resolved` |
| `metadata` | dict | Additional context (optional) |

### 5.1 Reading `allowed_scope` vs `observed_scope`

`allowed_scope` describes what the current task was authorised to touch. Compare it
with `observed_scope` to understand the deviation:

```
allowed_scope: "docs/surrealdb/ and tests/"
observed_scope: "services/risk/service.py"
```

This indicates the work item targeted a path outside the allowed scope. The
`drift_type` `path_out_of_scope` confirms this. The `required_action` `stop`
means the operator must halt and reassess before continuing.

---

## 6. Interpreting Drift Status

### 6.1 `overall_status` Values

| Status | Meaning | Required action |
|--------|---------|-----------------|
| `ok` | No scope drift findings | Continue within scope |
| `blocked_scope_drift` | One or more blocking findings | **Stop. Do not proceed.** Request Human-GO if write intent. |

Any `overall_status` of `blocked_scope_drift` is a hard stop signal.

### 6.2 Severity Levels

| Severity | Description | Default action |
|----------|-------------|----------------|
| `blocking` | Scope boundary crossed, write intent present, or Human-GO missing | **Stop** |
| `warning` | Scope boundary approached; no confirmed violation | Review and narrow scope |
| `info` | Informational note — scope is clear but adjacent context noted | Note and continue |

Blocking findings must be resolved before any write, merge, or deployment.
They do not resolve automatically.

---

## 7. Recognising Runtime and Trading Surfaces

Two drift types specifically protect critical system surfaces:

### 7.1 `runtime_surface_touched`

Triggered when a work item targets a path or domain associated with runtime
or service operation:

- Surface type `runtime` or `service` in the work item
- Paths under `services/`, `infrastructure/compose/`, `infrastructure/database/`,
  `core/safety/`

**Required action**: `stop`. Human-GO required before any write.

### 7.2 `trading_surface_touched`

Triggered when a work item targets a path or domain associated with trading,
risk, or execution:

- Surface type `trading` in the work item
- Paths under `services/risk/` or `services/execution/`

**Required action**: `stop`. Human-GO required before any write.
Board stage `trade-capable` does **not** authorise this. LR verdict remains **NO-GO**.

---

## 8. Human-GO Escalation

### 8.1 When Human-GO Is Required

Human-GO is required whenever:

- Any finding has `human_go_required: true`
- `overall_status` is `blocked_scope_drift`
- `drift_type` is `unauthorized_write_intent` or `missing_human_go`
- Any blocking finding is present

### 8.2 Escalation Procedure

1. **Stop all writes** — do not commit, push, merge, or deploy.
2. **Read the blocking output** — review `operator_action`, `affected_artifacts`,
   and `recommended_next_reads` from `build_blocking_output`.
3. **Read canonical governance files**:
   - `AGENTS.md`
   - `docs/runbooks/CONTROL_REGISTER.md`
   - `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
   - `knowledge/governance/CDB_AGENT_POLICY.md`
4. **Produce a dry-run preview** — document proposed changes with full scope analysis.
5. **Wait for explicit Human-GO** — the operator or human reviewer must issue
   an explicit `GO IMPLEMENT` or equivalent authorisation.
6. **Do not self-approve** — agents must not interpret a blocking drift finding
   as permission to proceed after self-assessment.

---

## 9. Stop Conditions

The following stop conditions apply when using the Scope Drift Firewall.
Stop immediately if any of these are true:

| Condition | Action |
|-----------|--------|
| `overall_status == "blocked_scope_drift"` | Stop. No write. No merge. No deploy. |
| `drift_type == "runtime_surface_touched"` | Stop. Human-GO required. |
| `drift_type == "trading_surface_touched"` | Stop. Human-GO required. LR NO-GO. |
| `drift_type == "unauthorized_write_intent"` | Stop. Human-GO required. |
| `drift_type == "missing_human_go"` | Stop. Obtain Human-GO first. |
| `drift_type == "parked_topic_activated"` | Stop. Read governance canon. |
| Any `severity == "blocking"` finding | Stop. Resolve before proceeding. |

---

## 10. Anti-Actions (Prohibited)

The following actions are **explicitly prohibited** and must never be performed
in response to a scope drift finding:

| Anti-action | Description |
|-------------|-------------|
| `no_auto_fix` | Do not automatically fix the scope violation |
| `no_auto_write` | Do not write to any file, DB, or GitHub resource |
| `no_auto_merge` | Do not merge pull requests |
| `no_auto_close` | Do not close issues or milestones |
| `no_live_go` | Do not issue a Live-Readiness-Go |
| `no_lr_go` | Do not change the LR verdict |
| `no_echtgeld_go` | Do not authorise real capital operations |
| `no_runtime_enable` | Do not start, enable, or configure runtime services |

---

## 11. Guardrails

The following guardrails are embedded in every scan result and MCP response:

1. Scope Drift Detection is signal, not authorization.
2. No auto-fix. No auto-write.
3. No Live-Readiness-Go.
4. No Echtgeld-Go.
5. Human-GO required for any write after blocking scope drift.

---

## 12. Troubleshooting

| Symptom | Cause | Action |
|---------|-------|--------|
| `overall_status: ok` but work seems out of scope | Bundle may be missing work items or scope definition | Review bundle `scope.allowed_paths` and `work_items` |
| All findings have `severity: info` | Scope boundaries are well-defined; items are within bounds | Proceed within scope |
| `drift_type: path_out_of_scope` on expected path | `allowed_paths` list is too narrow | Expand `allowed_paths` with Human-GO if needed |
| `drift_type: missing_human_go` on write operation | `operation_mode` contains `write` but no `human_go_token` in bundle | Add explicit `human_go_token` after obtaining Human-GO |
| CLI exits with code `1` | `--fail-on-blocking` set and blocking findings present | Review and resolve blocking findings |
| MCP returns `"unknown_tool"` | Tool not registered or wrong name | Confirm `cdb_context_scope_drift` is in registry |

---

## 13. References

| Resource | Path |
|----------|------|
| Scope Drift Firewall Service | `tools/surrealdb/scope_drift_firewall.py` |
| Scope Drift CLI | `tools/surrealdb/scope_drift_cli.py` |
| Scope Drift Blocking Helper | `tools/surrealdb/scope_drift_blocking.py` |
| MCP Scope Drift Tool | `tools/mcp/scope_drift_tools.py` |
| MCP Registry | `tools/mcp/registry.py` |
| Permission Guard | `tools/mcp/permission_guard.py` |
| Context Bridge | `tools/mcp/context_bridge.py` |
| Firewall Tests | `tests/unit/surrealdb/test_scope_drift_firewall.py` |
| CLI Tests | `tests/unit/surrealdb/test_scope_drift_cli.py` |
| Blocking Tests | `tests/unit/surrealdb/test_scope_drift_blocking.py` |
| MCP Tests | `tests/unit/tools/mcp/test_scope_drift_tools.py` |
| Sample Fixture | `tests/fixtures/surrealdb/scope_drift/sample_bundle.json` |
| Wave-17 Completion Gates | `docs/surrealdb/context-wave17-completion-gates.md` |
| Context Tool Contracts v1 | `docs/surrealdb/context-tool-contracts-v1.md` |
| MCP Access Runbook | `docs/runbooks/surrealdb_context_mcp_access.md` |
| Control Register | `docs/runbooks/CONTROL_REGISTER.md` |

---

## 14. Clearances and Verdict

| Item | Status |
|------|--------|
| LR Verdict | **NO-GO** (unchanged) |
| Board Stage | `trade-capable` (orthogonal) |
| Echtgeld | Not authorized |
| Write Path | Disabled (no auto-write, no auto-fix) |
| Runtime/MCP Live | Not authorized |
| Auto-Fix | Not authorized |
