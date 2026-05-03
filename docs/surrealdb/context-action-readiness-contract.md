# Context Intelligence — Agent Action Readiness Contract

**Issue**: [#2021](https://github.com/jannekbuengener/Claire_de_Binare/issues/2021)
**Status**: Proposed contract / pending PR merge
**Date**: 2026-05-04
**Epic**: [#1976](https://github.com/jannekbuengener/Claire_de_Binare/issues/1976)
**Parent**: [#2014](https://github.com/jannekbuengener/Claire_de_Binare/issues/2014)
**Dependencies**: [#2016](https://github.com/jannekbuengener/Claire_de_Binare/issues/2016) (Context Package Model v1 closed), [#2097](https://github.com/jannekbuengener/Claire_de_Binare/issues/2097) (Context Package v0 closed)
**Guardrail**: This document is a contract for [#2098](https://github.com/jannekbuengener/Claire_de_Binare/issues/2098) but does not implement [#2098](https://github.com/jannekbuengener/Claire_de_Binare/issues/2098).

---

## 1. Issue / Scope

This document defines the **Agent Action Readiness** contract for the SurrealDB Context Intelligence System (CIS). It specifies the status model, required inputs, required checks, output contract, agent guidance, stop rules, and Human-GO rules that must be evaluated before any agent begins work in the working repo.

Target issue: [#2021](https://github.com/jannekbuengener/Claire_de_Binare/issues/2021) — "Define agent action readiness checks".

All subsequent CIS tooling, including the Agent Readiness Check v0 ([#2098](https://github.com/jannekbuengener/Claire_de_Binare/issues/2098)) and the Agent OS Readiness Evaluator ([#2191](https://github.com/jannekbuengener/Claire_de_Binare/issues/2191)), shall consume and implement this contract.

---

## 2. Purpose

Provide a bounded, fail-closed readiness contract that answers: **"May the agent begin work on this task, and under what constraints?"**

The contract enforces:
- Agents must not start work blindly.
- Missing context blocks execution.
- Missing evidence blocks execution.
- Scope drift is detected and surfaced as a blocker.
- Human-GO requirements are explicit and non-negotiable.

---

## 3. Non-Goals

- Not a replacement for Human-GO.
- Not a Live-Readiness Go/No-Go.
- Not an Echtgeld-/Live-Capital authorization.
- Not a tool, MCP handler, evaluator, or runtime component.
- Not a merge gate or issue-closure mechanism.
- Not a Board-Stage-to-Live-Go mapping.
- Not a replacement for `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
- Not an implementation of [#2098](https://github.com/jannekbuengener/Claire_de_Binare/issues/2098) or [#2191](https://github.com/jannekbuengener/Claire_de_Binare/issues/2191).

---

## 4. Readiness Status Model

Every agent action readiness assessment MUST produce exactly one of the following status values:

| Status | Meaning |
|---|---|
| `ready_for_read_only` | Agent may read files, search code, and analyze context. No writes of any kind are permitted. |
| `ready_for_dry_run` | Agent may simulate, plan, diff, or generate previews. No write without explicit Human-GO. |
| `ready_for_human_go` | Agent has sufficient context to proceed but MUST stop and request explicit Human-GO before any write. |
| `blocked_missing_context` | Execution blocked. One or more required inputs are missing (Context Package, Required Reads, etc.). |
| `blocked_missing_evidence` | Execution blocked. One or more core assumptions lack committed evidence. |
| `blocked_scope_drift` | Execution blocked. The requested task diverges from the defined scope, or the scope is ambiguous. |

Status derivation must be deterministic: given the same inputs, the same status must be produced.

---

## 5. Required Inputs

The following inputs MUST be present before a readiness assessment can be performed:

| Input | Type | Description |
|---|---|---|
| `task_scope` | `string` | What the agent is asked to do (one concise sentence). |
| `target_issue` | `string \| null` | The GitHub issue driving the task, or `null` for exploratory / non-issue work. |
| `target_paths` | `string[]` | File paths or glob patterns in scope. May be empty if the task is not path-bound. |
| `operation_mode` | `string` | One of: `read_only`, `dry_run`, `write (code/docs)`, `write (config/infra)`, `write (DB/migration)`, `write (MCP live)`. |
| `context_package_ref` | `string \| null` | Reference to an assembled Context Package ([#2016](https://github.com/jannekbuengener/Claire_de_Binare/issues/2016)) or `null` if none was produced. |
| `required_reads` | `string[]` | Canonical files the agent MUST read before acting. Minimum: see [Section 6.3](#6-required-checks). |
| `evidence_refs` | `string[]` | References to evidence sources (issues, run artifacts, logs) that back core assumptions. |
| `impact_refs` | `string[]` | Issues/PRs/paths that would be impacted by the proposed action. Required if `operation_mode` is any form of `write`. |
| `stop_conditions` | `string[]` | Known stop conditions that would abort the task (see [Section 9](#9-stop-rules)). |
| `uncertainties` | `string[]` | Explicitly acknowledged unknowns or assumptions. May be empty, but must be present. |

All inputs must be validated before assessment. Missing or malformed inputs produce `blocked_missing_context`.

---

## 6. Required Checks

### 6.1 Scope Is Defined

- `task_scope` must be a non-empty string.
- If `target_issue` is provided, the issue body must be consistent with `task_scope`.
- If `target_issue` is `null`, the task must be explicitly classified as exploratory.

**Fail**: `blocked_missing_context` with reason "scope not defined".

### 6.2 Context Package Availability

- If the task is issue-driven (`target_issue` is not null), a Context Package ([#2016](https://github.com/jannekbuengener/Claire_de_Binare/issues/2016)) SHOULD be present.
- If no Context Package is available, the agent MUST self-assemble minimum context from `required_reads`.
- Absence of a Context Package is a warning, not a blocker, unless `required_reads` are also absent.

**Fail**: `blocked_missing_context` if both Context Package and `required_reads` are absent.

### 6.3 Required Reads Available

The following reads are the minimum baseline for any CDB agent session:

1. `AGENTS.md` (Root Pointer)
2. `agents/AGENTS.md` (Canonical Agent Registry)
3. `agents/OPEN_CODE_AGENTS.md` (OpenCode Shared Contract)
4. `docs/runbooks/CONTROL_REGISTER.md` (Board Stage & Operating Focus)
5. `CURRENT_STATUS.md` (Repo/Engineering Status Ledger)
6. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` (Live-Readiness SSOT)

Additional `required_reads` may be specified depending on the task domain.

**Fail**: `blocked_missing_context` if any minimum read is unavailable.

### 6.4 Evidence for Core Assumptions

- Every core assumption the agent relies on must be backed by at least one `evidence_ref`.
- Evidence refs must be traceable: GitHub issue number, artifact run ID, committed file path, or source hash.
- "No Evidence, No Trust": unsubstantiated claims must be flagged as unverified.

**Fail**: `blocked_missing_evidence` if any core assumption lacks a traceable evidence ref.

### 6.5 Impact Report (if Code/Docs/Decisions Affected)

Required when `operation_mode` is `write (code/docs)`, `write (config/infra)`, `write (DB/migration)`, or `write (MCP live)`.

An impact report must identify:
- Files that would be created, modified, or deleted.
- Downstream consumers of affected interfaces.
- Risk of contract breakage or invariant violation.

**Fail**: `blocked_missing_context` if impact report is missing for a write operation.

### 6.6 Stop Conditions Known

- At least the mandatory stop conditions from [Section 9](#9-stop-rules) must be known and acknowledged.
- Task-specific stop conditions should be added if applicable.

**Fail**: `blocked_missing_context` if no stop conditions are defined.

### 6.7 Human-GO Requirement Determined

- If `operation_mode` involves any write (`code/docs`, `config/infra`, `DB/migration`, `MCP live`), Human-GO is required.
- If the task touches Trading, Risk, Execution, or Strategy scope, Human-GO is required regardless of `operation_mode`.
- If the task makes LR-/Live-/Echtgeld claims, Human-GO is required.

**Output**: `human_go_required: true/false` in the readiness result.

### 6.8 Uncertainties Explicit

- All known unknowns must be listed in `uncertainties`.
- If an uncertainty relates to governance, LR, or Echtgeld, it is a Stop Condition.

**Fail**: `blocked_scope_drift` if material uncertainties are suppressed.

### 6.9 No Live-/Trading-Derivation

- The readiness assessment must not derive or imply any Live-Readiness, Echtgeld, or Trading authorization.
- Board-Stage (`trade-capable`) and LR-System (`NO-GO`) remain orthogonal and unchanged.

**Fail**: `blocked_scope_drift` if the assessment conflates readiness with authorization.

---

## 7. Output Contract

Every readiness assessment MUST produce the following output structure:

```json
{
  "status": "ready_for_read_only | ready_for_dry_run | ready_for_human_go | blocked_missing_context | blocked_missing_evidence | blocked_scope_drift",
  "reasons": ["string (one per reason)"],
  "required_next_reads": ["string (file paths or issue refs)"],
  "human_go_required": true,
  "stop_conditions": ["string (one per condition)"],
  "missing_context": ["string (absent inputs or reads)"],
  "missing_evidence": ["string (unsubstantiated claims)"],
  "scope_drift_findings": ["string (detected drift vectors)"],
  "uncertainties": ["string (explicit unknowns)"],
  "guardrails": ["string (active constraints for this action)"]
}
```

Field semantics:
- `status`: exactly one of the six readiness status values.
- `reasons`: human-readable explanation of why the status was assigned.
- `required_next_reads`: files or issues the agent must read before taking any action.
- `human_go_required`: `true` if the action requires explicit human approval.
- `stop_conditions`: conditions that would cause the agent to abort.
- `missing_context`: inputs or reads that are absent (empty if none).
- `missing_evidence`: claims that lack traceable evidence (empty if none).
- `scope_drift_findings`: detected divergences from defined scope (empty if none).
- `uncertainties`: explicit unknowns that could affect the outcome.
- `guardrails`: constraints the agent must obey during execution (e.g., "no writes", "no MCP live").

---

## 8. Agent Guidance

### 8.1 `ready_for_read_only`

- **Allowed**: file reads, code search, documentation analysis, issue reading, git log/diff inspection.
- **Forbidden**: any file edit, git commit, PR creation, issue comment, label change, MCP write, DB mutation.
- **Rule**: "Read everything, write nothing."

### 8.2 `ready_for_dry_run`

- **Allowed**: plan generation, diff previews, simulation output, dry-run PR bodies, mock tool invocations.
- **Forbidden**: any write without explicit Human-GO. This includes file writes, commits, pushes, issue updates.
- **Rule**: "Plan and preview, but do not execute."

### 8.3 `ready_for_human_go`

- **Allowed**: nothing until Human-GO is received.
- **Required**: present reasons, missing context, and uncertainties to the human operator.
- **Rule**: "Stop. Request Human-GO. Do not proceed without it."

### 8.4 `blocked_missing_context`

- **Allowed**: none. The agent must not start work.
- **Required**: communicate which inputs or reads are missing.
- **Rule**: "Do not proceed. Resolve missing context first."

### 8.5 `blocked_missing_evidence`

- **Allowed**: none. The agent must not start work.
- **Required**: communicate which claims lack evidence.
- **Rule**: "Do not proceed. Evidence is missing. No Evidence, No Trust."

### 8.6 `blocked_scope_drift`

- **Allowed**: none. The agent must not start work.
- **Required**: communicate the detected drift vectors and the corrective action needed.
- **Rule**: "Do not proceed. Scope is not stable."

### 8.7 General Agent Rules

- No automatic release, merge, close, or label change without Human-GO.
- Board-Stage (`trade-capable`) must never be interpreted as Live-Readiness-Go.
- LR-SSOT is `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`; this contract does not modify it.
- This contract is a prerequisite for [#2098](https://github.com/jannekbuengener/Claire_de_Binare/issues/2098) but does not implement [#2098](https://github.com/jannekbuengener/Claire_de_Binare/issues/2098).

---

## 9. Stop Rules

The following conditions MUST cause the agent to stop immediately, regardless of readiness status:

| # | Stop Condition |
|---|---|
| S1 | `task_scope` is missing, empty, or ambiguous. |
| S2 | Context Package is absent AND `required_reads` are absent or incomplete. |
| S3 | One or more minimum `required_reads` (see [Section 6.3](#63-required-reads-available)) are unavailable. |
| S4 | Core assumptions lack evidence (`evidence_refs` empty or untraceable). |
| S5 | Scope Drift detected: the task diverges from `task_scope` or from the target issue. |
| S6 | `operation_mode` is any write-capable mode (`write (code/docs)`, `write (config/infra)`, `write (DB/migration)`, `write (MCP live)`) without an impact report and Human-GO. |
| S7 | The task touches Trading, Risk, or Execution scope without explicit governance approval. |
| S8 | The task makes or implies Live-Readiness or Echtgeld claims outside of `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`. |
| S9 | A material uncertainty exists in Governance scope (Constitution, Policy, Invariant). |
| S10 | A `STOP` signal is encountered in canonical control surfaces (CONTROL_REGISTER, CURRENT_STATUS, AGENTS.md). |

Agent behavior on Stop:
- Log the stop condition.
- Do NOT proceed with any write.
- Report the stop condition to the human operator.
- Wait for explicit resolution or Human-GO.

---

## 10. Human-GO Rules

Human-GO is **explicit, non-delegable human approval** for a specific action. The following actions always require Human-GO:

| # | Action Requiring Human-GO |
|---|---|
| H1 | Any file write (create, modify, delete). |
| H2 | Any Runtime or DB mutation (start service, apply schema, insert/update data). |
| H3 | Any MCP live write (create issue, update issue, close issue, label change, merge). |
| H4 | Posting an issue comment. |
| H5 | Creating or merging a PR. |
| H6 | Any action touching Trading, Risk, Execution, or Strategy scope. |
| H7 | Cross-agent memory handoff beyond read-only context sharing. |
| H8 | Any claim or statement about Live-Readiness or Echtgeld status. |

Human-GO is scoped: approval for one action does not authorize any other action.

---

## 11. Example Assessments

### 11.1 Read-Only Research

**Inputs:**
- `task_scope`: "Inspect how the execution service handles fill confirmations."
- `target_issue`: null (exploratory)
- `target_paths`: ["services/execution/"]
- `operation_mode`: "read_only"
- `context_package_ref`: null
- `required_reads`: ["AGENTS.md", "agents/AGENTS.md", "agents/OPEN_CODE_AGENTS.md", "docs/runbooks/CONTROL_REGISTER.md", "CURRENT_STATUS.md", "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md"]
- `evidence_refs`: []
- `impact_refs`: []
- `stop_conditions`: ["S1: scope ambiguous", "S3: required reads unavailable"]
- `uncertainties`: ["Execution service contract may be outdated"]

**Output:**
```json
{
  "status": "ready_for_read_only",
  "reasons": ["Read-only scope, no writes required. No substantive conclusions beyond cited source reads; any findings from research still require evidence refs before action."],
  "required_next_reads": ["services/execution/executor.py", "knowledge/contracts/TRACE_CONTRACT_V1.md"],
  "human_go_required": false,
  "stop_conditions": ["S1: scope ambiguous", "S3: required reads unavailable"],
  "missing_context": [],
  "missing_evidence": [],
  "scope_drift_findings": [],
  "uncertainties": ["Execution service contract may be outdated"],
  "guardrails": ["No writes. No issue comments. No PR creation."]
}
```

### 11.2 Dry-Run Patch Plan

**Inputs:**
- `task_scope`: "Plan a fix for the reconnect timeout in the ws service."
- `target_issue`: "#2042"
- `target_paths`: ["services/ws/"]
- `operation_mode`: "dry_run"
- `context_package_ref`: "cp-abc123"
- `required_reads`: ["AGENTS.md", "agents/AGENTS.md", "services/ws/ws_client.py", "infrastructure/compose/compose.blue.yml"]
- `evidence_refs`: ["#2042 (issue body)", "#2040 (evidence)"]
- `impact_refs`: ["services/ws/", "infrastructure/compose/"]
- `stop_conditions`: ["S3: ws_client.py not readable"]
- `uncertainties`: ["Timeout root cause not yet confirmed"]

**Output:**
```json
{
  "status": "ready_for_dry_run",
  "reasons": ["Context Package present, required reads available, dry-run mode permits planning."],
  "required_next_reads": ["services/ws/ws_client.py", "infrastructure/compose/compose.blue.yml"],
  "human_go_required": false,
  "stop_conditions": ["S3: ws_client.py not readable"],
  "missing_context": [],
  "missing_evidence": [],
  "scope_drift_findings": [],
  "uncertainties": ["Timeout root cause not yet confirmed"],
  "guardrails": ["Plan and diff only. No writes without Human-GO."]
}
```

### 11.3 Blocked Missing Context

**Inputs:**
- `task_scope`: "Refactor the risk engine."
- `target_issue`: "#2099"
- `target_paths`: []
- `operation_mode`: "write (code/docs)"
- `context_package_ref`: null
- `required_reads`: []
- `evidence_refs`: []
- `impact_refs`: []
- `stop_conditions`: []
- `uncertainties`: []

**Output:**
```json
{
  "status": "blocked_missing_context",
  "reasons": ["No Context Package. No required reads defined. No impact report. No stop conditions."],
  "required_next_reads": ["AGENTS.md", "agents/AGENTS.md", "docs/runbooks/CONTROL_REGISTER.md"],
  "human_go_required": true,
  "stop_conditions": ["S2: no Context Package and no required reads", "S3: minimum reads missing", "S6: write without impact report"],
  "missing_context": ["required_reads", "impact_refs", "stop_conditions"],
  "missing_evidence": ["No evidence for refactor necessity or scope"],
  "scope_drift_findings": [],
  "uncertainties": ["Scope undefined. Risk engine contract unknown."],
  "guardrails": ["Do not proceed. Resolve missing context first."]
}
```

### 11.4 Blocked Missing Evidence

**Inputs:**
- `task_scope`: "Deploy the new signal pipeline to production."
- `target_issue`: "#2105"
- `target_paths`: ["services/signal/"]
- `operation_mode`: "write (config/infra)"
- `context_package_ref`: "cp-def456"
- `required_reads`: ["AGENTS.md", "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md", "services/signal/pipeline.py"]
- `evidence_refs`: []
- `impact_refs`: ["services/signal/", "services/execution/", "infrastructure/compose/"]
- `stop_conditions`: ["S8: LR claims"]
- `uncertainties`: ["Pipeline test coverage unknown"]

**Output:**
```json
{
  "status": "blocked_missing_evidence",
  "reasons": ["No evidence for pipeline readiness. No test-run artifacts. No soak evidence."],
  "required_next_reads": ["services/signal/pipeline.py", "tests/unit/signal/"],
  "human_go_required": true,
  "stop_conditions": ["S4: core assumptions lack evidence", "S8: LR claims"],
  "missing_context": [],
  "missing_evidence": ["No soak test evidence", "No integration test evidence", "No signal validation report"],
  "scope_drift_findings": [],
  "uncertainties": ["Pipeline test coverage unknown"],
  "guardrails": ["Do not proceed. Evidence is missing."]
}
```

### 11.5 Human-GO Required

**Inputs:**
- `task_scope`: "Fix the decimal precision bug in order quantity calculation."
- `target_issue`: "#1983"
- `target_paths`: ["services/execution/order_handler.py"]
- `operation_mode`: "write (code/docs)"
- `context_package_ref`: "cp-ghi789"
- `required_reads`: ["AGENTS.md", "services/execution/order_handler.py", "tests/unit/execution/test_order_handler.py", "knowledge/contracts/TRACE_CONTRACT_V1.md"]
- `evidence_refs`: ["#1983 (issue with reproduction steps)", "test run artifact run-12345"]
- `impact_refs`: ["services/execution/order_handler.py", "services/risk/", "core/utils/"]
- `stop_conditions`: ["S7: execution scope touched", "S10: STOP in control surfaces"]
- `uncertainties`: ["Decimal rounding edge case under negative quantities"]

**Output:**
```json
{
  "status": "ready_for_human_go",
  "reasons": ["Context sufficient. Plan is ready. Write operation touches execution scope — requires Human-GO."],
  "required_next_reads": [],
  "human_go_required": true,
  "stop_conditions": ["S7: execution scope touched", "S10: STOP in control surfaces"],
  "missing_context": [],
  "missing_evidence": [],
  "scope_drift_findings": [],
  "uncertainties": ["Decimal rounding edge case under negative quantities"],
  "guardrails": ["Stop. Request Human-GO. Do not write until approved."]
}
```

---

## 12. Validation

This contract is validated against the following sources:

| Source | Status | Evidence |
|---|---|---|
| [#2021](https://github.com/jannekbuengener/Claire_de_Binare/issues/2021) | OPEN (target) | Issue body defines readiness checks, status values, required fields. |
| [#2032](https://github.com/jannekbuengener/Claire_de_Binare/issues/2032) | CLOSED | Agent OS Readiness Criteria defined. Used as upstream reference. |
| [#2097](https://github.com/jannekbuengener/Claire_de_Binare/issues/2097) | CLOSED | Context Package v0 implemented. Used as dependency reference. |
| [#2016](https://github.com/jannekbuengener/Claire_de_Binare/issues/2016) | CLOSED | Context Package Model v1 defined. Referenced as input contract. |
| `docs/surrealdb/context-intelligence-system.md` | Canonical | Architecture boundaries, Human-GO and Stop-Condition principles. |
| `docs/surrealdb/context-intelligence-validation.md` | Canonical | Guardrails G1–G10 validated against this contract. |
| `docs/surrealdb/context-package-model-v1.md` | Canonical | Context Package schema, lifecycle. Referenced by required input `context_package_ref`. |
| `docs/runbooks/CONTROL_REGISTER.md` | Canonical | Stage: `trade-capable`, LR: NO-GO. Both confirmed orthogonal to this contract. |
| `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | Canonical | LR SSOT. This contract does not modify it. |
| `CURRENT_STATUS.md` | Ledger | Repo/Engineering status used as minimum read. |

Contract self-consistency check:
- All six readiness status values defined ✓
- All ten required inputs defined ✓
- All nine required checks defined ✓
- Output contract defined with all ten fields ✓
- Agent guidance provided for all six status values ✓
- Ten stop rules defined ✓
- Eight Human-GO rules defined ✓
- Five example assessments provided ✓
- Explicit boundary drawn: Readiness != Authorization ✓
- #2021 remains open until this PR is merged and reconciled. ✓

---

## 13. Residual Uncertainties

| # | Uncertainty | Mitigation |
|---|---|---|
| U1 | This contract is validated against closed evidence, not runtime behavior. | [#2098](https://github.com/jannekbuengener/Claire_de_Binare/issues/2098) will provide the first runtime implementation and reveal gaps. |
| U2 | The interaction between `ready_for_human_go` and the broader Human-GO workflow (issue #1645) is not fully specified. | The broader Human-GO workflow is tracked separately. This contract defers to existing governance. |
| U3 | Memory-handoff semantics for cross-agent sessions (cf. [#2121](https://github.com/jannekbuengener/Claire_de_Binare/issues/2121)) are not yet implemented. | Rule H7 captures the constraint; implementation follows in Wave 14+. |

---

## 14. Boundary: Readiness != Authorization

### What This Contract Does

- Assesses whether an agent has sufficient context to begin work on a specific task.
- Signals missing context, missing evidence, or scope drift.
- Determines whether Human-GO is required for the next step.

### What This Contract Does NOT Do

- **Does not authorize any action.** `ready_for_read_only` is a status, not a permission.
- **Does not replace Live-Readiness.** LR-Go/No-Go remains exclusively in `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
- **Does not imply Echtgeld readiness.** The LR verdict is `NO-GO`; this contract cannot authorize live capital.
- **Does not override Board-Stage.** `trade-capable` is a Board artefact, not a readiness or authorization signal.
- **Does not implement [#2098](https://github.com/jannekbuengener/Claire_de_Binare/issues/2098).** This contract is the specification; [#2098](https://github.com/jannekbuengener/Claire_de_Binare/issues/2098) is the implementation.

### Orthogonality Rule

| System | SSOT | This Contract's Role |
|---|---|---|
| Board Stage | `docs/runbooks/CONTROL_REGISTER.md` | References; does not modify. |
| Repo/Engineering Status | `CURRENT_STATUS.md` | References; does not modify. |
| Live-Readiness | `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | References; does not modify. |
| Action Readiness | This document (`docs/surrealdb/context-action-readiness-contract.md`) | Proposed SSOT for agent action readiness after PR merge and #2021 close. |

---

## Provenance / Quellen

- **Target Issue**: [#2021](https://github.com/jannekbuengener/Claire_de_Binare/issues/2021)
- **Epic**: [#1976](https://github.com/jannekbuengener/Claire_de_Binare/issues/1976)
- **Parent**: [#2014](https://github.com/jannekbuengener/Claire_de_Binare/issues/2014)
- **Evidence (closed)**: [#2032](https://github.com/jannekbuengener/Claire_de_Binare/issues/2032), [#2097](https://github.com/jannekbuengener/Claire_de_Binare/issues/2097), [#2016](https://github.com/jannekbuengener/Claire_de_Binare/issues/2016)
- **Dependent (not implemented here)**: [#2098](https://github.com/jannekbuengener/Claire_de_Binare/issues/2098), [#2191](https://github.com/jannekbuengener/Claire_de_Binare/issues/2191)
- **Docs**: `docs/surrealdb/context-intelligence-system.md`, `docs/surrealdb/context-intelligence-validation.md`, `docs/surrealdb/context-intelligence-roadmap.md`, `docs/surrealdb/context-package-model-v1.md`
