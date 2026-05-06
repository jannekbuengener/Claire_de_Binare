# Stale Knowledge Detection Runbook

**Status**: Operational  
**Authority**: Issue #2160 / Wave-16 / Epic #1976  
**Parent**: #2153

This runbook describes how operators and agents use the Stale Knowledge Detection
and Refresh Planning system (Wave-16) to scan, read, interpret, and act on stale
knowledge findings.

**LR-Status: NO-GO** — this runbook covers read-only detection tooling only.
No live capital, no Echtgeld-Go, no trading implication.

---

## 1. Purpose and Scope

The Stale Knowledge Detection system detects knowledge artifacts that have become
outdated, deleted, superseded, expired, or no longer observed. Detected findings
cover:

- Sources whose file hash has changed since last verification (`source_hash_changed`)
- Sources that have been deleted or no longer exist (`source_deleted`)
- Decision records that have been superseded by a newer decision (`decision_superseded`)
- Evidence records whose TTL/expiry timestamp has passed (`evidence_expired`)
- Memory records whose TTL has elapsed (`memory_ttl_expired`)
- Dependency edges that are no longer observed in the current run (`dependency_edge_no_longer_observed`)
- Context packages that are outdated (stale snapshot or freshness window exceeded) (`stale_context_package`)
- Briefing artifacts built from a stale snapshot or beyond their freshness window (`stale_briefing`)

**Detection is signal, not action authority.** No finding authorises any automated
action, write, deployment, trade, or live-go.

---

## 2. Non-Goals

The following are explicitly out of scope for this system:

- **No automatic delete** — no artifact is automatically removed based on a finding.
- **No automatic refresh write** — no DB or filesystem write is triggered automatically.
- **No DB write** — no SurrealDB or Postgres write from any of these tools.
- **No GitHub write** — no issue comment, label, close, or PR opened by the tools.
- **No Live-Readiness-Go** — stale findings do not change the LR verdict. The
  current verdict remains **NO-GO**.
- **No Echtgeld-Go** — stale findings do not authorise real capital operations.
- **No runtime adaptation** — the scan service does not feed into any live trading
  path or risk service.
- **No CI gate on its own** — `--fail-on-blocking` is available for operator-controlled
  CI integration but is not automatically enforced in any active workflow.

---

## 3. Tool Overview

### 3.1 Scan Service — `scan_stale_knowledge_v1`

- **Module**: `tools/surrealdb/stale_knowledge_scan.py`
- **Schema version**: `stale-knowledge-scan/v1`
- **API**: `scan_stale_knowledge_v1(bundle, as_of=None) → StaleKnowledgeScanResult`
- **Read-only**. No DB access. No network. No file output. No writes.
- **Deterministic**: SHA256-based `stale_id` generation, clock via
  `core.utils.clock.utcnow` (no wall-clock calls).
- **Input**: a `Mapping[str, Any]` bundle with domain record lists (see Section 4).
- **Output**: `StaleKnowledgeScanResult` containing `findings`, `blocking_count`,
  `severity_summary`, `recommended_refresh`, and `guardrails`.

### 3.2 CLI — `stale_context_cli.py`

- **Module**: `tools/surrealdb/stale_context_cli.py`
- **Invocation**: `python -m tools.surrealdb.stale_context_cli`

Three subcommands:

| Command | Purpose |
|---------|---------|
| `scan-stale-context` | Scan input bundle, output all stale-knowledge findings |
| `show-stale-context` | Show a single finding by `stale_id` |
| `report-stale-context` | Generate a structured summary report |

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | Success (no blocking findings, or `--fail-on-blocking` not set) |
| `1` | Blocking findings present and `--fail-on-blocking` flag was set |
| `2` | CLI or input/validation error |
| `3` | `show-stale-context`: `stale_id` not found in bundle |

Output formats: `--format json` (default) or `--format markdown`.

### 3.3 MCP Tool — `cdb_context_stale`

- **Handler**: `tools/mcp/stale_context_tools.py`
- **Tool name**: `cdb_context_stale`
- **Schema version**: `stale-context-mcp/v1`
- **Bundle-driven**: a `bundle` object must be supplied in the request — the tool
  never reads from a database, filesystem, or network.
