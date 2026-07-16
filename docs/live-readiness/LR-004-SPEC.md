# LR-004 Specification: Deterministic Completion Mechanism

**Version:** 1.0
**Status:** Active
**Date:** 2026-02-05
**Author:** CDB Repo Agent

---

## 1. Purpose

Establish a **fail-closed, deterministic completion tracking system** for Live Readiness (LR) tasks that:
- Eliminates dependency on external GitHub state (UI/API/CLI inconsistencies)
- Provides canonical, versioned state files (Git-native audit trail)
- Enforces binary terminal states (DONE/BLOCKED) with no ambiguity
- Validates state integrity via CI with fail-closed enforcement
- Enables reproducible project state from Git history alone

---

## 2. Scope

**In Scope:**
- LR-Tasks (LR-001, LR-002, LR-003, ...)
- Task manifest (canonical list of which LR tasks exist)
- State file schema definition (YAML v1.0)
- Validation rules (V000-V013)
- Reason code taxonomy for BLOCKED states
- CI enforcement mechanism

**Out of Scope (Future Extensions):**
- Generic task types (incidents, features) - see §11 Extension Points
- State transition automation (manual state setting only)
- GitHub API integration (intentionally excluded for determinism)
- Real-time dashboard generation (use `--report` mode instead)

---

## 3. Task Manifest

### 3.1 Purpose

The **task manifest** is the single source of truth for which LR tasks exist. Without this manifest, the validator cannot deterministically detect missing STATE files (it would only find existing files via glob, not missing ones).

### 3.2 Manifest File Location

```
docs/live-readiness/LR-TASKS.yaml
```

### 3.3 Manifest Schema

```yaml
# LR-TASKS.yaml
spec_version: "1.0"
tasks:
  - task_id: "LR-001"
    task_title: "P0 Governance CI/CD Shield"

  - task_id: "LR-002"
    task_title: "P0 Contract Tests"

  - task_id: "LR-003"
    task_title: "P0 Contract Drift Guard"

  - task_id: "LR-004"
    task_title: "P0 Deterministic Completion Mechanism"

  # Future tasks appended here
```

### 3.4 Manifest Rules

**Immutability:**
- `task_id` is **immutable** once added (never changed, never removed)
- `task_title` may be updated (e.g., better naming) but only with STATE file update and explanatory commit
- Tasks marked DONE remain in manifest (permanent historical record)

**Append-Only:**
- New tasks are added to the end of the list
- Existing tasks are never deleted (historical record)
- Ordering: Tasks listed in `task_id` ascending order (LR-001, LR-002, ...)

**Schema:**
- Each entry has exactly 2 fields: `task_id`, `task_title`
- No duplicate `task_id` values

**Validator Behavior:**
- Validator reads `LR-TASKS.yaml` to enumerate required tasks
- For each task in manifest, validator expects exactly one `LR-<NNN>-STATE.yaml` file
- STATE files not in manifest → FAIL (orphan)
- Tasks in manifest without STATE → FAIL (missing)
- Duplicate STATE files for same task_id → FAIL (duplicate)

---

## 4. State File Schema (v1.0)

### 4.1 File Naming Convention

```
docs/live-readiness/LR-<NNN>-STATE.yaml
```

Where `<NNN>` is a zero-padded 3-digit task ID (e.g., `LR-001`, `LR-042`, `LR-123`)

### 4.2 Schema Definition (DONE State)

```yaml
spec_version: "1.0"
task_id: "LR-001"
task_title: "P0 Governance CI/CD Shield"
status: "DONE"
completion_timestamp: "2026-01-28T14:32:00Z"
completion_author: "jannekbuengener"
evidence_file: "docs/live-readiness/LR-001-EVIDENCE.md"
evidence_commit: "928d33f"

# BLOCKED-specific fields (must be null when DONE)
blocked_reason_code: null
blocked_reason_text: null
blocked_since: null
```

