# Session Log: #2605 MCP Agent Surface Smoke Slice 3

**Date:** 2026-05-29  
**Issue:** [#2605](https://github.com/jannekbuengener/Claire_de_Binare/issues/2605) (Epic — Context / Memory / Evidence / Decision MCP Tools)  
**Branch:** `main` @ `d93a2ffe` (read-only smoke; no code PR)  
**LR:** NO-GO (unchanged)  
**Board stage:** trade-capable (orthogonal; no live capital)

## Scope

Bridge-level MCP agent-surface smoke for #2605: registry vs `create_bridge()` runtime, tool inventory,
read-only contract, base + Wave-14 dispatch, source honesty, permission guard, capability files.
No SurrealDB marathon, no CLI `context-smoke-db`, no trading/runtime changes, no productive DB writes.
#2603 / #2604 / #2606 context only. Issue **not** closed.

## Brain Evidence

```text
brain_source: repo-only (+ local bridge invoke; no DB-backed MCP claims)
brain_status: not-used
tools_or_queries:
  - create_bridge().list_tools() / execute_tool()
  - pytest tests/unit/tools/mcp/* (issue validation bundle)
  - make context-doctor (read-only preflight)
  - docker ps (BLUE/RED read-only health)
records_or_results:
  - 26 tools; 26 registry placeholders before bridge; 0 stubs after bridge
  - All list_tools entries readOnly=true
  - Wave-14 forged surrealdb-local params → metadata.source=in_memory
  - context.search INSERT → forbidden_keyword
  - claire-de-binare.mcp.json: cdb_context present; stdio import OK
```

## Registry vs Bridge (canonical runtime)

| Check | Result |
|-------|--------|
| `ContextToolRegistry` before `create_bridge()` (fresh subprocess) | **26/26** handlers = `not_implemented_handler` (expected placeholders) |
| After `create_bridge()` | **0** stub handlers; all tools wired to real handlers |
| `list_tools()` count | **26** (matches runbook §1.5 expectation) |
| `readOnly` on every listed tool | **PASS** |
| `get_read_only_status().enforced` | **true** |

**Red flag avoided:** Inspecting registry without `create_bridge()` would falsely report all tools as `not_implemented`.

## Base Context tools (bridge `execute_tool`, in-memory / noop adapter)

| Tool | Smoke call | Result |
|------|------------|--------|
| `context.search` | `query=smoke` | `ok` (not `not_implemented`) |
| `context.trace` | `target_id=evt_smoke_2605` | `ok` |
| `context.explain_source` | `source_ref=tool:context.search` | `ok` |
| `context.package` | minimal artifact id | `error` `invalid_artifacts` (validation, real handler) |
| `context.readiness` | `action=session_start` | `ok` |
| `context.self_explain` | `{}` | `error` `invalid_question` (validation) |
| `context.briefing` | valid `task_scope` + `operation_mode=read_only` | `ok` |
| `context.stop_resolver` | `stop_id=smoke` | `ok` |
| `context.required_reads` | minimal | `error` `invalid_task_scope` (validation) |
| `context.show_snapshot` | `min_count=0` | `error` `invalid_snapshot_id` (needs id; see unit tests) |
| `context.show_audit` | `{}` | `error` `invalid_entity_id` (validation) |
| `cdb_context_impact` | `{}` | `ok` |

None returned `not_implemented`.

## Wave-14 tools (bridge dispatch + source honesty)

| Tool | Forged caller `source` / `brain_*` | `metadata.source` | `metadata.read_only` | `not_implemented` |
|------|-----------------------------------|-------------------|----------------------|-------------------|
| `cdb_context_evidence_resolve` | `surrealdb-local` | `in_memory` | `true` | no |
| `cdb_context_claim_resolve` | forged | `in_memory` | `true` | no |
| `cdb_context_memory_get` | forged | `in_memory` | `true` | no |
| `cdb_context_trust_summary` | forged | `in_memory` | `true` | no |
| `cdb_context_decision_history` | forged | `in_memory` | `true` | no |
| `cdb_context_decision_replay` | forged | `in_memory` | `true` | no |

Source-claim guardrails hold: caller cannot spoof DB-backed mode without adapter evidence (#2638 path).
Real `surrealdb-local` proof remains scoped to opt-in local tests (#2639/#2649/#2650) — **not** re-run this slice.

## Read-only guard

| Check | Result |
|-------|--------|
| `context.search` + `INSERT INTO t` | `error` `forbidden_keyword` |
| `cdb_context_impact` + `operation_mode=write` | `error` `invalid_operation_mode` |
| Unit: `test_permission_guard.py` | green (200 selected in focused run) |

## Capability resolution (repo / bridge level)

| Level | Result |
|-------|--------|
| L1 `claire-de-binare.mcp.json` | present; `cdb_context` server entry enabled |
| L2 host config | `opencode.jsonc` references `cdb_context` (repo-tracked) |
| L3a `create_bridge()` | PASS — 26 tools |
| L3b `import tools.mcp.server` | PASS (stdio import OK this session) |
| L4 `context.briefing` in inventory | PASS |
| L5 `context.briefing` invocation | PASS (valid params) |
| `make context-doctor` | exit 1 — `context_query.local.yaml` missing; SurrealDB not reachable (expected without local config; no blocker for bridge-only smoke) |

## BLUE/RED (read-only)

26 BLUE/RED containers healthy; `cdb_surrealdb` not running (no runtime stack change).

## Unit validation (CI-mode, no containers)

```bash
pytest -m unit tests/unit/tools/mcp/test_context_bridge.py \
  tests/unit/tools/mcp/test_permission_guard.py \
  tests/unit/tools/mcp/test_mcp_wave14_tools.py \
  tests/unit/tools/mcp/test_mcp_wave14_surrealdb_mode.py \
  tests/unit/tools/mcp/test_wave14_query_contracts.py \
  tests/unit/surrealdb/test_context_onboarding_doctor.py
```

Focused MCP subset: **200 passed** (Wave-14 dispatch + permission guard + show_handlers + wave14 tools).

## Context (#2603 / #2604 / #2606)

- **#2603:** Runtime prerequisite for real DB; not exercised beyond doctor read-only check.
- **#2604:** CLI chain proven in Slice 2; #2679 literal-normalizer merged (#2680) — separate from MCP surface.
- **#2606:** Long-term memory epic; no memory-write in this slice.

## Follow-ups (epic remains open)

- Per-agent host L2/L5 still operator-dependent (Runbook §1.5 matrix).
- Wave-15–20: bundle/in-memory only; no real-SurrealDB proof path (unlike Wave-14).
- Opt-in `CDB_RUN_REAL_SURREALDB_SMOKE=1` local Wave-14 DB smoke not re-run (out of slice scope).
- `context-doctor` needs local `context_query.local.yaml` for full green preflight.

## Verdict

MCP agent surface **PASS** at bridge level for Slice 3. No code defect requiring PR.
**Status:** `DONE_NO_PR`. #2605 remains **open**.