- **Read-only**. No DB. No network. No GitHub calls.

Supported scope values for the `scope` parameter:

| Scope | Stale types included |
|-------|----------------------|
| `all` (default) | all 8 types |
| `artifact` | `source_hash_changed`, `source_deleted` |
| `decision` | `decision_superseded` |
| `evidence` | `evidence_expired` |
| `memory` | `memory_ttl_expired` |
| `edge` | `dependency_edge_no_longer_observed` |
| `package` | `stale_context_package` |
| `briefing` | `stale_briefing` |

Additional filters: `target_ref`, `stale_type`, `severity`.  
Limit: default `100`, maximum `500` (requests above cap are silently truncated).

### 3.4 Refresh Plan — `generate_refresh_plan_v1`

- **Module**: `tools/surrealdb/stale_refresh_plan.py`
- **Schema version**: `stale-refresh-plan/v1`
- **API**: `generate_refresh_plan_v1(scan_input, as_of=None) → RefreshPlanResult`
- **Input**: accepts a `StaleKnowledgeScanResult`, a serialised scan result dict,
  or a raw bundle (scan is run internally in that case).
- **Output**: `RefreshPlanResult` with prioritised `plan_items`, `priority_summary`,
  `action_summary`, `guardrails`, and `errors`.
- **Recommendation only** — `write_authorized` is always `False` on every plan item.
  The plan does not grant permission to act.

---

## 4. Input Bundles

### 4.1 `sample_bundle.json`

**Location**: `tests/fixtures/surrealdb/stale_knowledge_scan/sample_bundle.json`

A minimal deterministic fixture that triggers three stale types:

- `source_hash_changed` — source `src-hash-changed-001` has a current hash
  different from its last verified hash.
- `source_deleted` — source `src-deleted-001` has `exists: false` and a
  `deleted_at` timestamp.
- `evidence_expired` — evidence `ev-expired-001` has an `expires_at` before
  the bundle's `meta.as_of` (`2026-05-06T00:00:00+00:00`).

Use this bundle for quick smoke tests covering the three most common stale
types. No secrets, no real data, no absolute host paths.

### 4.2 `all_types_bundle.json`

**Location**: `tests/fixtures/surrealdb/stale_knowledge_scan/all_types_bundle.json`

A comprehensive deterministic fixture that triggers all 8 stale types — exactly
one finding per type:

| Domain key | Fixture ID | Stale type triggered |
|------------|------------|----------------------|
| `sources` | `fixture-src-hash-001` | `source_hash_changed` |
| `sources` | `fixture-src-deleted-001` | `source_deleted` |
| `decisions` | `fixture-dec-superseded-001` | `decision_superseded` |
| `evidence_records` | `fixture-ev-expired-001` | `evidence_expired` |
| `memory_records` | `fixture-mem-expired-001` | `memory_ttl_expired` |
| `dependency_edges` | `fixture-edge-unobserved-001` | `dependency_edge_no_longer_observed` |
| `context_packages` | `fixture-ctx-pkg-001` | `stale_context_package` |
| `briefings` | `fixture-briefing-stale-001` | `stale_briefing` |

Reference `as_of`: `2026-05-06T12:00:00+00:00` (pass explicitly for determinism).

### 4.3 Bundle Keys

The bundle is a JSON object. Supported top-level keys:

| Key | Type | Used by rules |
|-----|------|---------------|
| `sources` | list | `source_hash_changed`, `source_deleted` |
| `decisions` | list | `decision_superseded` |
| `evidence_records` | list | `evidence_expired` |
| `memory_records` | list | `memory_ttl_expired` |
| `dependency_edges` | list | `dependency_edge_no_longer_observed` |
| `context_packages` | list | `stale_context_package` |
| `briefings` | list | `stale_briefing` |
| `meta` | object | advisory `as_of` timestamp |

Unknown top-level keys are silently ignored. The `meta` key is consumed before
scanning; its `as_of` value is used as the reference timestamp for time-based
rules if no explicit `as_of` argument is provided.

### 4.4 Advisory `meta.as_of`