### 4.3 Schema Definition (BLOCKED State)

```yaml
spec_version: "1.0"
task_id: "LR-005"
task_title: "Shadow Mode Metrics Dashboard"
status: "BLOCKED"
completion_timestamp: null
completion_author: null
evidence_file: "docs/live-readiness/LR-005-EVIDENCE.md"
evidence_commit: "a1efea8"

# BLOCKED-specific fields (mandatory when BLOCKED)
blocked_reason_code: "RC_B003"
blocked_reason_text: "Grafana Cloud API quota exhausted; requires upgraded plan (ticket: PROC-1234)"
blocked_since: "2026-02-03T09:00:00Z"
```

### 4.4 Field Specifications

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `spec_version` | String | Yes | Must equal "1.0" |
| `task_id` | String | Yes | Must match filename pattern `LR-<NNN>` and exist in manifest |
| `task_title` | String | Yes | Must match manifest entry, non-empty, max 200 chars |
| `status` | Enum | Yes | Exactly `DONE` or `BLOCKED` (case-sensitive) |
| `completion_timestamp` | ISO 8601 UTC | Conditional | Required if DONE, null if BLOCKED, must end in 'Z' |
| `completion_author` | String | Conditional | Required if DONE, null if BLOCKED |
| `evidence_file` | String | Yes | Relative path, file must exist |
| `evidence_commit` | String | Yes | 7-40 chars, hexadecimal (format only, no Git SHA validation) |
| `blocked_reason_code` | Enum | Conditional | Required if BLOCKED, null if DONE, must be in taxonomy (§5) |
| `blocked_reason_text` | String | Conditional | Required if BLOCKED, null if DONE, non-empty |
| `blocked_since` | ISO 8601 UTC | Conditional | Required if BLOCKED, null if DONE, must end in 'Z' |

**Conditional Requirements:**
- **DONE State:** MUST have `completion_timestamp`, `completion_author`; MUST NOT have `blocked_*` fields (must be null)
- **BLOCKED State:** MUST have `blocked_reason_code`, `blocked_reason_text`, `blocked_since`; MUST NOT have `completion_timestamp`, `completion_author` (must be null)

**Audit Trail:**
- Git commit history provides full audit trail (who, when, why)
- Use `git log`, `git blame`, `git diff` to trace state changes
- No embedded history in STATE files (Git is single source of truth)

---

## 5. Reason Code Taxonomy (BLOCKED States)

### 5.1 Reason Code Format

Format: `RC_B<CCC>` where `<CCC>` is a 3-digit category-based number.

### 5.2 Taxonomy Table

| Code | Category | Description | Example Use Case |
|------|----------|-------------|------------------|
| **RC_B001** | Dependency | Upstream LR-Task not completed (hard dependency) | LR-005 blocked until LR-003 DONE |
| **RC_B002** | Dependency | External system dependency unavailable | Database cluster down, blocks deployment |
| **RC_B003** | Dependency | Third-party API/service unavailable or quota exceeded | Grafana API quota exhausted |
| **RC_B100** | Resource | Budget/funding approval required | Infrastructure spend needs CFO approval |
| **RC_B101** | Resource | Infrastructure resource unavailable (compute, storage) | No available GPU instances for ML task |
| **RC_B102** | Resource | Personnel resource unavailable (specialized expertise) | Security audit requires external auditor |
| **RC_B200** | Technical | Critical bug blocking implementation | P0 bug makes feature impossible to implement |
| **RC_B201** | Technical | Technology limitation (not fixable in current scope) | Browser API not supported on target platform |
| **RC_B202** | Technical | Security/compliance blocker (requires audit/approval) | PII handling needs security review |
| **RC_B300** | Organizational | Awaiting stakeholder decision/approval | Architecture decision pending CTO review |
| **RC_B301** | Organizational | Organizational policy change required | New policy must be approved before proceeding |
| **RC_B302** | Organizational | Cross-team coordination blocker | Dependent team has conflicting roadmap |
| **RC_B400** | Scope | Requirements clarification needed | Acceptance criteria ambiguous, needs refinement |
| **RC_B401** | Scope | Scope change invalidated current approach | Requirements changed mid-implementation |
| **RC_B402** | Scope | Acceptance criteria unachievable under current constraints | Performance target impossible with current infra |

