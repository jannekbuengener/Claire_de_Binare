# LR-005 Specification: Deterministic Completion Reporting & State Visibility

**Version:** 1.0
**Status:** Ready for Review
**Date:** 2026-02-06
**Author:** CDB Repo Agent

---

## 1. Purpose

Establish a **read-only, deterministic reporting mechanism** for Live Readiness (LR) task completion state that:
- Generates machine-readable snapshots of canonical completion state
- Provides human-readable summary views for stakeholders
- Enables offline state reconstruction from Git history alone
- Supports operational visibility without GitHub API dependencies
- Operates as pure observer (no state mutations, no side effects)

---

## 2. Problem Statement

### 2.1 Current State (LR-004)

LR-004 provides:
- Canonical state files (`LR-*-STATE.yaml`)
- Validator enforcing schema integrity
- Fail-closed CI enforcement

**Gap:** No consolidated reporting mechanism for:
- Aggregated completion metrics (% done, blocked count)
- BLOCKED task visibility (reason, duration)
- Historical state reconstruction
- Machine-readable snapshot for downstream tooling

### 2.2 Use Cases

**UC-1: Project Manager Visibility**
- "How many LR tasks are complete? How many blocked?"
- "Which tasks are blocked and why?"

**UC-2: CI/CD Pipeline Integration**
- "Generate completion snapshot artifact for release metadata"
- "Export JSON for dashboard ingestion (Grafana, etc.)"

**UC-3: Historical Audit**
- "What was completion state at release v1.2.3?"
- "Reconstruct state from Git history at any commit SHA"

---

## 3. Scope

### 3.1 In Scope

**Core Functionality:**
- Read LR-TASKS.yaml (manifest) and LR-*-STATE.yaml (state files)
- Compute aggregated metrics (total, done, blocked counts)
- Extract BLOCKED task metadata (reason code, reason text, blocked timestamp)
- Generate deterministic outputs:
  - JSON snapshot (machine-readable)
  - Markdown snapshot (human-readable)

**Determinism Requirements:**
- Pure function: same inputs → same outputs
- Offline-capable: no network calls, no GitHub API
- Reproducible: running at same Git SHA produces identical output
- Clock-independent: no `now()` or dynamic date calculations in output

**Governance:**
- Observer role: reads state, does not modify
- No state transitions, no notifications, no actions

### 3.2 Out of Scope

**Explicitly Excluded:**
- State mutations (use manual STATE file updates via LR-004 workflows)
- Notifications (email, Slack, GitHub issues)
- Dashboards (use snapshot JSON as data source in separate system)
- GitHub API integration (API calls, commit status updates)
- Database persistence (snapshots are ephemeral, regenerated on-demand)
- CI Required Check (reporting is optional artifact generation)
- BLOCKED task auto-escalation or reminders
- SLA enforcement (e.g., "fail if blocked > 14 days")
- Age calculations (delegated to consumers; see §6 Determinism)

---

## 4. Data Model

### 4.1 Input Schema

**Inputs (Read-Only):**
1. `docs/live-readiness/LR-TASKS.yaml` (manifest)
2. `docs/live-readiness/LR-*-STATE.yaml` (per-task state files)

**Input Validation:**
- Leverage existing LR-004 validator for schema integrity
- LR-005 assumes inputs are valid (run LR-004 validator first)
- If invalid inputs detected, report error referencing LR-004

### 4.2 Output Schema: JSON Snapshot

**Conceptual Schema (Illustrative):**

```json
{
  "spec_version": "1.0",
  "snapshot_metadata": {
    "data_source": "docs/live-readiness/",
    "git_commit": "a1efea8",
    "git_branch": "main"
  },
  "summary": {
    "total_tasks": 4,
    "done_count": 3,
    "blocked_count": 1,
    "completion_percentage": 75.0
  },
  "tasks": [
    {
      "task_id": "LR-001",
      "task_title": "P0 Governance CI/CD Shield",
      "status": "DONE",
      "completion_timestamp": "2026-01-28T14:32:00Z",
      "completion_author": "jannekbuengener",
      "evidence_file": "docs/live-readiness/LR-001-EVIDENCE.md",
      "evidence_commit": "928d33f"
    },
    {
      "task_id": "LR-004",
      "task_title": "P0 Deterministic Completion Mechanism",
      "status": "BLOCKED",
      "blocked_reason_code": "RC_B400",
      "blocked_reason_text": "Implementation in progress - awaiting CI integration",
      "blocked_since": "2026-02-05T10:00:00Z",
      "blocked_since_epoch": 1738747200,
      "evidence_file": "docs/live-readiness/LR-004-EVIDENCE.md",
      "evidence_commit": "a1efea8"
    }
  ],
  "blocked_details": [
    {
      "task_id": "LR-004",
      "task_title": "P0 Deterministic Completion Mechanism",
      "reason_code": "RC_B400",
      "reason_text": "Implementation in progress - awaiting CI integration",
      "blocked_since": "2026-02-05T10:00:00Z",
      "blocked_since_epoch": 1738747200
    }
  ]
}
```