The `meta.as_of` field is an ISO-8601 UTC string (e.g. `"2026-05-06T12:00:00+00:00"`).
It is advisory: the CLI and MCP tool read it from the bundle and pass it to
`scan_stale_knowledge_v1`. For fully deterministic scans (e.g. in tests), pass
`as_of` explicitly. If omitted everywhere, the service falls back to
`core.utils.clock.utcnow()`.

---

## 5. Stale Types Reference

| Stale type | Default severity | Trigger condition | Recommended action |
|------------|-----------------|-------------------|-------------------|
| `source_hash_changed` | `warning` | `current_hash != last_verified_hash` | `reverify_source` |
| `source_deleted` | `blocking` | `exists == false` or `deleted_at` set | `reverify_source` |
| `decision_superseded` | `warning` | `superseded_by` set or `status == "superseded"` | `recheck_decision` |
| `evidence_expired` | `warning` | `expires_at < as_of` | `refresh_evidence` |
| `memory_ttl_expired` | `warning` | `expires_at < as_of` | `refresh_memory` |
| `dependency_edge_no_longer_observed` | `warning` | `observed == false` or `last_observed_run_id != current_run_id` | `reobserve_dependency_edge` |
| `stale_context_package` | `warning` | snapshot ID mismatch or freshness window exceeded | `rebuild_context_package` |
| `stale_briefing` | `warning` | snapshot ID mismatch or freshness window exceeded | `regenerate_briefing` |

**Confidence values** (defaults):

| Stale type | Confidence |
|------------|-----------|
| `source_hash_changed` | 0.95 |
| `source_deleted` | 0.99 |
| `decision_superseded` | 0.90 |
| `evidence_expired` | 0.90 |
| `memory_ttl_expired` | 0.90 |
| `dependency_edge_no_longer_observed` | 0.85 |
| `stale_context_package` (snapshot mismatch) | 0.90 |
| `stale_context_package` (freshness exceeded) | 0.80 |
| `stale_briefing` (snapshot mismatch) | 0.90 |
| `stale_briefing` (freshness exceeded) | 0.80 |

---

## 6. Running a Scan

### 6.1 Service-level (Python API)

```python
import json
from pathlib import Path
from tools.surrealdb.stale_knowledge_scan import scan_stale_knowledge_v1

bundle = json.loads(Path("tests/fixtures/surrealdb/stale_knowledge_scan/all_types_bundle.json").read_text())
# Remove meta to pass as_of explicitly for determinism
as_of = bundle.pop("meta", {}).get("as_of")
bundle.pop("_comment", None)

result = scan_stale_knowledge_v1(bundle, as_of=as_of)
print(result.total_count)        # number of findings
print(result.blocking_count)     # number of blocking findings
for f in result.findings:
    print(f.stale_id, f.stale_type, f.severity)
```

Pair with the refresh plan generator:

```python
from tools.surrealdb.stale_refresh_plan import generate_refresh_plan_v1

plan = generate_refresh_plan_v1(result)
for item in plan.plan_items:
    print(item.priority, item.recommended_action, item.target_ref)
    print("write_authorized:", item.write_authorized)  # always False
```

### 6.2 CLI-level

**Scan all findings (JSON output)**:

```bash
python -m tools.surrealdb.stale_context_cli \
    --format json \
    scan-stale-context \
    --input tests/fixtures/surrealdb/stale_knowledge_scan/all_types_bundle.json
```

**Scan with Markdown output**:

```bash
python -m tools.surrealdb.stale_context_cli \
    --format markdown \
    scan-stale-context \
    --input tests/fixtures/surrealdb/stale_knowledge_scan/sample_bundle.json
```

**Fail on blocking findings (for operator-controlled CI integration)**:

```bash
python -m tools.surrealdb.stale_context_cli \
    scan-stale-context \
    --input bundle.json \
    --fail-on-blocking
# exit code 1 if any blocking findings are present
```

**Show a single finding by stale_id**:

```bash
python -m tools.surrealdb.stale_context_cli \
    show-stale-context \
    --input bundle.json \
    --stale-id <stale_id>
# exit code 3 if stale_id not found in bundle
```

**Generate a summary report**:

```bash
python -m tools.surrealdb.stale_context_cli \
    --format markdown \
    report-stale-context \
    --input bundle.json
```

The `report-stale-context` command produces `stale_type_summary` and
`blocking_findings` sections in addition to the standard scan output.