### 5.3 Category Ranges (Future Expansion)

- **RC_B001-099:** Dependency blockers
- **RC_B100-199:** Resource blockers
- **RC_B200-299:** Technical blockers
- **RC_B300-399:** Organizational blockers
- **RC_B400-499:** Scope blockers
- **RC_B500-999:** Reserved for future categories

### 5.4 Reason Code Selection Guidelines

1. **Choose Most Specific Code:** If multiple codes apply, select the most specific root cause
2. **Use blocked_reason_text for Context:** Supplement with ticket numbers, references, ETA
3. **Document Resolution Criteria:** Include what needs to happen to unblock (e.g., "ticket PROC-1234 approved")
4. **Track in Git Commit Messages:** When transitioning states, explain why in commit message

---

## 6. Validation Rules (V000-V013)

### 6.1 Manifest Validation Rules

**Rule V000: Manifest Existence**
- **Check:** File `docs/live-readiness/LR-TASKS.yaml` exists
- **Fail:** File not found
- **Error:** "Task manifest not found: docs/live-readiness/LR-TASKS.yaml"

**Rule V001: Manifest Schema Valid**
- **Check:** Manifest has `spec_version: "1.0"` and `tasks` array
- **Fail:** Missing fields, invalid structure
- **Error:** "Manifest schema invalid (missing spec_version or tasks array)"

**Rule V002: No Duplicate Task IDs in Manifest**
- **Check:** All `task_id` values in manifest are unique
- **Fail:** Duplicate task_id found
- **Error:** "Duplicate task_id in manifest: {task_id}"

### 6.2 State File Validation Rules

**Rule V003: STATE File Exists for Each Manifest Entry**
- **Check:** For each task in manifest, file `docs/live-readiness/{task_id}-STATE.yaml` exists
- **Fail:** STATE file missing for manifest task
- **Error:** "Missing STATE file for task {task_id} (expected: docs/live-readiness/{task_id}-STATE.yaml)"

**Rule V004: No Orphan STATE Files**
- **Check:** Every STATE file found corresponds to a task in manifest
- **Fail:** STATE file exists but task not in manifest
- **Error:** "Orphan STATE file: {filename} (task {task_id} not in manifest)"

**Rule V005: No Duplicate STATE Files for Same Task**
- **Check:** Exactly one STATE file per task_id
- **Fail:** Multiple STATE files map to same task_id
- **Error:** "Duplicate STATE files for task {task_id}: {file1}, {file2}"

**Rule V006: Schema Version Match**
- **Check:** STATE file `spec_version == "1.0"`
- **Fail:** Version mismatch, missing field, or non-string type
- **Error:** "Schema version must be exactly '1.0' (found: {actual})"

**Rule V007: Task ID Consistency**
- **Check:** Filename `LR-XXX-STATE.yaml` matches `task_id: "LR-XXX"` and manifest entry
- **Fail:** Mismatch between filename, content, or manifest
- **Error:** "Task ID mismatch (filename: {filename}, content: {task_id})"

**Rule V008: Task Title Consistency**
- **Check:** STATE file `task_title` matches manifest entry for same `task_id`
- **Fail:** Title mismatch
- **Error:** "Task title mismatch (STATE: {state_title}, manifest: {manifest_title})"

**Rule V009: Status Enum Validity**
- **Check:** `status in ["DONE", "BLOCKED"]` (case-sensitive)
- **Fail:** Invalid value, missing field, or non-string type
- **Error:** "Status must be 'DONE' or 'BLOCKED' (found: {actual})"

