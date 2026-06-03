# CDB PASS_WITH_LIMITS ratification — Benchmark #2 / harness minimal profile

Status: Ratification record (closes [#2852](https://github.com/jannekbuengener/Claire_de_Binare/issues/2852))  
Parent meta: [#2847](https://github.com/jannekbuengener/Claire_de_Binare/issues/2847)  
Harness: `tools/surrealdb/context_live_invocation_harness.py` (`--profile minimal` default, `--profile full` optional)  
Benchmark source: [`CDB_ALL_TOOLS_LIVE_INVOCATION_PROOF_2026-06-03.md`](CDB_ALL_TOOLS_LIVE_INVOCATION_PROOF_2026-06-03.md)

Boundaries: No live-go, no persist activation, no MCP mutations. LR **NO-GO** unchanged.

---

## Summary vs matrix count (6 vs 8)

| Count | What it measured |
|-------|------------------|
| **6** | Executive summary in Benchmark #2: distinct **limitation classes** still open after that session (host cwd, five `missing_*` record paths, bundle gap). |
| **8** | Per-tool matrix rows marked **PASS_WITH_LIMITS** (or equivalent) including `context.readiness` (MCP-only) and `cdb_context_stale` (call without bundle). |

**Reconciliation after #2844 / #2848 / #2849 (bridge harness on `main`):**

- `cdb_context_scope_drift`: **FAIL → PASS** ([#2844](https://github.com/jannekbuengener/Claire_de_Binare/issues/2844), PR #2857).
- `context.readiness`: **PASS_WITH_LIMITS (MCP cwd) → PASS** on bridge when canon + stop_conditions satisfied ([#2848](https://github.com/jannekbuengener/Claire_de_Binare/issues/2848), PR #2859).
- `cdb_context_stale`: **PASS_WITH_LIMITS (no bundle) → PASS** when harness supplies `bundle` + `scope` (manifest fix in #2849).
- **Remaining 6** on `--profile minimal`: Wave-14 record tools invoked **without** inline `*_records` / `records` — intentional fail-closed proof, not handler defects.

`cdb_context_memory_write_intent` is **PASS** (refused) on bridge; MCP-only **BLOCKED_SAFETY** remains an accepted Smart Mode boundary, not a PASS_WITH_LIMITS row.

---

## Per-tool decisions

| tool_name | Root cause | Decision | Safety impact | Recheck trigger |
|-----------|------------|----------|---------------|-----------------|
| `context.readiness` | MCP host `cwd` ≠ repo root; empty `required_reads` without canon check (pre-#2848) | **FIXED (bridge)** + **ACCEPTED_LIMITATION (MCP cwd)** | Readiness is not authorization; LR NO-GO | Re-run MCP from repo root; harness `--profile minimal` |
| `cdb_context_evidence_resolve` | No `evidence_records[]` in minimal call | **ACCEPTED_LIMITATION** | Lookup-only; no writes | `make context-live-invoke` or `--profile full` |
| `cdb_context_claim_resolve` | No `claim_records[]` | **ACCEPTED_LIMITATION** | Resolver fail-closed; no approval | Harness full profile / supply records in integration |
| `cdb_context_memory_get` | No `memory_records[]` | **ACCEPTED_LIMITATION** | Read-only memory surface | Harness full profile |
| `cdb_context_decision_history` | No `decision_events[]` | **ACCEPTED_LIMITATION** | History query only | Harness full profile |
| `cdb_context_decision_replay` | No `decision_events[]` | **ACCEPTED_LIMITATION** | Replay builder only | Harness full profile |
| `cdb_context_contradictions` | No `records` object (bundle alone insufficient) | **ACCEPTED_LIMITATION** | Scan-only; no mutation | Harness full profile with `records` dict |
| `cdb_context_stale` | Benchmark called without `bundle` | **FIXED (harness)** | Stale scan read-only | `make context-live-invoke` |
| `cdb_context_scope_drift` | `AttributeError` on minimal bundle (pre-#2844) | **FIXED** ([#2844](https://github.com/jannekbuengener/Claire_de_Binare/issues/2844)) | No scope mutation | Harness must stay PASS |

---

## ACCEPTED_LIMITATION rationale (Wave-14 minimal profile)

The six remaining **PASS_WITH_LIMITS** results on `--profile minimal` prove that handlers:

1. Are **callable** (real JSON, not inventory-only).
2. **Fail closed** when inline adapter inputs are omitted (no silent empty success).
3. Do **not** require productive SurrealDB or MCP writes for regression signal.

Supplying inline benchmark records is validated separately via `--profile full` (all 27 **PASS**, 0 **PASS_WITH_LIMITS** on bridge).

---

## Validation commands

```bash
# Minimal profile (fail-closed record paths — 6 PASS_WITH_LIMITS expected)
make context-live-invoke

# Full inline-record profile (27 PASS expected)
make context-live-invoke-full

pytest tests/unit/surrealdb/test_context_live_invocation_harness.py -q
```

---

## Brain Evidence

```text
brain_source: repo-only
brain_status: used
tools_or_queries:
  - python -m tools.surrealdb.context_live_invocation_harness --profile minimal
  - python -m tools.surrealdb.context_live_invocation_harness --profile full
records_or_results:
  - minimal: 21 PASS, 6 PASS_WITH_LIMITS, 0 FAIL (main post-#2849)
  - full: 27 PASS, 0 PASS_WITH_LIMITS, 0 FAIL (expected after #2852)
limitations:
  - MCP stdio path and Smart Mode write-intent block not re-proven each run
```