### 6.3 MCP-level

The `cdb_context_stale` tool accepts a JSON request with a `bundle` parameter.
The bundle must be supplied in-memory; no DB or filesystem reads are performed.

**Minimal request (all scopes)**:

```json
{
  "tool": "cdb_context_stale",
  "parameters": {
    "bundle": {
      "sources": [
        {
          "source_id": "src-001",
          "current_hash": "newvalue",
          "last_verified_hash": "oldvalue"
        }
      ]
    },
    "as_of": "2026-05-06T12:00:00+00:00"
  }
}
```

**Filtered request (evidence scope only, blocking severity)**:

```json
{
  "tool": "cdb_context_stale",
  "parameters": {
    "bundle": { "..." : "..." },
    "scope": "evidence",
    "severity": "blocking",
    "limit": 50,
    "include_guardrails": true
  }
}
```

**Response shape**:

```json
{
  "tool": "cdb_context_stale",
  "schema_version": "stale-context-mcp/v1",
  "status": "ok",
  "summary": {
    "total_count": 8,
    "blocking_count": 1,
    "truncated": false,
    "severity_summary": { "info": 0, "warning": 7, "blocking": 1 },
    "stale_type_summary": { "source_deleted": 1, "..." : "..." }
  },
  "findings": [ "..." ],
  "recommended_refresh": [ "..." ],
  "source_refs": [ "..." ],
  "guardrails": [ "..." ],
  "as_of": "2026-05-06T12:00:00+00:00",
  "metadata": { "source": "in_memory", "read_only": true }
}
```

---

## 7. Reading Findings

Every `StaleFinding` returned by the scan service has the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `stale_id` | `str` | Deterministic 16-char SHA256 prefix of `stale_type\|target_ref\|reason`. Stable across identical inputs. |
| `stale_type` | `str` | One of the 8 canonical stale types (see Section 5). |
| `target_ref` | `str` | ID or path of the stale artifact (e.g. `src-deleted-001`). |
| `reason` | `str` | Human-readable explanation of why the artifact is stale. |
| `severity` | `str` | `info`, `warning`, or `blocking`. |
| `confidence` | `float` | Detection confidence in `[0.0, 1.0]`. |
| `source_refs` | `list[str]` | Source IDs involved in the finding. |
| `evidence_refs` | `list[str]` | Evidence record IDs referenced by this finding. |
| `detected_by` | `str` | Service/version that produced this finding (e.g. `stale-knowledge-scan/v1`). |
| `detected_at` | `str` | ISO-8601 UTC timestamp of detection (from `core.utils.clock.utcnow`). |
| `recommended_refresh` | `str` | Human-readable guidance string for the refresh action. |
| `blocking` | `bool` | `true` iff `severity == "blocking"` and status is not `accepted_stale`, `false_positive`, or `refreshed`. |
| `status` | `str` | One of `open`, `accepted_stale`, `false_positive`, `refreshed`. |

**`guardrails`** are always present at the result level (not per-finding):

```
"Stale Detection is signal, not authorization."
"No automatic delete."
"No automatic refresh write."
"No Live-Readiness-Go."
"No Echtgeld-Go."
```

---

## 8. Refresh Plan Interpretation

### 8.1 Priorities

The refresh plan assigns a priority to each plan item based on the source finding's
severity, stale type, confidence, and `blocking` flag:

| Priority | Condition |
|----------|-----------|
| **P0** | `severity == "blocking"` or `blocking == true`. Includes all `source_deleted` findings. |
| **P1** | `severity == "warning"` + time-critical type (`evidence_expired`, `memory_ttl_expired`), OR high-confidence (≥0.85) `decision_superseded` or `source_hash_changed`. |
| **P2** | `severity == "warning"` + context/package/edge types (`stale_context_package`, `stale_briefing`, `dependency_edge_no_longer_observed`), or other warning types below the P1 threshold. |
| **P3** | `severity == "info"` or low-confidence findings. |

### 8.2 Recommended Actions

