# Wave-14 Completion Gates

**Status**: Partial — see Section 3 for open items
**Authority**: Issue #2128 / Wave 14 / Epic #1976
**Parent**: #2115

This document defines the completion gates for Wave-14
(Evidence, decision, and memory retrieval v1).

---

## 1. Scope Baseline

### 1.1 Parent & Child Issues

| Issue | Title | State |
|-------|-------|-------|
| #2115 | Wave-14 anchor: Evidence, decision, and memory retrieval v1 | OPEN — blocked |
| #2116 | Implement evidence lookup v1 | CLOSED |
| #2117 | Implement claim resolution v1 | CLOSED |
| #2118 | Implement decision history query v1 | CLOSED |
| #2119 | Implement decision replay v1 | CLOSED |
| #2120 | Implement scoped memory read v1 | CLOSED |
| #2121 | Implement context trust summary builder v1 | CLOSED |
| #2122 | Enrich agent briefing with evidence, decisions, and memory | **OPEN** |
| #2123 | Implement evidence resolve MCP tool v1 | CLOSED |
| #2124 | Implement decision history/replay MCP tool v1 | CLOSED |
| #2125 | Implement scoped memory read MCP tool v1 | CLOSED |
| #2126 | Add tests and fixtures for evidence, decision, and memory retrieval | CLOSED (partial — see Section 4) |
| #2127 | Add evidence, decision, and memory retrieval runbook | CLOSED |
| #2128 | Define wave-14 completion gates | CLOSED (this document) |

### 1.2 Merged PRs

| PR | Title | SHA |
|----|-------|-----|
| #2340 | feat(surrealdb): implement decision history and replay v1 | `b2e95ecf` |
| #2342 | docs(surrealdb): define wave-13 completion gates | `014edb5d` |
| #2343 | feat(wave14): implement evidence, claim, memory, and trust services v1 | `4db9892a` |
| #2344 | docs(status): record wave-13 and wave-14 completion | `7a1e8751` |

---

## 2. Deliverables

### 2.1 Service Implementations (all COMPLETE)

| File | Description | State |
|------|-------------|-------|
| `tools/surrealdb/evidence_lookup.py` | Evidence Lookup v1 | MERGED (`4db9892a`) |
| `tools/surrealdb/claim_resolver.py` | Claim Resolution v1 | MERGED (`4db9892a`) |
| `tools/surrealdb/memory_read.py` | Scoped Memory Read v1 | MERGED (`4db9892a`) |
| `tools/surrealdb/trust_summary.py` | Context Trust Summary Builder v1 | MERGED (`4db9892a`) |
| `tools/surrealdb/decision_history_query.py` | Decision History Query v1 | MERGED (`b2e95ecf`) |
| `tools/surrealdb/decision_replay_builder.py` | Decision Replay Builder v1 | MERGED (`b2e95ecf`) |

All services are read-only, fail-closed, in-memory (NoopAdapter pattern). No SurrealDB writes.

### 2.2 MCP Adapter Files (PARTIAL)

| File | Description | State |
|------|-------------|-------|
| `tools/mcp/context_evidence_memory_tools.py` | MCP handlers: evidence / claim / memory / trust | MERGED (`4db9892a`) |
| `tools/mcp/context_decision_tools.py` | MCP handlers: decision history / replay | MERGED (`b2e95ecf`) |

