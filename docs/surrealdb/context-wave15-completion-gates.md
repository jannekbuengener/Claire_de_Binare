# Wave-15 Completion Gates

**Status**: CLOSED — all gates satisfied (see Section 3)  
**Authority**: Issue #2152 / Wave-15 / Epic #1976  
**Parent**: #2145

This document defines and tracks the completion gates for Wave-15
(Contradiction Detection Runtime v1).

---

## 1. Scope Baseline

### 1.1 Parent & Child Issues

| Issue | Title | State |
|-------|-------|-------|
| #2145 | Wave-15 anchor: Contradiction Detection Runtime v1 | OPEN — closure pending this doc |
| #2146 | Implement contradiction scan runtime v1 | CLOSED |
| #2147 | Add contradiction scan CLI | CLOSED |
| #2148 | Add contradiction MCP tool `cdb_context_contradictions` | CLOSED |
| #2149 | Generate contradiction report | CLOSED — this slice |
| #2150 | Add contradiction fixtures and tests | CLOSED — this slice |
| #2151 | Add contradiction detection runbook | CLOSED — this slice |
| #2152 | Define wave-15 completion gates | CLOSED (this document) |

### 1.2 Merged PRs

| PR | Title | SHA |
|----|-------|-----|
| #2347 | feat(wave15): implement contradiction scan runtime v1 | `e4b74958` |
| #2348 | feat(wave15): add contradiction scan cli | `b092e648` |
| #2350 | feat(wave15): add contradiction MCP tool cdb_context_contradictions | `9badfdc9` |

---

## 2. Deliverables

### 2.1 Service Implementation (COMPLETE)

| File | Description | State |
|------|-------------|-------|
| `tools/surrealdb/contradiction_scan.py` | Contradiction Scan Runtime v1 | MERGED (`e4b74958`) |

9 detection rules: `doc_vs_code`, `doc_vs_decision`, `decision_vs_evidence`,
`claim_vs_evidence`, `memory_vs_source`, `current_status_vs_live_surface`,
`runbook_vs_contract`, `test_vs_claim`, `stale_decision_vs_new_evidence`.

All rules are read-only, fail-closed, deterministic (SHA256 IDs, clock via
`core.utils.clock.utcnow`). No SurrealDB writes. No network.

### 2.2 CLI (COMPLETE)

| File | Description | State |
|------|-------------|-------|
| `tools/surrealdb/contradiction_cli.py` | Contradiction Scan CLI v1 | MERGED (`b092e648`) |

Three subcommands: `scan-contradictions`, `show-contradiction`, `report-contradictions`.

`report-contradictions` output includes:
- `summary.blocking`, `summary.false_positives`, `summary.accepted_risks`, `summary.warning`, `summary.info`
- `recommended_next_reads` (blocking findings first, capped at 20)
- `affected_artifacts` (all source/claim/evidence refs, deduplicated, sorted)
- `guardrail` note on every response

Exit codes: `0 = ok`, `1 = error`, `2 = blocking (with --fail-on-blocking)`.

### 2.3 MCP Tool (COMPLETE)

| File | Description | State |
|------|-------------|-------|
| `tools/mcp/context_contradiction_tools.py` | MCP handler: `cdb_context_contradictions` | MERGED (`9badfdc9`) |
| `tools/mcp/registry.py` | Tool registration (Wave-15 entry added) | MERGED (`9badfdc9`) |
| `tools/mcp/context_bridge.py` | Bridge routing (Wave-15 tool wired) | MERGED (`9badfdc9`) |
| `tools/mcp/permission_guard.py` | Permission guard (Wave-15 tool exempted for read-only) | MERGED (`9badfdc9`) |

MCP output always includes `no_live_go: true` and `no_write: true`.

### 2.4 Report (COMPLETE — this slice, #2149)

`report-contradictions` subcommand fully covers the required report spec:

| Required field | Present |
|----------------|---------|
| Finding counts (`total_findings`, `blocking_count`) | ✅ |
| Severity summary (`blocking`, `warning`, `info`) | ✅ |
| Blocking contradictions list | ✅ `summary.blocking` |
| Affected artifacts | ✅ `affected_artifacts` |
| False positives | ✅ `summary.false_positives` |
| Accepted risks | ✅ `summary.accepted_risks` |
| Recommended next reads | ✅ `recommended_next_reads` |
| No secrets in output | ✅ confirmed |
| No auto-correction | ✅ read-only contract |
| No issue creation | ✅ no GitHub API calls |

