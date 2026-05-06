# Contradiction Detection Runbook

**Status**: Operational  
**Authority**: Issue #2151 / Wave-15 / Epic #1976  
**Parent**: #2145

This runbook describes how operators and agents use the Contradiction Detection
system (Wave-15) to scan, read, interpret, and act on contradiction findings.

**LR-Status: NO-GO** — this runbook covers read-only context tooling only.
No live capital, no Echtgeld-Go, no trading implication.

---

## 1. Purpose and Scope

The Contradiction Detection system detects inconsistencies across:
- Documentation vs. code (`doc_vs_code`)
- Documentation vs. decision records (`doc_vs_decision`)
- Decisions vs. evidence (`decision_vs_evidence`)
- Claims vs. evidence (`claim_vs_evidence`)
- Memory vs. source of truth (`memory_vs_source`)
- CURRENT_STATUS vs. live system surfaces (`current_status_vs_live_surface`)
- Runbooks vs. contracts (`runbook_vs_contract`)
- Tests vs. claims (`test_vs_claim`)
- Stale decisions vs. new evidence (`stale_decision_vs_new_evidence`)

**Detection is signal, not action authority.** No finding authorises any automated
action, write, deployment, trade, or live-go.

---

## 2. Tool Overview

### Service — `tools/surrealdb/contradiction_scan.py`

- **Schema version**: `contradiction-scan/v1`
- **API**: `scan_contradictions_v1(records, overrides) → ContradictionScanResult`
- **Read-only**. No SurrealDB writes. No network. No file output.
- **Deterministic**: SHA256 IDs, clock via `core.utils.clock.utcnow`.

### CLI — `tools/surrealdb/contradiction_cli.py`

Three subcommands:

| Command | Purpose |
|---------|---------|
| `scan-contradictions` | Scan input bundle, output all findings |
| `show-contradiction` | Show a single finding by `contradiction_id` |
| `report-contradictions` | Generate a structured summary report |

Exit codes: `0 = ok`, `1 = CLI/input error`, `2 = blocking (with --fail-on-blocking)`.

### MCP Tool — `cdb_context_contradictions`

- **Handler**: `tools/mcp/context_contradiction_tools.py`
- **Tool name**: `cdb_context_contradictions`
- **Output keys**: `findings`, `blocking_count`, `recommended_next_reads`, `no_live_go`, `no_write`
- Registered in `tools/mcp/registry.py`.

---

## 3. Running a Scan

Prepare an input bundle as a JSON file. The bundle may contain any combination of
supported record types (see Section 4). Run:

```bash
python -m tools.surrealdb.contradiction_cli \
    --format json \
    scan-contradictions \
    --input path/to/bundle.json
```

To surface blocking findings and exit with code 2 if any are found (for CI gates):

```bash
python -m tools.surrealdb.contradiction_cli \
    scan-contradictions \
    --input bundle.json \
    --fail-on-blocking
```

To filter to a specific contradiction type:

```bash
python -m tools.surrealdb.contradiction_cli \
    scan-contradictions \
    --input bundle.json \
    --type claim_vs_evidence
```

---

## 4. Input Bundle Format

The bundle is a JSON object. Supported top-level keys:

| Key | Type | Used by rules |
|-----|------|---------------|
| `doc_claims` | list | `doc_vs_code`, `doc_vs_decision` |
| `code_symbols` | list | `doc_vs_code` |
| `decision_records` | list | `doc_vs_decision`, `decision_vs_evidence`, `stale_decision_vs_new_evidence` |
| `evidence_records` | list | `decision_vs_evidence`, `stale_decision_vs_new_evidence` |
| `claims` | list | `claim_vs_evidence` |
| `memory_records` | list | `memory_vs_source` |
| `source_records` | list | `memory_vs_source` |
| `live_surfaces` | list | `current_status_vs_live_surface` |
| `runbook_records` | list | `runbook_vs_contract` |
| `test_records` | list | `test_vs_claim` |
| `overrides` | dict | Override status of specific findings (see Section 6–7) |

Unknown keys are silently ignored. The `overrides` key is consumed before scanning.

**Minimal example** (triggers `claim_vs_evidence` warning):

```json
{
  "claims": [
    {
      "claim_id": "c-001",
      "status": "stale",
      "topic": "Deployment SOP v1",
      "evidence_refs": ["ev-001"]
    }
  ]
}
```

---

## 5. Generating a Report

```bash
python -m tools.surrealdb.contradiction_cli \
    --format json \
    report-contradictions \
    --input bundle.json
```

Or as Markdown:

```bash
python -m tools.surrealdb.contradiction_cli \
    --format markdown \
    report-contradictions \
    --input bundle.json
```

### Report Output Fields

| Field | Description |
|-------|-------------|
| `total_findings` | Total number of findings (all severities) |
| `blocking_count` | Number of actively blocking findings |
| `summary.blocking` | Findings with `severity=blocking` and not overridden |
| `summary.false_positives` | Findings overridden as `false_positive` |
| `summary.accepted_risks` | Findings overridden as `accepted_risk` |
| `summary.warning` | Findings with `severity=warning` (not overridden) |
| `summary.info` | Findings with `severity=info` (not overridden) |
| `recommended_next_reads` | Paths/IDs to review, blocking findings first |
| `affected_artifacts` | All paths/IDs across all findings (deduplicated, sorted) |
| `guardrail` | Guardrail note (always present) |

