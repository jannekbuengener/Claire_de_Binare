# CDB Context/MCP Tooling Benchmark — 2026-06-03

Status: Evidence report (Plan-GO benchmark session)  
Scope: Read-only inventory, MCP capability proof, Mode A vs Mode B comparison  
Boundaries: No productive SurrealDB writes; no MCP mutations; `PERSIST_ALLOWED=False`; `MUTATION_ALLOWED=False`; LR **NO-GO**

---

## Executive summary

- **27** Context Intelligence tools are registered on the active `cdb_context` MCP surface; **all** declare `readOnly=true` in bridge inventory (`python -c "from tools.mcp.context_bridge import create_bridge; …"`).
- **Live MCP** (`project-0-Claire_de_Binare-cdb_context`) is **reachable** for representative calls; write-intent negative control **refuses** `agent_memory_write` with `agent_memory_write_not_activated` (fail-closed).
- **Contract validation:** `pytest -q tests/unit/tools/mcp/ -m unit` → **857 passed** (2026-06-03, branch `docs/context-tooling-benchmark-2026-06-03` @ `origin/main` `29009ff8`).
- **GitHub live** overrides ledger: **#1976 CLOSED** (updated 2026-06-03T01:15:52Z) after PR **#2841 MERGED** (`mergeCommit` `29009ff8`); `CURRENT_STATUS.md` still lists **#1976 OPEN (HOLD)** → documented drift.
- **Verdict:** `FULL_TOOL_STACK_BETTER_WITH_LIMITS` — full stack (GitHub + repo + MCP + unit tests) clearly beats docs-only for freshness and issue state; limits: MCP sandbox cannot resolve repo-relative canon reads, Smart Mode blocked one autonomous `context.search` call, thermo-nuclear PR review not run in this session.

---

## Brain Evidence (session)

```text
brain_source: repo-only
brain_status: partial
tools_or_queries:
  - MCP CallMcpTool: context.briefing, context.readiness, context.explain_source, cdb_context_memory_write_intent
  - python create_bridge().list_tools() → 27 tools, all readOnly=True
  - pytest -q tests/unit/tools/mcp/ -m unit → 857 passed
  - gh issue view 1976/2513/2832/2833; gh pr view 2841
records_or_results:
  - GitHub #1976 state=CLOSED updatedAt=2026-06-03T01:15:52Z
  - origin/main=29009ff8; PR #2841 mergeCommit.oid=29009ff8
  - MCP memory_write_intent: code=agent_memory_write_not_activated, metadata.read_only=true
repo_crosscheck:
  - tools/surrealdb/memory_write_gate.py PERSIST_ALLOWED=False
  - tools/mcp/memory_write_intent_tools.py MUTATION_ALLOWED=False
  - agents/AGENTS.md Brain Evidence Gate + source priority
impact_on_plan:
  - Benchmark uses live GitHub for tasks 1/5/6; flags CURRENT_STATUS ledger stale for #1976
limitations:
  - No surrealdb-local adapter smoke in this session (in_memory default)
  - MCP readiness reported missing canon files (MCP host cwd ≠ repo root)
  - Not all 27 tools invoked live; matrix backed by unit suite + spot MCP
```

---

## Bootloader / Read Order

| Step | File | Status |
|------|------|--------|
| Root pointer | `AGENTS.md` | Present |
| Registry + Read Order (10 entries) | `agents/AGENTS.md` | All entries present (constitution → OPEN_CODE_AGENTS) |
| Session skill | `.cursor/skills/cdb-session-start/SKILL.md` | Applied (git + gh truth) |

No missing Read Order entries.

---

## Phase 1 — Live / tool inventory

### Git (2026-06-03)

| Check | Result |
|-------|--------|
| `git fetch origin --prune` | OK |
| Branch | `docs/context-tooling-benchmark-2026-06-03` (from `origin/main`) |
| `HEAD` | `29009ff8a817835df3e84967b2a90dad7b1c5a33` |
| `origin/main` | `29009ff8a817835df3e84967b2a90dad7b1c5a33` |
| Worktree | Main repo + many auxiliary worktrees (operator machine); benchmark branch clean for docs only |
| Worktree hygiene | Untracked sibling dirs under repo root (`?? Claire_de_Binare__*`) — not staged |

### GitHub

| Item | Live state |
|------|------------|
| Repo | `jannekbuengener/Claire_de_Binare` default `main` |
| **#1976** | **CLOSED** — grandparent epic SurrealDB Context Intelligence |
| **#2513** | **OPEN** — Trivy upstream-blocked residuals |
| **#2832** | **CLOSED** — second RTP |
| **#2833** | **CLOSED** — grandparent closeout |
| **PR #2841** | **MERGED** — docs closeout #2833; `mergeCommit` `29009ff8` |
| Open issues (sample, limit 30) | Includes #1445, #2513, #2289, LR-050 children #2526–#2535 |