### 2.5 Tests and Fixtures (COMPLETE — this slice, #2150)

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/unit/surrealdb/test_contradiction_scan.py` | All 9 rules + overrides + determinism | MERGED (`e4b74958`) |
| `tests/unit/surrealdb/test_contradiction_cli.py` | All 3 subcommands + report buckets | this slice |
| `tests/unit/tools/mcp/test_mcp_contradiction_tool.py` | 20 test groups | MERGED (`9badfdc9`) |

All tests run without a live SurrealDB instance. All fixtures are inline or minimal JSON
files. No secrets, no writes.

Fixture files:

| File | Description |
|------|-------------|
| `tests/fixtures/surrealdb/contradiction_scan/sample_bundle.json` | Mixed blocking/warning (MERGED `b092e648`) |
| `tests/fixtures/surrealdb/contradiction_scan/false_positive_bundle.json` | Invalidated claim + false_positive override (this slice) |
| `tests/fixtures/surrealdb/contradiction_scan/accepted_risk_bundle.json` | Stale claim + accepted_risk override (this slice) |

### 2.6 Runbook (COMPLETE — this slice, #2151)

| File | Description |
|------|-------------|
| `docs/surrealdb/context-contradiction-detection-runbook.md` | Operator/agent runbook for contradiction detection |

Covers: running a scan, generating a report, reading findings, blocking findings,
false positives, accepted risks, next reads, guardrails, governance notes.

---

## 3. Completion Gate Criteria

| Gate | Required | Status |
|------|----------|--------|
| #2146 Scan Runtime CLOSED (PR #2347) | Yes | ✅ CLOSED |
| #2147 CLI CLOSED (PR #2348) | Yes | ✅ CLOSED |
| #2148 MCP Tool CLOSED (PR #2350) | Yes | ✅ CLOSED |
| #2149 Report CLOSED (this slice) | Yes | ✅ CLOSED |
| #2150 Tests/Fixtures CLOSED (this slice) | Yes | ✅ CLOSED |
| #2151 Runbook CLOSED (this slice) | Yes | ✅ CLOSED |
| #2152 Gates doc CLOSED (this document) | Yes | ✅ CLOSED |
| All services read-only, fail-closed | Yes | ✅ confirmed |
| No SurrealDB writes | Yes | ✅ confirmed |
| No auto-fix | Yes | ✅ confirmed |
| No auto issue/PR creation | Yes | ✅ confirmed |
| No secrets in output | Yes | ✅ confirmed |
| `no_live_go: true` in MCP output | Yes | ✅ confirmed |
| `no_write: true` in MCP output | Yes | ✅ confirmed |
| Runbook committed | Yes | ✅ this slice |
| Gates doc committed | Yes | ✅ this document |
| No live capital, no Echtgeld | Yes | ✅ LR remains NO-GO |

**Wave-15 is COMPLETE.** All gate criteria are satisfied.

**#2145 is ready for closure** pending human review of this PR.

---

## 4. Anti-Criteria (What This Wave Does NOT Do)

The following are explicit non-goals for Wave-15. Any PR that introduces these
behaviours must be rejected.

| Anti-criterion | Detail |
|----------------|--------|
| No automatic fix | Detection never modifies any file, record, or system state |
| No automatic issue creation | No GitHub issues, PRs, or comments are created by detection |
| No repo/GitHub write | No `git commit`, `git push`, or GitHub API write from detection tooling |
| No live-go | A contradiction finding does not constitute a live-trading or Echtgeld-Go signal |
| No LR override | LR-STATUS remains NO-GO unless explicitly changed by human gate |
| No Wave-16–21 scope | Wave-15 is bounded to contradiction detection and report only |

---

## 5. Detection as Signal

> **Detection is signal, not action authority.**

A contradiction finding means: "The system detected a potential inconsistency.
A human or authorised agent should review and decide."

It does NOT mean:
- The inconsistency is confirmed.
- Any action is required immediately.
- Any automated remediation is permitted.
- Any live-trading or Echtgeld decision is unlocked.

---

## 6. Governance Notes

- **LR-Status**: NO-GO (unchanged — Wave-15 is context tooling, not trading infrastructure)
- **Board-Stage**: `trade-capable` (ratified 2026-04-08 via Issue #1492) —
  orthogonal to LR-STATUS; does not authorise live capital or strategy execution
- `DELIVERY_APPROVED.yaml` is human-controlled; this document does not modify it
- All Wave-15 services are read-only; no mutation of system state
- Contradiction findings are explanatory signals; they do not substitute for human GO signals