| Action | Triggered by stale type |
|--------|------------------------|
| `reverify_source` | `source_hash_changed`, `source_deleted` |
| `recheck_decision` | `decision_superseded` |
| `refresh_evidence` | `evidence_expired` |
| `refresh_memory` | `memory_ttl_expired` |
| `reobserve_dependency_edge` | `dependency_edge_no_longer_observed` |
| `rebuild_context_package` | `stale_context_package` |
| `regenerate_briefing` | `stale_briefing` |
| `manual_review` | Unknown stale type (fallback); or `requires_human_review == true` |

### 8.3 `write_authorized` Invariant

**`write_authorized` is always `False` on every plan item.** This is a hard
invariant enforced by the `RefreshPlanItem` dataclass — it is not configurable
and cannot be overridden. The refresh plan is a recommendation, not an execution
order. No action may be taken based solely on a plan item without a separate,
explicit human or operator approval step.

Plan items also carry:

- `requires_human_review: bool` — `true` for `source_deleted`, `blocking`
  severity, unknown/missing target refs, or unknown stale types.
- `status: "pending"` — all items start as pending; status is not updated by
  the tool.
- `blocked_by: []` — empty in the current implementation (no blocking
  conditions modelled in MVP).
- `refresh_inputs` — deduplicated union of `source_refs` and `target_ref`; used
  as context for the reverification step.

---

## 9. Reverification Workflow

When a finding requires follow-up, use this step-by-step process:

1. **Run the scan** — obtain a `StaleKnowledgeScanResult` via CLI or API.
2. **Run the refresh plan** — obtain a `RefreshPlanResult` to understand priorities
   and recommended actions.
3. **Triage by priority** — address P0 findings before P1, P1 before P2/P3.
4. **For each plan item in scope**:
   a. **Collect evidence** — retrieve the current state of the `target_ref`
      artifact (file, decision record, evidence record, etc.) from its
      authoritative source.
   b. **Verify the source** — confirm whether the stale signal is accurate
      (hash truly changed, record truly deleted, evidence truly expired, etc.).
   c. **Evaluate the plan item** — decide whether to proceed with the recommended
      action, mark as `false_positive`, or escalate for human review.
   d. **Obtain a separate GO per write** — each write operation (update of
      `last_verified_hash`, evidence re-collection, memory refresh, etc.)
      requires its own explicit approval step. The plan item itself never grants
      this approval (`write_authorized == false`).
   e. **Document the outcome** — record the decision, evidence collected, and
      resulting state in the appropriate governance artifact (session log,
      decision record, evidence file).
5. **Do not batch-approve** — each finding and each write action is independent.
   Blanket approval of all plan items is not permitted.

---

## 10. Handling Stale Memory / Decisions / Evidence

### Memory TTL Expired (`memory_ttl_expired`)

A `memory_ttl_expired` finding means the memory record's `expires_at` timestamp
has passed relative to `as_of`.

- **Priority**: P1 (time-critical).
- **Recommended action**: `refresh_memory`.
- **Operator steps**:
  1. Identify the memory record by `target_ref`.
  2. Determine whether the content is still accurate.
  3. If still valid: extend the TTL with an explicit approval step.
  4. If outdated: collect updated content and write with explicit approval.
  5. No automatic write — the scan service and refresh plan do not modify any
     memory store.

### Decision Superseded (`decision_superseded`)

A `decision_superseded` finding means the decision record has a `superseded_by`
field pointing to a newer decision, or its `status` is set to `"superseded"`.

- **Priority**: P1 (if confidence ≥ 0.85), P2 otherwise.
- **Recommended action**: `recheck_decision`.
- **Operator steps**:
  1. Locate the superseded decision by `target_ref`.
  2. Confirm that the superseding decision (`superseded_by`) is authoritative
     and up to date.
  3. Archive or tombstone the superseded record via an explicit approval step.
  4. Update any artifacts that reference the superseded decision.
  5. Requires human review for `blocking` severity cases.

### Evidence Expired (`evidence_expired`)

An `evidence_expired` finding means the evidence record's `expires_at` is before
the scan's `as_of` timestamp.

- **Priority**: P1 (time-critical).
- **Recommended action**: `refresh_evidence`.
- **Operator steps**:
  1. Identify the evidence record by `target_ref`.
  2. Determine whether a newer version of this evidence exists or can be
     collected.
  3. Re-collect evidence via the appropriate process (soak run, canary capture,
     manual measurement).
  4. Record the new evidence in the appropriate evidence file with a new
     `expires_at` value.
  5. No automatic evidence write — each step requires explicit approval.