**Rule V010: DONE State Completeness**
- **Check (DONE):**
  - `completion_timestamp` is non-null ISO 8601 UTC string
  - `completion_author` is non-null, non-empty string
  - `blocked_reason_code`, `blocked_reason_text`, `blocked_since` are all null
- **Fail:** Missing required fields or unexpected fields present
- **Error:** "DONE state missing required field: {field}" or "DONE state has unexpected {field} (must be null)"

**Rule V011: BLOCKED State Completeness**
- **Check (BLOCKED):**
  - `blocked_reason_code` is non-null, valid taxonomy code
  - `blocked_reason_text` is non-null, non-empty string
  - `blocked_since` is non-null ISO 8601 UTC string
  - `completion_timestamp`, `completion_author` are both null
- **Fail:** Missing required fields or unexpected fields present
- **Error:** "BLOCKED state missing required field: {field}" or "BLOCKED state has unexpected {field} (must be null)"

**Rule V012: Timestamp Format Validation**
- **Check:** All timestamp fields match ISO 8601 UTC format: `YYYY-MM-DDTHH:MM:SSZ`
- **Fail:** Invalid format, missing 'Z' suffix, local timezone offset present
- **Error:** "Invalid timestamp format for {field}: {value} (expected ISO 8601 UTC ending in 'Z')"

**Rule V013: Reason Code Taxonomy Validity**
- **Check:** If BLOCKED, `blocked_reason_code` must be in taxonomy (§5.2)
- **Fail:** Unknown reason code
- **Error:** "Invalid blocked_reason_code: {code} (not in taxonomy; see LR-004-SPEC.md §5.2)"

**Rule V014: Evidence File Existence**
- **Check:** File at `evidence_file` path exists relative to repo root
- **Fail:** File not found
- **Error:** "Evidence file not found: {evidence_file}"

**Rule V015: Evidence Commit Format**
- **Check:** `evidence_commit` is 7-40 chars, all hexadecimal
- **Fail:** Invalid format (non-hex chars, wrong length)
- **Error:** "Invalid evidence_commit format: {value} (expected 7-40 hex chars)"
- **Note:** Does not validate Git SHA existence (no Git calls)

### 6.3 Validation Algorithm

```
1. Load and validate manifest (Rules V000-V002):
   - Parse LR-TASKS.yaml
   - Check schema version
   - Check for duplicate task_ids
   - Build task registry (task_id → task_title)

2. Scan for STATE files:
   - Glob docs/live-readiness/LR-*-STATE.yaml
   - Build STATE file registry (task_id → filepath)
   - Detect duplicate STATE files for same task_id (Rule V005)

3. Cross-validate manifest ↔ STATE files (Rules V003-V005):
   - For each manifest task: STATE file must exist
   - For each STATE file: task must be in manifest
   - No duplicate STATE files for same task_id

4. Validate each STATE file (Rules V006-V015):
   - Parse YAML
   - Run V006-V015 for this file
   - Collect all violations

5. Report results:
   - If any violations: report all, exit 1 (fail-closed)
   - If no violations: exit 0
   - If BLOCKED tasks exist: report them but do not fail
```

### 6.4 Error Reporting Format

```
[LR-004] VALIDATION FAILURES (N):
  ✗ {task_id}: Rule {rule_id} violation - {error_message}
  ✗ {task_id}: Rule {rule_id} violation - {error_message}
  ...

[LR-004] ❌ FAIL: Validation failed (fail-closed)
```

---

## 7. State Transition Rules

### 7.1 Adding New LR Task

**Steps:**
1. **Update Manifest:** Add new task entry to `LR-TASKS.yaml` (append to end)
2. **Create STATE File:** Copy template to `LR-NNN-STATE.yaml`
3. **Set Initial State:** Usually `status: "BLOCKED"` with `RC_B400` (requirements clarification)
4. **Validate:** Run `lr004_completion_guard.py --check`
5. **Commit:** Commit both manifest and STATE file together