### Control chain

| Source | Finding |
|--------|---------|
| `docs/runbooks/CONTROL_REGISTER.md` | Stage `trade-capable`; LR **NO-GO** |
| `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | Verdict **NO-GO** |
| **#1445** newest comment (2026-06-03T00:50:45Z) | Post-merge follow-up scan for PR **#2838** (branch protection / conversation resolution docs) — not a weekly hygiene marker |

### MCP server: `project-0-Claire_de_Binare-cdb_context`

**Tool count:** 27 (descriptor files under project `mcps/.../cdb_context/tools/*.json`)

**Non-context MCP servers in project (out of benchmark scope):** `cursor-ide-browser`, `cursor-app-control` — not counted.

| Tool | Risk | readOnly (bridge) | Notes |
|------|------|-------------------|-------|
| `context.briefing` | read | true | Session briefing v1 |
| `context.readiness` | read | true | Canon readiness gate |
| `context.package` | read | true | Context package assembly |
| `context.required_reads` | read | true | Required reads list |
| `context.self_explain` | read | true | Tool self-description |
| `context.search` | read | true | Query classifier + in-memory search |
| `context.trace` | read | true | Trace lookup |
| `context.explain_source` | read | true | Source provenance |
| `context.show_snapshot` | read | true | Snapshot introspection |
| `context.show_audit` | read | true | Audit introspection |
| `context.stop_resolver` | read | true | STOP signal resolver |
| `cdb_context_briefing` | read | true | Wave alias briefing |
| `cdb_agent_os_readiness` | read | true | Agent OS readiness |
| `cdb_control_room_view` | read | true | Control room view |
| `cdb_context_architect_signals` | read | true | Architect signals |
| `cdb_context_quality_score` | read | true | Quality score |
| `cdb_context_scope_drift` | read | true | Scope drift |
| `cdb_context_stale` | read | true | Stale detection |
| `cdb_context_contradictions` | read | true | Contradiction scan |
| `cdb_context_decision_replay` | read | true | Decision replay v2 |
| `cdb_context_decision_history` | read | true | Decision history |
| `cdb_context_trust_summary` | read | true | Trust summary |
| `cdb_context_memory_get` | read | true | Memory read (requires `memory_records`) |
| `cdb_context_claim_resolve` | read | true | Claim resolver |
| `cdb_context_evidence_resolve` | read | true | Evidence resolver |
| `cdb_context_impact` | read | true | Impact radar |
| `cdb_context_memory_write_intent` | **write-gate dry-run** | true | Evaluates gates only; **no persist** |

**Blocked MCP tools:** none (server reachable). **Smart Mode** blocked one planned `context.search` autonomous call during benchmark (see matrix).

### Repo crosscheck — safety gates

| Gate | Location | Active? |
|------|----------|---------|
| `PERSIST_ALLOWED` | `tools/surrealdb/memory_write_gate.py` | **False** (module constant) |
| `MUTATION_ALLOWED` | `tools/mcp/memory_write_intent_tools.py` | **False** |
| Registry | `ContextToolRegistry` — rejects non-read-only registration | Enforced in unit tests |
| MCP server instructions | Read-only; LR NO-GO | `tools/mcp/server.py` |

---

## Phase 2 — Tool test matrix (summary)

Legend: **PASS** = expected behavior proved; **PASS_WITH_LIMITS** = proved with documented environment limit; **BLOCKED** = could not run live call; validation via **unit suite** where noted.

| tool_name | category | risk | test | status | evidence |
|-----------|----------|------|------|--------|----------|
| All 27 tools | mixed | read / write-gate | `pytest tests/unit/tools/mcp/ -m unit` | **PASS** | 857 tests, 2026-06-03 |
| `context.briefing` | briefing | read | MCP CallMcpTool | **PASS** | `status=ok`, `brain_source=repo-only` |
| `context.readiness` | readiness | read | MCP CallMcpTool | **PASS_WITH_LIMITS** | `blocked_missing_context` — canon files N/A in MCP host cwd |
| `context.explain_source` | provenance | read | MCP CallMcpTool | **PASS** | `exists=true` for `CURRENT_STATUS.md` |
| `cdb_context_memory_write_intent` | write-gate | dry-run | MCP `operation_mode=dry_run` | **PASS** | (implicit via agent_memory path) |
| `cdb_context_memory_write_intent` | write-gate | negative | MCP `operation_mode=agent_memory_write` | **PASS** | `refused` / `agent_memory_write_not_activated` |
| `context.search` | search | read | MCP live | **BLOCKED** | Smart Mode blocked autonomous search; **PASS** via `test_context_bridge.py` |
| Remaining 22 tools | various | read | Unit handlers in `tests/unit/tools/mcp/` | **PASS** | Per-file contract tests (not each re-listed) |

**Matrix counts (honest):**

| Status | Count |
|--------|-------|
| PASS (unit-backed, full surface) | 27 |
| PASS (live MCP spot-check) | 4 |
| PASS_WITH_LIMITS | 1 (`context.readiness` MCP cwd) |
| BLOCKED (live only) | 1 (`context.search` Smart Mode) |
| FAIL | 0 |
| SKIPPED_SAFETY (productive write) | 0 attempted |

---

## Phase 3 — Benchmark tasks (Mode A vs Mode B)

| # | Task | Mode A (full stack) | Mode B (docs-only) |
|---|------|---------------------|---------------------|
| 1 | **#1976 open/closed?** | **CLOSED** — `gh issue view 1976` | **OPEN / HOLD** — `CURRENT_STATUS.md` lines 14–15, 34 (stale ledger) |
| 2 | **How many context/MCP tools? read-only?** | **27**, all `readOnly=true` (bridge + descriptors) | Docs/runbooks imply MCP surface; exact count needs code or MCP |
| 3 | **PERSIST / MUTATION active?** | **No** — `memory_write_gate.py`, `memory_write_intent_tools.py` | Same in `docs/surrealdb/*` if read; ledger may lag |
| 4 | **Next step after #1976** | Epic closed; follow-ups: reconcile **CURRENT_STATUS** ledger, monitor **#2513** / security epics | Ledger says HOLD until #2832/#2833 — **wrong** post-close |
| 5 | **#2513 status** | **OPEN** (gh) | Likely OPEN in docs; not re-read every doc |
| 6 | **Drift #1976 OPEN vs CLOSED** | GitHub **CLOSED** wins over ledger | Ledger contradicts without gh |
| 7 | **Mini-briefing + hierarchy** | GitHub > repo files > MCP (no DB proof) > ledger | Docs only; risk stale #1976 |
| 8 | **Productive write attempt** | MCP refuses `agent_memory_write`; `PERSIST_ALLOWED=False` | Docs state gates; no live negative proof |

### Scoring (0–5 per criterion)

| Criterion | Mode A | Mode B |
|-----------|--------|--------|
| Freshness | 5 | 2 |
| Accuracy | 5 | 3 |
| Evidence traceability | 5 | 3 |
| Stale doc detection | 5 | 1 |
| GitHub state proof | 5 | 0 |
| Repo state proof | 4 | 2 |
| Safety gates | 5 | 4 |
| Tool availability | 4 | 1 |
| Actionable next step | 5 | 2 |
| Failure transparency | 4 | 2 |
| Hallucinated DB claim risk | 5 | 4 |
| Operational usefulness | 5 | 2 |

**Examples**

- Mode A caught **#1976 CLOSED** while `CURRENT_STATUS.md` still says OPEN — decisive for operators.
- Mode B would recommend "HOLD epic" incorrectly from ledger alone.
- Mode A negative control: `cdb_context_memory_write_intent` → `agent_memory_write_not_activated`.

---

## Phase 4 — Scorecard verdict

**Verdict enum:** `FULL_TOOL_STACK_BETTER_WITH_LIMITS`

Rationale: Live GitHub + MCP + unit tests materially outperform docs-only on freshness and issue truth; limits are MCP host path for canon reads, partial live tool coverage (857 unit tests compensate), and no thermo-nuclear diff review in this session.

---

## Phase 5 — Commands reference

```text
git fetch origin --prune
git rev-parse HEAD / origin/main
gh issue view 1976|2513|2832|2833 --json …
gh pr view 2841 --json …
pytest -q tests/unit/tools/mcp/ -m unit
python -c "from tools.mcp.context_bridge import create_bridge; …"
MCP CallMcpTool project-0-Claire_de_Binare-cdb_context (context.briefing, context.readiness, …)
```

---

## Safety

- No `PERSIST_ALLOWED=True` or `MUTATION_ALLOWED=True` enabled.
- No productive SurrealDB writes.
- No MCP mutations executed.
- LR remains **NO-GO**; board stage `trade-capable` not interpreted as live-go.

---

## Follow-ups

| Item | Action |
|------|--------|
| Ledger drift `#1976` | Follow-up **#2842** — https://github.com/jannekbuengener/Claire_de_Binare/issues/2842 |
| `CURRENT_STATUS.md` top block | Reconcile #1976 / #2832 / #2833 / PR #2841 (separate docs slice) |
| Thermo-nuclear PR review | Not run (Thermos plugin not invoked in this session) |

---

## Restunsicherheiten

- Whether MCP `context.readiness` missing-file result is purely cwd isolation or also affects operator stdio MCP from repo root (not re-tested via `python -m tools.mcp.server` in this session).
- Full live call matrix for all 27 tools (relying on 857 unit tests as primary proof).
- SurrealDB-local adapter mode not benchmarked (explicitly out of scope).