---

## 11. Operator Gates

### When to Stop

Stop processing and escalate to human review if:

- Any `blocking` finding is present (P0 priority) and the recommended action
  is unclear or cannot be safely completed.
- A `source_deleted` finding references an artifact that is still actively
  referenced by downstream artifacts — do not proceed without understanding
  full impact.
- `requires_human_review == true` on a plan item and the operator cannot
  independently determine the correct action.
- The refresh bundle is not trusted (unknown provenance, unexpected IDs, or
  findings that change between consecutive scans on the same bundle — see
  Section 13).

### When Human Review Is Required

Human review is required for:

- All `source_deleted` findings (hard rule — always `requires_human_review == true`).
- All plan items with `severity == "blocking"`.
- Plan items where `target_ref` is missing or resolves to an unknown reference.
- Any situation where the recommended action would affect governance artifacts,
  decision records, or LR-related evidence.
- Any discrepancy between the refresh plan's `recommended_action` and the
  operator's own assessment of the situation.

### Handling Blocking Findings

1. Do not proceed with refresh actions until blocking findings are reviewed.
2. Use `report-stale-context` to get a focused view of blocking findings only:

   ```bash
   python -m tools.surrealdb.stale_context_cli \
       report-stale-context \
       --input bundle.json
   ```

3. Address P0 items first; do not skip to lower-priority items.
4. For CI integration: `--fail-on-blocking` causes exit code `1` when blocking
   findings exist. This is operator-controlled and not enforced by default.

---

## 12. Guardrails / Limits

### System Guardrails

The following guardrails are enforced by the scan service and are included in
every scan result and MCP response:

```
"Stale Detection is signal, not authorization."
"No automatic delete."
"No automatic refresh write."
"No Live-Readiness-Go."
"No Echtgeld-Go."
```

Additional refresh plan guardrails:

```
"Refresh Plan is recommendation only."
"No automatic delete."
"No automatic refresh write."
"No DB write."
"No Live-Readiness-Go."
"No Echtgeld-Go."
```

### Hard Invariants

- `write_authorized` is always `False` — this cannot be configured away.
- No finding changes the LR verdict. Current LR verdict: **NO-GO** (see
  `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`).
- No finding changes the board stage. Current stage: `trade-capable` — orthogonal
  to LR; no live capital, no Grafana gate.
- The scan service never calls wall-clock time directly — all timestamps are via
  `core.utils.clock.utcnow`.
- All `stale_id` and `plan_id` values are deterministic SHA256 prefixes — no
  random UUID generation.

### MCP Tool Limits

- Maximum `limit`: 500 findings per response. Requests above this are silently
  capped.
- Default `limit`: 100. Set explicitly if you expect more findings.
- When `truncated == true` in the response summary, not all findings are included.
  Run with a higher `limit` or use the CLI for full output.

---

## 13. Troubleshooting

### Invalid bundle

**Symptom**: CLI exits with code 2 or MCP returns `"error": "invalid_bundle"`.

**Likely causes**:
- File is not valid JSON.
- Top-level value is not a JSON object (e.g. a list).
- A required sub-field has an unexpected type (e.g. `expires_at` is not a string).

**Resolution**: validate the bundle against the key schema in Section 4.3. Run
`python -m json.tool <bundle.json>` to check JSON validity. Check that all list
items are objects, not primitives.

### No findings returned

**Symptom**: `total_count: 0` despite expecting stale artifacts.

**Likely causes**:
- The bundle's domain lists are empty or contain items that do not trigger any
  rule (e.g. sources with matching hashes, evidence with future `expires_at`).
- `as_of` is set too far in the past — expired items may appear fresh if
  `as_of` predates their `expires_at`.
- Freshness window for `stale_context_package` / `stale_briefing` has not been
  exceeded yet relative to `as_of`.

**Resolution**: check each domain list for completeness. Confirm the `as_of`
value is the intended reference time. Try the `all_types_bundle.json` fixture as
a reference to confirm the tools are working correctly.

### Stale IDs change between runs

**Symptom**: `stale_id` values differ across two scans of the same bundle.