**Example Commit:**
```bash
git add docs/live-readiness/LR-TASKS.yaml \
        docs/live-readiness/LR-NNN-STATE.yaml
git commit -m "lr-004: add new task LR-NNN (title)

- Added to manifest
- Initial state: BLOCKED (RC_B400 - requirements TBD)"
git push
```

### 7.2 Transition: BLOCKED → DONE

**Prerequisites:**
- Blocker resolved (documented in commit message)
- Evidence file complete (`LR-NNN-EVIDENCE.md`)
- All pass criteria met

**Steps:**
1. Update `status: "DONE"`
2. Set `completion_timestamp` (ISO 8601 UTC)
3. Set `completion_author` (Git user.name)
4. Set `blocked_reason_code`, `blocked_reason_text`, `blocked_since` to null
5. Validate locally (`lr004_completion_guard.py --check`)
6. Commit with message explaining completion
7. Push

### 7.3 Transition: DONE → BLOCKED (Regression)

**Use Case:** Discovered issue invalidates completion (rare)

**Steps:**
1. Update `status: "BLOCKED"`
2. Set `blocked_reason_code` (e.g., `RC_B200` for critical bug)
3. Set `blocked_reason_text` with details
4. Set `blocked_since` to current UTC timestamp
5. Set `completion_timestamp`, `completion_author` to null
6. Commit with message explaining regression and root cause
7. Validate and push

**Warning:** Regressions are exceptional; should trigger root cause analysis.

### 7.4 Forbidden Transitions

- **No Intermediate States:** Cannot set status to anything other than DONE or BLOCKED
- **No Partial Updates:** All required fields for target state must be set atomically
- **Audit via Git:** All changes tracked in Git history (use meaningful commit messages)
- **Never Remove from Manifest:** Completed tasks stay in manifest (permanent historical record)

---

## 8. Validator Tool Specification

### 8.1 Tool Name and Location

**Name:** `lr004_completion_guard.py`
**Location:** `scripts/lr004_completion_guard.py`
**Language:** Python 3.11+
**Dependencies:** `pyyaml` (stdlib for pathlib, datetime, argparse, re)

### 8.2 CLI Interface

```bash
# Check mode (CI enforcement)
python scripts/lr004_completion_guard.py --check
# Exit 0: All tasks in manifest have valid STATE files
# Exit 1: Validation failed (fail-closed)
# Exit 2: Configuration error (missing manifest, invalid args)

# Check specific task
python scripts/lr004_completion_guard.py --check --task-id LR-001

# Report mode (human-readable summary)
python scripts/lr004_completion_guard.py --report
# Output: Markdown table of all LR tasks with status
```

### 8.3 Exit Codes

| Code | Meaning | Use Case |
|------|---------|----------|
| 0 | Success | All state files valid (DONE or BLOCKED) |
| 1 | Validation Failure | Invalid/missing state, schema violation (CI blocks merge) |
| 2 | Configuration Error | Missing manifest/dependencies, invalid args, tool error |

### 8.4 Output Format (--check mode)

```
[LR-004] Completion Guard: Validating LR-Task States...
[LR-004] Loading manifest: docs/live-readiness/LR-TASKS.yaml
[LR-004] Found 4 tasks in manifest

[OK] LR-001: DONE (completed 2026-01-28)
[OK] LR-002: DONE (completed 2026-01-30)
[OK] LR-003: DONE (completed 2026-02-04)
[BLOCKED] LR-004: RC_B400 - Implementation in progress

[LR-004] Summary:
  Total Tasks: 4
  DONE: 3
  BLOCKED: 1
  Missing: 0
  Orphaned: 0

[LR-004] ✓ PASS: All LR-Task states valid
```

---

## 9. CI Integration Requirements

### 9.1 Workflow Job Specification