**Mandatory Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `spec_version` | String | Schema version (must be "1.0") |
| `snapshot_metadata.data_source` | String | Path to STATE file directory |
| `snapshot_metadata.git_commit` | String | Git SHA at snapshot time (deterministic) |
| `snapshot_metadata.git_branch` | String | Git branch at snapshot time (deterministic) |
| `summary.total_tasks` | Integer | Total tasks in manifest |
| `summary.done_count` | Integer | Count of DONE tasks |
| `summary.blocked_count` | Integer | Count of BLOCKED tasks |
| `summary.completion_percentage` | Float | `(done_count / total_tasks) * 100` |
| `tasks` | Array | Full task list with state details |
| `tasks[].task_id` | String | Task ID (e.g., "LR-001") |
| `tasks[].task_title` | String | Task title from manifest |
| `tasks[].status` | Enum | "DONE" or "BLOCKED" |
| `tasks[].completion_timestamp` | ISO 8601 UTC | Present if DONE, null if BLOCKED |
| `tasks[].completion_author` | String | Present if DONE, null if BLOCKED |
| `tasks[].blocked_reason_code` | String | Present if BLOCKED, null if DONE |
| `tasks[].blocked_reason_text` | String | Present if BLOCKED, null if DONE |
| `tasks[].blocked_since` | ISO 8601 UTC | Present if BLOCKED, null if DONE |
| `tasks[].blocked_since_epoch` | Integer | Unix epoch seconds (present if BLOCKED, null if DONE) |
| `tasks[].evidence_file` | String | Path to evidence file (always present) |
| `tasks[].evidence_commit` | String | Git SHA of evidence commit (always present) |
| `blocked_details` | Array | Subset of tasks with status=BLOCKED (convenience) |

### 4.3 Output Schema: Markdown Snapshot

**Conceptual Template (Illustrative):**

```markdown
# LR-Task Completion Snapshot

**Git Commit:** a1efea8
**Branch:** main
**Data Source:** docs/live-readiness/

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 4 |
| **Done** | 3 |
| **Blocked** | 1 |
| **Completion** | 75.0% |

---

## Task Status

| Task ID | Title | Status | Details |
|---------|-------|--------|---------|
| LR-001 | P0 Governance CI/CD Shield | ✅ DONE | Completed 2026-01-28 by jannekbuengener |
| LR-002 | P0 Contract Tests | ✅ DONE | Completed 2026-01-30 by jannekbuengener |
| LR-003 | P0 Contract Drift Guard | ✅ DONE | Completed 2026-02-04 by jannekbuengener |
| LR-004 | P0 Deterministic Completion Mechanism | 🔴 BLOCKED | RC_B400 - since 2026-02-05 |

---

## Blocked Tasks (1)

| Task ID | Title | Reason Code | Blocked Since | Reason |
|---------|-------|-------------|---------------|--------|
| LR-004 | P0 Deterministic Completion Mechanism | RC_B400 | 2026-02-05T10:00:00Z | Implementation in progress - awaiting CI integration |
```

---

## 5. Determinism Rules

### 5.1 Strict Determinism Requirement

**LR-005 outputs MUST be clock-independent:**
- No `now()`, `today()`, or dynamic date calculations
- Same inputs (STATE files, Git SHA) → identical outputs
- Reproducible at any point in time (past, present, future)

**Rationale:**
- Historical reconstruction: Generate snapshot for release v1.2.3 years later, get identical result
- Audit trail: Snapshots are deterministic evidence, not time-dependent reports
- CI reproducibility: Same commit → same artifact (no clock variance)

### 5.2 BLOCKED Task Aging Delegation

**Decision: Age calculations are OUT OF SCOPE for LR-005.**

**Provided Fields (Deterministic):**
- `blocked_since` (ISO 8601 UTC timestamp)
- `blocked_since_epoch` (Unix epoch seconds)

**Consumer Responsibility:**
- External tools compute age: `age_days = floor((current_epoch - blocked_since_epoch) / 86400)`
- Dashboards, alerting systems, CI jobs perform aging logic
- LR-005 provides timestamp inputs, not computed ages

**Rationale:**
- Separates concerns: LR-005 = state extraction, consumers = time-based logic
- Maintains determinism: No clock dependency in snapshot
- Flexibility: Different consumers can use different "now" references (report generation time, CI run time, etc.)

### 5.3 Git Metadata

**Deterministic Extraction:**
- `git_commit`: Obtained via `git rev-parse HEAD`
- `git_branch`: Obtained via `git branch --show-current`

**Note:** These reflect repo state at snapshot generation time (deterministic given repo state).

---

## 6. Governance Principles

### 6.1 Observer Role

**LR-005 is a pure observer:**
- Reads STATE files (no writes)
- Generates snapshots (ephemeral, regeneratable)
- No state transitions, no notifications, no actions

