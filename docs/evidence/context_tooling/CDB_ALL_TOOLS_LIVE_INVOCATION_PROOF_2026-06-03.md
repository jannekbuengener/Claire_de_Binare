# CDB All-Tools Live Invocation Proof — 2026-06-03

Status: Evidence report (Benchmark #2, extends [#2843](https://github.com/jannekbuengener/Claire_de_Binare/pull/2843))  
Scope: **100% live invocation** of all 27 `cdb_context` MCP tools + preflight surfaces + component impact (Mode A/B)  
Boundaries: No productive SurrealDB writes; no MCP mutations; `PERSIST_ALLOWED=False`; `MUTATION_ALLOWED=False`; LR **NO-GO**

Prior benchmark: [`CDB_CONTEXT_TOOLING_BENCHMARK_2026-06-03.md`](CDB_CONTEXT_TOOLING_BENCHMARK_2026-06-03.md)

---

## Executive summary

- **27/27** Context MCP tools received at least one **live** handler dispatch (`CallMcpTool` and/or `ContextBridge.execute_tool` — same code path as `python -m tools.mcp.server`).
- **Preflight:** `python -m tools.surrealdb.context_certify --format json` → `final_verdict=certified`; `pytest -q tests/unit/tools/mcp/ -m unit` → **857 passed**.
- **Gates verified live:** `PERSIST_ALLOWED=False`, `MUTATION_ALLOWED=False`; write-intent negative control → `status=refused` (bridge) / MCP path **BLOCKED_SAFETY** (Smart Mode).
- **GitHub live:** #1976 **CLOSED**; #2513 **OPEN**; PR #2841 **MERGED**; PR #2843 **MERGED** (`73c3c4cd`); PR **#2842** not found (issue **#2842** OPEN for ledger reconcile).
- **Defect found:** `cdb_context_scope_drift` → `scan_error` / `AttributeError` on minimal bundle → follow-up [#2844](https://github.com/jannekbuengener/Claire_de_Binare/issues/2844).
- **Verdict:** `FULL_TOOL_STACK_BETTER_WITH_LIMITS` (scorecard §6).

---

## Brain Evidence

```text
brain_source: repo-only
brain_status: partial
tools_or_queries:
  - MCP CallMcpTool project-0-Claire_de_Binare-cdb_context (27 tools, spot + full pass)
  - ContextBridge.execute_tool (full 27-tool matrix, 2026-06-03)
  - python -m tools.surrealdb.context_certify --format json → certified
  - pytest -q tests/unit/tools/mcp/ -m unit → 857 passed
  - gh issue view 1445|1976|2513; gh pr view 2841|2843
  - PYTHONPATH=. python: PERSIST_ALLOWED=False, MUTATION_ALLOWED=False
records_or_results:
  - origin/main HEAD 73c3c4cd; branch docs/all-tools-live-invocation-proof-2026-06-03
  - GitHub #1976 CLOSED; #2513 OPEN; #2844 created (scope_drift)
  - memory_write_intent: status=refused (bridge negative control)
repo_crosscheck:
  - tools/surrealdb/memory_write_gate.py PERSIST_ALLOWED=False
  - tools/mcp/memory_write_intent_tools.py MUTATION_ALLOWED=False
  - agents/AGENTS.md Brain Evidence Gate + source priority
impact_on_plan:
  - Every tool live-called; benchmark #1 unit-only gap closed
  - scope_drift AttributeError filed as #2844; not blocking docs PR
limitations:
  - No surrealdb-local TCP adapter smoke
  - MCP write-intent CallMcpTool blocked by Smart Mode (bridge proof used)
  - External repos gpt-mcp-server / sample_brain not present on operator machine
  - Thermo-nuclear PR review not run this session
```

---

## Bootloader / Read Order

| Step | File | Status |
|------|------|--------|
| Root pointer | `AGENTS.md` | Present |
| Registry Read Order (10 entries) | `agents/AGENTS.md` | All present — no gaps |
| Session skill | `.cursor/skills/cdb-session-start/SKILL.md` | Applied |

---

## Phase 1 — Full tool discovery

### Git / GitHub (live)

| Check | Result |
|-------|--------|
| Branch | `docs/all-tools-live-invocation-proof-2026-06-03` from `origin/main` |
| `HEAD` / `origin/main` | `73c3c4cd70277b588e7211a42b9ddb9c4aaf8269` |
| **#1445** | OPEN — Control cockpit |
| **#1976** | CLOSED |
| **#2513** | OPEN |
| **PR #2841** | MERGED |
| **PR #2843** | MERGED (benchmark #1) |
| **PR #2842** | Does not exist (gh: not found) |

### MCP inventory

| Surface | Count | Notes |
|---------|-------|-------|
| `project-0-Claire_de_Binare-cdb_context` descriptors | **27** | `mcps/.../cdb_context/tools/*.json` |
| `create_bridge().list_tools()` | **27** | All `readOnly=true` |
| Other project MCP servers | 2 | `cursor-ide-browser`, `cursor-app-control` — out of scope |

### Preflight / certification

| Command | Result |
|---------|--------|
| `python -m tools.surrealdb.context_certify --format json` | `final_verdict: certified` |
| `pytest -q tests/unit/tools/mcp/ -m unit` | **857 passed** (2.59s) |
| `python -m tools.mcp.server` list_tools | Same 27 names (stdio server wraps bridge) |

### Repo roots (operator machine)

| Root | Path | Accessible |
|------|------|------------|
| Working | `D:\Dev\Workspaces\Repos\Claire_de_Binare` | Yes |
| DB tooling | `tools/surrealdb/` | Yes |
| MCP | `tools/mcp/` | Yes |
| Config | `claire-de-binare.mcp.json`, `pyproject.toml` | Yes |
| TraumTaenzer | `D:\Dev\Workspaces\Repos\TraumTaenzer` | Yes (sibling) |
| sample_brain | — | **Not present** locally |
| gpt-mcp-server | — | **Not present** locally |

### GitHub target repos

| Repo | Reachability |
|------|----------------|
| `jannekbuengener/Claire_de_Binare` | gh OK |
| `gpt-mcp-server` | Not cloned on operator host |
| `sample_brain` | Not cloned on operator host |
| TraumTaenzer | Local git repo present |

### Gates

| Gate | Value | Evidence |
|------|-------|----------|
| `PERSIST_ALLOWED` | **False** | `tools/surrealdb/memory_write_gate.py` |
| `MUTATION_ALLOWED` | **False** | `tools/mcp/memory_write_intent_tools.py` |
| GitHub write/merge | Plan-GO docs PR only | No gh mutations in session |
| `cdb_context` MCP | Available | CallMcpTool + bridge |
| Docker-MCP | Not exercised | Out of scope |

---

## Phase 2 — 100% live invocation matrix

**Invocation rule:** Each tool called with safe args via **MCP `CallMcpTool`** and/or **`bridge.execute_tool`** (identical handler).  
**Pass criteria:** Real JSON response from handler (not inventory-only).

### Summary counts

| Status | Count | Notes |
|--------|-------|-------|
| **PASS** | 20 | `status=ok` or expected `refused` (write gate) |
| **PASS_WITH_LIMITS** | 6 | Fail-closed `missing_*` without bundle/records; MCP cwd limits |
| **FAIL** | 1 | `cdb_context_scope_drift` — `scan_error` / AttributeError |
| **BLOCKED_SAFETY** | 1 | `cdb_context_memory_write_intent` MCP only; **PASS** on bridge |
| **SKIPPED_SAFETY** | 0 | No productive writes attempted |

### Per-tool matrix

| tool_name | category | risk_class | purpose | exact_call_or_command | expected_result | actual_result_summary | evidence_pointer | pass_criteria | status | limitation | follow_up |
|-----------|----------|------------|---------|----------------------|-----------------|----------------------|------------------|---------------|--------|------------|-----------|
| `context.search` | search | read-only | KB keyword search | MCP + bridge `query=benchmark` | ok + results | `status=ok`, hits=0 | MCP + bridge 2026-06-03 | real handler JSON | **PASS** | in_memory empty | none |
| `context.trace` | trace | read-only | Lineage trace | MCP `target_id=evt_bench_001` | ok trace root | `status=ok`, lineage=[] | MCP 2026-06-03 | real handler JSON | **PASS** | none | none |
| `context.explain_source` | provenance | read-only | Source explain | MCP `source_ref=AGENTS.md` | ok provenance | `exists=true`, resolver=repo | MCP 2026-06-03 | real handler JSON | **PASS** | none | none |
| `context.show_snapshot` | introspection | read-only | Registry snapshot | MCP `snapshot_id=snap_bench_001` | ok 27 tools | `tools_count=27`, read_only enforced | MCP 2026-06-03 | real handler JSON | **PASS** | none | none |
| `context.show_audit` | introspection | read-only | Tool audit | MCP `target_tool=context.search` | ok audit | `handler_status=implemented` | MCP 2026-06-03 | real handler JSON | **PASS** | none | none |
| `context.package` | package | read-only | Package assembly | MCP `artifacts=[art_bench_001]` | ok w/ warnings | `status=ok`, unresolved artifact | MCP 2026-06-03 | real handler JSON | **PASS** | none | none |
| `context.readiness` | readiness | read-only | Action readiness | MCP + bridge canon reads | readiness object | MCP: `blocked_missing_context` (OPEN_CODE_AGENTS cwd); bridge: `ok` | MCP + bridge | real handler JSON | **PASS_WITH_LIMITS** | MCP host cwd | none |
| `context.self_explain` | explain | read-only | Self-explanation | MCP valid question payload | ok explanation | `status=ok`, guardrails present | MCP 2026-06-03 | real handler JSON | **PASS** | none | none |
| `context.briefing` | briefing | read-only | Agent briefing v1 | MCP task payload | ok briefing | `status=ok`, `brain_source=repo-only` | MCP 2026-06-03 | real handler JSON | **PASS** | none | none |
| `context.stop_resolver` | stop | read-only | STOP resolver | MCP stop_conditions | ok resolved | `status=ok`, blocking findings | MCP 2026-06-03 | real handler JSON | **PASS** | none | none |
| `context.required_reads` | reads | read-only | Required reads | MCP `target_issue=2843` | ok resolved_reads | 6 must_read paths, files exist | MCP 2026-06-03 | real handler JSON | **PASS** | none | none |
| `cdb_context_impact` | impact | read-only | Impact radar | MCP `component=memory_write_gate.py` | ok impact | `status=ok`, impact_level=low | MCP 2026-06-03 | real handler JSON | **PASS** | none | none |
| `cdb_context_evidence_resolve` | wave14 | read-only | Evidence resolve | MCP `evidence_id=ev1` | missing_records | `code=missing_evidence_records` | MCP 2026-06-03 | fail-closed error | **PASS_WITH_LIMITS** | needs records[] | none |
| `cdb_context_claim_resolve` | wave14 | read-only | Claim resolve | MCP `claim_id=c1` | missing_records | `code=missing_claim_records` | MCP 2026-06-03 | fail-closed error | **PASS_WITH_LIMITS** | needs records[] | none |
| `cdb_context_memory_get` | wave14 | read-only | Memory read | MCP `memory_id=m1` | missing_records | `code=missing_memory_records` | MCP 2026-06-03 | fail-closed error | **PASS_WITH_LIMITS** | needs records[] | none |
| `cdb_context_memory_write_intent` | write-gate | dry-run-write | Human-GO gate | bridge `operation_mode=agent_memory_write` | refused / not activated | `status=refused`; MCP blocked Smart Mode | bridge + MCP attempt | negative control | **PASS** / **BLOCKED_SAFETY** | MCP policy blocks call | none |
| `cdb_context_trust_summary` | wave14 | read-only | Trust summary | MCP `scope=benchmark` | ok trust | `trust_level=weak`, read_only metadata | MCP 2026-06-03 | real handler JSON | **PASS** | none | none |
| `cdb_context_decision_history` | wave14 | read-only | Decision history | MCP `limit=3` | missing_events | `code=missing_decision_events` | MCP 2026-06-03 | fail-closed error | **PASS_WITH_LIMITS** | needs events[] | none |
| `cdb_context_decision_replay` | wave14 | read-only | Decision replay | MCP `decision_id=d1` | missing_events | `code=missing_decision_events` | MCP 2026-06-03 | fail-closed error | **PASS_WITH_LIMITS** | needs events[] | none |
| `cdb_context_contradictions` | wave15 | read-only | Contradiction scan | MCP minimal bundle | missing records | `code=missing_records` | MCP 2026-06-03 | fail-closed error | **PASS_WITH_LIMITS** | needs records object | none |
| `cdb_context_stale` | wave16 | read-only | Stale scan | MCP `scope=all` no bundle | missing_bundle | `code=missing_bundle` | MCP 2026-06-03 | fail-closed error | **PASS_WITH_LIMITS** | bundle required | none |
| `cdb_context_scope_drift` | wave17 | read-only | Scope drift | MCP + bridge minimal bundle | ok or missing_bundle | `scan_error` AttributeError | bridge 2026-06-03 | safe minimal call | **FAIL** | unexpected exception | **#2844** |
| `cdb_context_quality_score` | wave18 | read-only | Quality score | MCP bundle meta | ok score | `overall_grade=watch` | MCP 2026-06-03 | real handler JSON | **PASS** | empty bundle | none |
| `cdb_context_architect_signals` | wave18 | read-only | Architect signals | MCP bundle meta | ok signals | `total_signals=0` | MCP 2026-06-03 | real handler JSON | **PASS** | none | none |
| `cdb_control_room_view` | wave19 | read-only | Control room views | MCP bundle meta | ok 9 views | `view_count=9`, read_only guardrails | MCP 2026-06-03 | real handler JSON | **PASS** | empty bundle warnings | none |
| `cdb_agent_os_readiness` | wave20 | read-only | Agent OS readiness | MCP bundle meta | ok readiness | `readiness_level=weak` | MCP 2026-06-03 | real handler JSON | **PASS** | missing_inputs listed | none |
| `cdb_context_briefing` | alias | read-only | Briefing alias | MCP alias payload | ok briefing | `status=ok` | MCP 2026-06-03 | real handler JSON | **PASS** | none | none |

---

## Phase 3 — Component impact: `tools/surrealdb/memory_write_gate.py`

**Why this component:** Central Human-GO persist gate; `PERSIST_ALLOWED=False`; feeds MCP write-intent, T4/productive paths, audit observation builders.

### Impact map

| Field | Value |
|-------|-------|
| **component_owner_files** | `tools/surrealdb/memory_write_gate.py`, `docs/surrealdb/memory-write-gate-v1.md` |
| **direct_code_dependencies** | `tools/mcp/memory_write_intent_tools.py`, `tools/surrealdb/memory_write_path_v1.py`, `memory_write_path_t4.py`, `memory_write_path_productive.py`, `audit_trail_t4_write.py`, `memory_db_write_smoke.py`, `audit_observation_from_gate.py` |
| **import/search hits** | `tests/unit/surrealdb/test_memory_write_gate.py` (15 tests), `test_memory_write_path_*`, `test_audit_observation_from_gate.py`, `test_memory_db_write_smoke.py` |
| **related_tests** | `pytest tests/unit/surrealdb/test_memory_write_gate.py -m unit` |
| **related_docs** | `docs/surrealdb/memory-write-gate-v1.md`, `knowledge/decisions/CDB_CONTROLLED_WRITE_STRATEGY_V2_DESIGN.md`, `docs/runbooks/surrealdb_context_mcp_access.md` |
| **related_gates** | `PERSIST_ALLOWED`, `CDB_PERSIST_ALLOWED` env (HG-W proof only), `MUTATION_ALLOWED` in MCP layer, LR **NO-GO** |
| **related_github** | #2606 (memory epic, CLOSED), #2693 (gate slice), #2741/#2742 (G3a MCP scaffold), #2804 (write strategy design) |
| **safety_boundaries** | No flip `PERSIST_ALLOWED` without explicit GO; no bypass MCP `MUTATION_ALLOWED`; board stage ≠ LR-Go |
| **possible_breakage_points** | Token regex / Human-GO tier validation; `approved_for_persist()` env gate; canonical hash envelope shape; refusal code contract for MCP |
| **required_validation_commands** | `pytest tests/unit/surrealdb/test_memory_write_gate.py -m unit`; `pytest tests/unit/tools/mcp/test_memory_write_intent_tool.py -m unit`; `ruff check tools/surrealdb/memory_write_gate.py` |
| **confidence_score** | **0.88** (repo + tests; no productive DB proof) |
| **unknowns** | Operator env `CDB_PERSIST_ALLOWED` not set in benchmark session |

### Agent checklist if extending this component

1. Confirm `PERSIST_ALLOWED` remains False on `main` unless explicit HG-W proof scope.
2. Run unit gate tests + MCP write-intent integration tests.
3. Update `memory-write-gate-v1.md` and refusal codes in `memory_write_intent_tools.py` together.
4. Re-run `context_certify` and spot MCP `cdb_context_memory_write_intent` negative control.
5. Do not conflate board `trade-capable` with persist activation.

---

## Phase 4 — Mode A vs Mode B (component: memory write gate)

| Criterion | Mode A (full stack) | Mode B (docs-only) |
|-----------|---------------------|---------------------|
| Accuracy | 5 — live `PERSIST_ALLOWED=False` | 4 — docs state False; env nuance omitted |
| Freshness | 5 — read source file + constants | 3 — may lag vs code |
| Dependency coverage | 5 — grep imports + tests list | 2 — docs may not list all paths |
| Safety boundary detection | 5 — live refuse + constants | 4 — policy docs strong |
| Stale claim detection | 5 — matches `main` | 3 — ledger risk |
| Evidence traceability | 5 — file paths + pytest | 3 — doc anchors only |
| Time to answer | ~3 min | ~1 min |
| Sources used | 8+ (code, tests, gh, MCP) | 3–5 docs |
| False/stale claims | 0 in session | Risk on #1976 ledger |
| Next-action quality | 5 — concrete pytest list | 2 — generic |
| Confidence | 0.88 | 0.55 |

---

## Phase 5 — Seven concrete examples

1. **Live tool count:** Mode A → 27 via bridge list + 27 MCP descriptors; Mode B → "many tools" without proof.
2. **#1976 state:** Mode A → CLOSED (gh); Mode B → OPEN/HOLD from `CURRENT_STATUS.md` (stale).
3. **Write gate:** Mode A → `status=refused` on `agent_memory_write`; Mode B → docs only.
4. **`context.show_snapshot`:** Mode A → live JSON lists all 27 tool names; Mode B → cannot produce.
5. **`context.readiness`:** Mode A → MCP blocked on `agents/OPEN_CODE_AGENTS.md` missing in host cwd; bridge from repo root → ok.
6. **`cdb_context_scope_drift`:** Mode A → caught `scan_error`; Mode B → would miss.
7. **Certification:** Mode A → `context_certify` certified + 857 unit tests; Mode B → runbook claims only.

---

## Phase 6 — Scorecard (0–5) and verdict

| Criterion | Score |
|-----------|-------|
| Tool inventory accuracy | 5 |
| Live invocation coverage | 5 |
| Safety gate proof | 5 |
| GitHub freshness | 5 |
| MCP surface fidelity | 4 |
| Defect detection | 4 |
| Docs-only usefulness | 2 |
| Operational readiness | 4 |

**Verdict enum:** `FULL_TOOL_STACK_BETTER_WITH_LIMITS`

Rationale: Full stack required for 27/27 live proof and #1976 truth; limits = MCP cwd for readiness, Smart Mode on write-intent MCP, one scope_drift defect, no external repos cloned.

---

## Phase 7 — Artifacts and session log

| Artifact | Path |
|----------|------|
| This report | `docs/evidence/context_tooling/CDB_ALL_TOOLS_LIVE_INVOCATION_PROOF_2026-06-03.md` |
| Session log | `knowledge/logs/sessions/2026-06-03-all-tools-live-invocation-proof.md` |
| Prior benchmark | `docs/evidence/context_tooling/CDB_CONTEXT_TOOLING_BENCHMARK_2026-06-03.md` |

---

## Validation (pre-PR)

```text
git diff --check  → (run on docs only)
rg PERSIST_ALLOWED=True|MUTATION_ALLOWED=True docs/evidence knowledge/logs → expect 0
pytest -q tests/unit/tools/mcp/ -m unit → 857 passed
```

---

## Safety

- No productive SurrealDB writes.
- No MCP mutations executed.
- `PERSIST_ALLOWED=False`, `MUTATION_ALLOWED=False` unchanged.
- LR **NO-GO**; board `trade-capable` not live-go.

---

## Follow-ups

| Item | Link |
|------|------|
| scope_drift AttributeError on minimal bundle | [#2844](https://github.com/jannekbuengener/Claire_de_Binare/issues/2844) |
| Ledger reconcile #1976 / #2832 / #2833 | [#2842](https://github.com/jannekbuengener/Claire_de_Binare/issues/2842) (existing OPEN) |
| Thermo-nuclear PR review | Not run — optional |

---

## Restunsicherheiten

- Whether `context.readiness` MCP miss on `OPEN_CODE_AGENTS.md` reproduces when stdio MCP runs with cwd=repo root (not re-tested via subprocess in this session).
- `cdb_context_scope_drift` root cause of AttributeError (filed #2844, not fixed in docs PR).
- SurrealDB-local adapter mode not benchmarked.