**Job Name:** `lr-004-completion-guard`
**Trigger:** All PRs to main/develop, all pushes to main/develop
**Runner:** `ubuntu-latest`
**Dependencies:** Run after `lr-003-contract-drift-guard` (ensures contract stability first)

### 9.2 Required Steps

1. **Checkout:** Standard checkout (shallow clone acceptable)
2. **Python Setup:** Python 3.11
3. **Dependencies:** `pip install pyyaml`
4. **Validation:** `python scripts/lr004_completion_guard.py --check`
5. **Failure Artifact Upload:** Upload state files + manifest on failure (for debugging)

### 9.3 Failure Handling

- **continue-on-error: false** (fail-closed, blocks merge)
- **Error Message:** Display actionable guidance (how to fix)
- **Artifact Upload:** Manifest + STATE files + Evidence files for post-mortem

### 9.4 Build Summary Integration

Add to `build-summary` job:
- Include `lr-004-completion-guard` in `needs` array
- Display status: `✅ All LR-Task states valid` or `❌ Validation failed`
- Link to validation failure report (if failed)

---

## 10. Developer Workflows

### 10.1 Workflow: Add New LR Task

```bash
# 1. Update manifest
vim docs/live-readiness/LR-TASKS.yaml
# Add:
#   - task_id: "LR-NNN"
#     task_title: "Task Title Here"

# 2. Create STATE file from template
cp docs/live-readiness/LR-STATE-TEMPLATE.yaml \
   docs/live-readiness/LR-NNN-STATE.yaml

# 3. Edit STATE (set task_id, task_title, status=BLOCKED, RC_B400)
vim docs/live-readiness/LR-NNN-STATE.yaml

# 4. Validate
python scripts/lr004_completion_guard.py --check --task-id LR-NNN

# 5. Commit both files
git add docs/live-readiness/LR-TASKS.yaml \
        docs/live-readiness/LR-NNN-STATE.yaml
git commit -m "lr-004: add task LR-NNN (title)

- Added to manifest
- Initial state: BLOCKED (RC_B400)"
git push
```

### 10.2 Workflow: Mark Task DONE

```bash
# Prerequisites:
# - Evidence file complete (LR-NNN-EVIDENCE.md)
# - All pass criteria met
# - No blockers remaining

# 1. Get current timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
AUTHOR=$(git config user.name)
COMMIT=$(git rev-parse --short HEAD)

# 2. Edit STATE file
vim docs/live-readiness/LR-NNN-STATE.yaml
# Set: status=DONE, completion_timestamp, completion_author
# Set: blocked_* fields to null

# 3. Validate locally
python scripts/lr004_completion_guard.py --check --task-id LR-NNN

# 4. Commit and push
git add docs/live-readiness/LR-NNN-STATE.yaml
git commit -m "lr-004: mark LR-NNN as DONE

- All pass criteria met
- Evidence file complete"
git push
```

### 10.3 Workflow: Mark Task BLOCKED

```bash
# 1. Edit STATE file
vim docs/live-readiness/LR-NNN-STATE.yaml
# Set: status=BLOCKED
# Set: blocked_reason_code (e.g., RC_B003)
# Set: blocked_reason_text (include ticket/context)
# Set: blocked_since (ISO 8601 UTC)
# Set: completion_* fields to null

# 2. Validate
python scripts/lr004_completion_guard.py --check --task-id LR-NNN

# 3. Commit
git add docs/live-readiness/LR-NNN-STATE.yaml
git commit -m "lr-004: mark LR-NNN as BLOCKED (RC_B003)

- Blocker: [explanation]
- Resolution: [what needs to happen]"
git push
```

---

## 11. Extension Points (Future Enhancements)

### 11.1 Generic Task Types (v2.0)

**Current:** LR-Task specific (`LR-*-STATE.yaml`)

**Future:** Generic task state system supporting multiple task types:

```yaml
# Generic manifest: docs/tasks/TASKS.yaml
spec_version: "2.0"
task_types:
  - type: "lr"
    manifest: "docs/live-readiness/LR-TASKS.yaml"
  - type: "incident"
    manifest: "docs/incidents/INC-TASKS.yaml"
  - type: "feature"
    manifest: "docs/features/FEAT-TASKS.yaml"
```

### 11.2 Validation Metadata (v1.1+)

**Future:** Optionally track when/how validation occurred:

```yaml
# Future extension (not part of v1.0):
validation_metadata:
  last_validated_at: "2026-02-05T10:15:00Z"
  last_validated_by: "lr004_completion_guard.py"
  validation_result: "PASS"
```

### 11.3 Schema Hash (v1.1+)

**Future:** Optionally include tamper-detection hash:

```yaml
# Future extension (not part of v1.0):
schema_hash: "sha256:a3f2b1c9d4e5..."  # Computed by validator
```

### 11.4 Automated State Updates (Future)

```bash
# Initialize new task (creates STATE file + updates manifest)
python scripts/lr004_completion_guard.py --init LR-042 "Task Title"

# Mark task DONE (auto-populates timestamps, author)
python scripts/lr004_completion_guard.py --mark-done LR-042
```

---

## 12. Security Considerations

### 12.1 Threat Model

**Threats:**
1. **Malicious State Modification:** Attacker modifies STATE file to falsely mark task DONE
2. **Manifest Tampering:** Attacker removes task from manifest to hide incomplete work
3. **Evidence Tampering:** Attacker modifies evidence file to match false DONE state

**Mitigations:**
1. **Git Audit Trail:** All changes visible in Git history, blame, PR review
2. **CI Enforcement:** Invalid states block merge (fail-closed)
3. **Manifest Integrity:** Append-only (task_id immutable), no deletions
4. **Evidence File Validation:** Validator checks file existence (Rule V014)

### 12.2 Access Control

**Assumption:** Trust Git commit access control
- Only authorized developers can push to main/develop
- PR reviews required before merge (GitHub branch protection)
- CI validates all changes before merge

---

## 13. Performance Requirements

### 13.1 Validation Speed

**Target:** < 5 seconds total CI runtime for validation job

**Breakdown:**
- Checkout: ~1s
- Python setup: ~1s
- Dependencies install: ~1s
- Validation: < 2s (for up to 50 LR tasks)

**Scalability:** O(N) where N = number of tasks in manifest

---

## 14. Acceptance Criteria

LR-004 is considered **DONE** when:

1. ✅ This specification document (`LR-004-SPEC.md`) is complete and reviewed
2. ✅ Task manifest (`LR-TASKS.yaml`) created with LR-001 through LR-004
3. ✅ Validator script (`lr004_completion_guard.py`) implements all rules (V000-V015)
4. ✅ CI job (`lr-004-completion-guard`) runs on all PRs and blocks invalid states
5. ✅ Evidence file (`LR-004-EVIDENCE.md`) demonstrates 5 test cases
6. ✅ Template file (`LR-STATE-TEMPLATE.yaml`) available for developers
7. ✅ At least 3 existing LR tasks have valid STATE files (LR-001, LR-002, LR-003)
8. ✅ CI passes with all LR-004 checks green
9. ✅ Developer workflows documented (§10)

---

## 15. References

- **LR-003 Evidence:** `docs/live-readiness/LR-003-EVIDENCE.md` (pattern reference)
- **LR-003 Fingerprint:** `docs/live-readiness/LR-003-FINGERPRINT.json` (precedent for Git-native state)
- **CI Workflow:** `.github/workflows/ci.yml` (integration point)
- **Project Status:** `PROJECT_STATUS.md` (context for LR tasks)
- **Governance:** `knowledge/governance/CDB_GOVERNANCE.md` (authority hierarchy)

---

**End of Specification v1.0**