**Contrast with LR-004:**
- LR-004 = enforcer (validates, blocks CI)
- LR-005 = reporter (aggregates, exports)

### 6.2 Fail-Safe Validation

**LR-005 depends on LR-004 validation:**
- Assumes inputs are valid (LR-004 already enforced in CI)
- If invalid inputs detected during snapshot generation, report error and exit
- Reference LR-004 validator for repair

---

## 7. Non-Goals

**Explicitly NOT in LR-005 scope:**

1. **State Mutations:** LR-005 does not modify STATE files
2. **Notifications:** No email, Slack, GitHub issue creation
3. **Dashboards:** Tool generates data, not visualizations
4. **SLA Enforcement:** No fail-closed checks on blocked duration
5. **GitHub API Calls:** No commit status updates, no PR comments
6. **Database Persistence:** Snapshots are ephemeral
7. **Real-Time Updates:** Snapshot is point-in-time
8. **Age Calculations:** Delegated to consumers (§5.2)
9. **CI Required Check:** Reporting is optional (informational only)

---

## 8. Acceptance Criteria (Definition-Level)

LR-005 specification is considered **DONE** when:

1. ✅ This specification document is complete and reviewed
2. ✅ Scope clearly defines In/Out boundaries
3. ✅ JSON schema defines mandatory fields with deterministic semantics
4. ✅ Markdown schema template provided for human-readable output
5. ✅ Determinism rules documented (clock-independent, reproducible)
6. ✅ BLOCKED aging delegation decision documented (§5.2)
7. ✅ Observer governance principle established (§6)
8. ✅ Consistent with LR-004 (reads STATE files, no schema conflicts)
9. ✅ Non-goals explicitly documented (§7)

**Note:** Implementation (tool, CI, evidence) is OUT OF SCOPE for this specification.

---

## 9. Open Questions

**Q1: Snapshot artifact lifecycle**
- Should snapshots be committed to repo? (Optional, consumer decision)
- Should snapshots be CI artifacts? (Optional, non-blocking)
- **Decision:** Out of scope for spec; consumers decide retention policy

**Q2: Schema versioning strategy**
- How to handle breaking changes to JSON schema?
- **Decision:** Use `spec_version` field; increment on breaking changes

**Q3: Multi-task-type support**
- Should LR-005 support non-LR tasks (incidents, features)?
- **Decision:** Out of scope for v1.0; future extension point

---

## 10. References

- **LR-004 Spec:** `docs/live-readiness/LR-004-SPEC.md` (state file schema, validation rules)
- **LR-TASKS Manifest:** `docs/live-readiness/LR-TASKS.yaml` (canonical task list)
- **STATE Files:** `docs/live-readiness/LR-*-STATE.yaml` (per-task state)

---

## 11. Schema Versioning and Backward Compatibility

### 11.1 Version Identification
- All JSON snapshots include `spec_version` field (e.g., "1.0")
- Schema file: `docs/live-readiness/LR-005-SCHEMA.json`
- Schema is versioned inline with `spec_version` field

### 11.2 Compatibility Strategy

**Breaking Changes** (require `spec_version` bump, e.g., 1.0 → 2.0):
- Removing required fields
- Changing field types (e.g., string → integer)
- Renaming fields
- Changing enum values
- Tightening validation constraints (e.g., new required fields)

**Non-Breaking Changes** (allow minor additions without version bump):
- Adding optional fields with default values
- Relaxing validation constraints
- Adding new enum values (if backward-compatible)
- Documentation clarifications

### 11.3 Migration Path
When breaking changes are necessary:
1. Increment `spec_version` in schema and reporter
2. Document migration guide in SPEC (this file)
3. Maintain schema files for old versions (LR-005-SCHEMA-v1.0.json, etc.)
4. Reporter tool supports latest version only

### 11.4 Validation
- Integration tests validate examples against schema (see `tests/integration/test_lr005_schema_compliance.py`)
- Schema validation is mandatory for all generated snapshots
- Invalid snapshots trigger exit code 1 (validation error)

---

## 12. Future Extensions (Non-Binding)

**The following are OUT OF SCOPE for LR-005 v1.0 but documented as potential future directions:**

### 12.1 Aging Alert Thresholds (v1.1+)
- Optional flag: Fail if any task blocked > N days
- Use case: Optional CI job for SLA enforcement
- Implementation: Separate tool consuming snapshot JSON

### 12.2 Trend Analysis (v2.0+)
- Compare snapshots over time (completion velocity, blocker resolution time)
- Implementation: Separate tool consuming snapshot history

### 12.3 Multi-Task-Type Support (v2.0+)
- Extend to support incidents, features (not just LR tasks)
- Requires generic task manifest schema

### 12.4 Tool Implementation (Out of Scope for Spec)
- CLI interface, exit codes, output modes
- Developer workflows
- CI integration patterns
- Evidence test cases

**Note:** These extensions are documented for context only. They do not constitute requirements or commitments.

---

**End of Specification v1.0**