**Known gap (#2122, PR 2 pending):** The 6 Wave-14 MCP tool names
(`cdb_context_evidence_resolve`, `cdb_context_claim_resolve`, `cdb_context_memory_get`,
`cdb_context_trust_summary`, `cdb_context_decision_history`, `cdb_context_decision_replay`)
are **not yet registered in `tools/mcp/registry.py`**. Until PR 2 merges, these tools are
accessible only by direct handler import, not via the registry routing path.

### 2.3 Briefing Enrichment (PARTIAL — #2122 OPEN)

`tools/mcp/context_bridge.py` carries Briefing Enrichment output fields
(`enriched_evidence`, `enriched_decisions`, `enriched_memory`, `trust_summary`) but
**does not yet call the Wave-14 retrieval services**. The fields currently return empty
lists with a partial-mode trust summary string.

Full wiring (`lookup_evidence_v1`, `resolve_claims_v1`, `read_memory_v1`,
`build_trust_summary_v1` called from `cdb_context_briefing_handler`) is scope of
**PR 2 (code slice for #2122)**. Until that PR merges, Briefing Enrichment remains
a documented stub.

### 2.4 Schema & Docs

| File | PR |
|------|----|
| `docs/surrealdb/decision_replay_query_contract.md` | #2340 |
| `docs/surrealdb/context-briefing-enrichment-model-v1.md` | pre-existing |
| `docs/surrealdb/context-evidence-claim-memory-runbook.md` | this PR |
| `docs/surrealdb/context-wave14-completion-gates.md` | this PR (this document) |

### 2.5 Tests (53 pass for core services)

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/unit/surrealdb/test_wave14_services_v1.py` | 37 | PASSED |
| `tests/unit/tools/mcp/test_mcp_wave14_tools.py` | 16 | PASSED |
| `tests/unit/surrealdb/test_decision_history_query_v1.py` | ✓ | PASSED |
| `tests/unit/surrealdb/test_decision_replay_builder_v1.py` | ✓ | PASSED |
| `tests/unit/surrealdb/test_decision_mcp_tools_v1.py` | ✓ | PASSED |
| `tests/unit/tools/mcp/test_mcp_briefing_enrichment.py` | 5 (stub only) | PASSED — partial |

**Known gap (#2126 closed-but-partial):** `test_mcp_briefing_enrichment.py` covers
only the stub behavior (empty lists + partial-mode trust string). Tests for the fully
wired briefing enrichment (with real service calls) are scope of PR 2.

### 2.6 Fixtures

| Directory / File | Description |
|------------------|-------------|
| `tests/fixtures/surrealdb/wave14/wave14_v1.json` | Evidence / claim / memory fixture |
| `tests/fixtures/surrealdb/decision_history/` | Decision history fixture data |
| `tests/fixtures/surrealdb/decision_replay/` | Decision replay fixture data |
| `tests/fixtures/surrealdb/decision_mcp/` | Decision MCP fixture data |

---

## 3. Completion Gate Criteria

| Gate | Required | Status |
|------|----------|--------|
| #2116 Evidence Lookup v1 CLOSED | Yes | ✅ CLOSED |
| #2117 Claim Resolution v1 CLOSED | Yes | ✅ CLOSED |
| #2118 Decision History v1 CLOSED | Yes | ✅ CLOSED |
| #2119 Decision Replay v1 CLOSED | Yes | ✅ CLOSED |
| #2120 Scoped Memory Read v1 CLOSED | Yes | ✅ CLOSED |
| #2121 Trust Summary Builder v1 CLOSED | Yes | ✅ CLOSED |
| #2122 Briefing Enrichment CLOSED | Yes | ❌ OPEN — PR 2 pending |
| #2123 Evidence MCP Tool CLOSED | Yes | ✅ CLOSED |
| #2124 Decision MCP Tools CLOSED | Yes | ✅ CLOSED |
| #2125 Memory MCP Tool CLOSED | Yes | ✅ CLOSED |
| #2126 Tests/Fixtures CLOSED | Yes | ✅ CLOSED (partial — see 2.5) |
| #2127 Runbook CLOSED | Yes | ✅ CLOSED |
| #2128 Gates doc CLOSED | Yes | ✅ CLOSED (this document) |
| All Wave-14 services read-only, fail-closed | Yes | ✅ NoopAdapter pattern |
| No SurrealDB writes | Yes | ✅ confirmed |
| MCP tools registered in registry.py | Yes | ❌ PR 2 pending |
| Briefing Enrichment wired (real service calls) | Yes | ❌ PR 2 pending |
| Enrichment tests cover real wiring | Yes | ❌ PR 2 pending |
| No live capital, no Echtgeld | Yes | ✅ LR remains NO-GO |
| Runbook committed | Yes | ✅ this PR |
| Gates doc committed | Yes | ✅ this document |

**Wave-14 is NOT YET COMPLETE.** Three gate criteria remain open, all scoped to PR 2:

1. Registry registration of 6 Wave-14 MCP tools
2. Briefing Enrichment real wiring in `context_bridge.py`
3. Enrichment tests covering real service calls

**#2115 remains blocked** until all gates are satisfied.

---

## 4. Known Open Items (Not Blockers for This Doc PR)

### 4.1 #2122 — Briefing Enrichment (OPEN)

Scope for PR 2:
- Wire `lookup_evidence_v1`, `resolve_claims_v1`, `read_memory_v1`, `build_trust_summary_v1`
  into `cdb_context_briefing_handler()` in `tools/mcp/context_bridge.py`.
- Fail-closed: empty input records → honest empty output, no exception.
- Extend `test_mcp_briefing_enrichment.py` with integration-level tests using real records.

### 4.2 #2126 — Tests (closed-but-partial)

`test_mcp_briefing_enrichment.py` covers only stub state. PR 2 must add tests that
exercise the real enrichment wiring. #2126 should not be reopened; PR 2 will satisfy
the remaining scope.

### 4.3 Registry Verdrahtung (#2123/#2124/#2125 — partial)

All three MCP tools exist as adapter functions but are not registered in
`tools/mcp/registry.py`. PR 2 must add `ToolDefinition` entries for all 6 Wave-14
tool names with `read_only=True`.

---

## 5. Governance Notes

- **LR-STATUS:** NO-GO (unchanged — Wave 14 is context tooling, not trading)
- **Board-Stage:** `trade-capable` (ratified 2026-04-08, orthogonal to LR — does not
  authorize Echtgeld or live capital)
- `approval_semantics.no_echtgeld_go: true` is carried in every Wave-14 tool response
- All Wave-14 services are read-only traces; no mutation of system state
- Decisions and evidence are explanatory; they do not substitute for human GO signals