**Likely causes**:
- The `reason` string contains a dynamic component (e.g. a wall-clock timestamp
  outside of the tool's control).
- The bundle contains different values across the two runs (e.g. `current_hash`
  was updated between runs).
- `as_of` was not pinned explicitly and `core.utils.clock.utcnow()` produced
  different values — this affects time-based rules' `detected_at` but not
  `stale_id` (which is derived from `stale_type|target_ref|reason`, not from
  timestamps).

**Note**: `stale_id` stability depends entirely on the stability of
`stale_type`, `target_ref`, and `reason`. The `reason` string includes hash
fragments and timestamps from the input bundle. If the bundle is identical and
`as_of` is pinned, `stale_id` values will be identical. Use the
`test_all_types_fixture_stale_ids_deterministic` test as a reference.

### Limit / truncation

**Symptom**: `truncated: true` in MCP response summary; fewer findings than expected.

**Resolution**: increase the `limit` parameter (max 500):

```json
{ "parameters": { "bundle": { "..." : "..." }, "limit": 500 } }
```

For complete output without truncation, use the CLI `scan-stale-context` command,
which has no pagination limit.

### Pending CodeQL or PR checks are not a runtime signal

Pending or failing CodeQL scans, CI checks, or open PRs are **not** stale
knowledge findings and are not surfaced by this tool. They have no bearing on
the scan results and do not block the stale detection workflow. Do not interpret
a pending check as evidence of stale knowledge.

---

## 14. Related Docs / Issues / PRs

### Issues

| Issue | Title | Role |
|-------|-------|------|
| [#2153](https://github.com/jannekbuengener/Claire_de_Binare/issues/2153) | Wave-16 — Stale knowledge runtime and refresh planning v1 | Parent/anchor — stays open |
| [#2154](https://github.com/jannekbuengener/Claire_de_Binare/issues/2154) | Stale knowledge scan service | Implemented via PR #2368 |
| [#2155](https://github.com/jannekbuengener/Claire_de_Binare/issues/2155) | Stale context CLI | Implemented via PR #2370 |
| [#2157](https://github.com/jannekbuengener/Claire_de_Binare/issues/2157) | Stale context MCP tool | Implemented via PR #2371 |
| [#2158](https://github.com/jannekbuengener/Claire_de_Binare/issues/2158) | Refresh plan generator | Implemented via PR #2372 |
| [#2159](https://github.com/jannekbuengener/Claire_de_Binare/issues/2159) | Stale knowledge fixtures and tests | Implemented via PR #2373 |
| [#2160](https://github.com/jannekbuengener/Claire_de_Binare/issues/2160) | Add stale knowledge runbook | This document |
| [#2161](https://github.com/jannekbuengener/Claire_de_Binare/issues/2161) | Define Wave-16 completion gates | Out of scope for this runbook |

### PRs (merged)

| PR | Title | Merge SHA |
|----|-------|-----------|
| [#2368](https://github.com/jannekbuengener/Claire_de_Binare/pull/2368) | feat(wave16): implement stale knowledge scan service | `09e43564` |
| [#2370](https://github.com/jannekbuengener/Claire_de_Binare/pull/2370) | feat(wave16): add stale context cli | `33b9897` |
| [#2371](https://github.com/jannekbuengener/Claire_de_Binare/pull/2371) | feat(wave16): add stale context mcp tool | `d560929` |
| [#2372](https://github.com/jannekbuengener/Claire_de_Binare/pull/2372) | feat(wave16): add stale refresh plan generator | `f8d47db` |
| [#2373](https://github.com/jannekbuengener/Claire_de_Binare/pull/2373) | test(wave16): add stale knowledge fixtures coverage | `8ac8adb` |

### Related Runbooks

- [`docs/surrealdb/context-contradiction-detection-runbook.md`](context-contradiction-detection-runbook.md)
  — Wave-15 Contradiction Detection runbook; same structural pattern as this document.
- [`docs/runbooks/surrealdb_context_query.md`](../runbooks/surrealdb_context_query.md)
  — SurrealDB context query runbook.
- [`docs/runbooks/surrealdb_context_import.md`](../runbooks/surrealdb_context_import.md)
  — SurrealDB context import runbook.