---

## 6. Reading Findings

Each finding contains:

| Field | Description |
|-------|-------------|
| `contradiction_id` | Deterministic SHA256-based ID (16 hex chars) |
| `contradiction_type` | One of the 9 rule types |
| `source_a_ref` | Primary source (`ref_id`, `ref_type`, `path`, `description`) |
| `source_b_ref` | Opposing source |
| `claim_refs` | Related claim IDs |
| `evidence_refs` | Related evidence refs (`evidence_id`, `evidence_type`, `strength`) |
| `severity` | `info`, `warning`, or `blocking` |
| `confidence` | Float `[0.0, 1.0]` |
| `detected_by` | Always `contradiction-scan/v1` |
| `detected_at` | ISO 8601 UTC timestamp |
| `status` | `open`, `false_positive`, `accepted_risk`, `acknowledged`, etc. |
| `blocking` | `true` only if `severity=blocking` and status is not an override |
| `recommended_action` | Human-readable remediation hint (signal only) |

---

## 7. Interpreting Blocking Findings

A finding is **blocking** when `severity == "blocking"` and no override has been applied.

Blocking findings indicate a detected inconsistency that — if confirmed — requires
human review. They do **not** automatically trigger any action.

**Operator response for a blocking finding:**

1. Read `source_a_ref` and `source_b_ref` to understand the two conflicting sources.
2. Follow `recommended_action` as a hint (not a mandate).
3. Consult `recommended_next_reads` for related artifacts to inspect.
4. Decide: confirm the contradiction, mark as false_positive, or mark as accepted_risk.

**What NOT to do:**
- Do not let tooling auto-fix the underlying inconsistency.
- Do not auto-close issues or auto-create new ones.
- Do not treat a blocking finding as a live-trading go/no-go signal.

---

## 8. Marking False Positives

A false positive is a finding that was triggered by the detection rules but does not
represent a real inconsistency in the current context.

To mark a finding as false positive, add an `"overrides"` key to the input bundle:

```json
{
  "claims": [...],
  "overrides": {
    "<contradiction_id>": "false_positive"
  }
}
```

The finding remains visible in the report under `summary.false_positives` with
`blocking=false`. It is **never discarded** — the audit trail is preserved.

To discover a `contradiction_id`, first run `scan-contradictions` and note the ID
from the output.

---

## 9. Marking Accepted Risks

An accepted risk is a finding where the inconsistency is real but has been explicitly
acknowledged as acceptable for the current context.

```json
{
  "overrides": {
    "<contradiction_id>": "accepted_risk"
  }
}
```

The finding appears under `summary.accepted_risks` with `blocking=false`.

Both `false_positive` and `accepted_risk` overrides:
- Set `status` on the finding to the override value.
- Set `blocking=false`.
- Never suppress or discard the finding.
- Do not modify any repository file, issue, or system state.

---

## 10. Deriving Next Reads

The `recommended_next_reads` output field contains paths and IDs derived from
blocking findings first, then non-blocking, capped at 20 entries. These are
**signals** for human or agent review, not commands.

Example use:
- Feed the list into a briefing tool to load relevant context.
- Review the listed artifacts to confirm or resolve the contradiction.

---

## 11. Guardrails

| Rule | Detail |
|------|--------|
| No auto-fix | Detection never modifies any file, record, or system state |
| No auto-create | No issues, PRs, or comments are created by detection |
| No repo write | No `git commit`, `git push`, or GitHub API write |
| No live-go | A finding does not constitute a live-trading or Echtgeld-Go signal |
| No LR override | LR-STATUS remains NO-GO unless explicitly changed by human gate |
| Read-only | All scan operations are side-effect-free |
| No secrets in output | Finding output never includes API keys, tokens, or credentials |

---

## 12. Governance Notes

- **LR-Status**: NO-GO (Wave-15 is context tooling, not trading infrastructure)
- **Board-Stage**: `trade-capable` (ratified 2026-04-08 via Issue #1492) —
  orthogonal to LR-STATUS; does not authorise live capital or strategy execution
- `no_live_go: true` is always present in MCP tool output
- `no_write: true` is always present in MCP tool output
- All contradiction detection is read-only and audit-preserving
- Findings are explanatory signals, not action permissions

---

## 13. Related Documents

- [docs/surrealdb/context-wave15-completion-gates.md](context-wave15-completion-gates.md) — Wave-15 gate status
- [docs/surrealdb/context-evidence-claim-memory-runbook.md](context-evidence-claim-memory-runbook.md) — Wave-14 retrieval runbook
- `tools/surrealdb/contradiction_scan.py` — service implementation
- `tools/surrealdb/contradiction_cli.py` — CLI implementation
- `tools/mcp/context_contradiction_tools.py` — MCP adapter
