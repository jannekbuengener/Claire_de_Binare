# SurrealDB Pre-Phase-2 Documentation Canon Audit

| Field | Value |
| --- | --- |
| **Issue** | [#2780](https://github.com/jannekbuengener/Claire_de_Binare/issues/2780) |
| **Epic gate** | [#2778](https://github.com/jannekbuengener/Claire_de_Binare/issues/2778) G8 Entry Gate |
| **Parent** | [#1976](https://github.com/jannekbuengener/Claire_de_Binare/issues/1976) |
| **Repo SHA** | `4f220eaaae797133ac2f16fb1e6a830772aefc95` |
| **Audit date** | 2026-06-02 |
| **Auditor** | cdb-docs-canon-maintainer (Cursor) |
| **Decision** | **PASS_WITH_DEFERRED_EXIT_ITEMS** |

---

## Scope

Pre-Phase-2 documentation canon validation for SurrealDB / Context Intelligence /
Memory / MCP / CLI surfaces. **Docs and minimal reconcile only** — no runtime,
no DB writes, no Phase-2 implementation, no LR change.

**In scope paths:**

- `docs/surrealdb/` (81 files)
- `docs/runbooks/surrealdb_*`, `SURREALDB_LOCAL_CONTEXT_RUNTIME.md`
- `knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`
- `agents/AGENTS.md`, `agents/roles/*.md`, `.cursor/agents/cdb-*.md` (pointers)
- `CURRENT_STATUS.md` (ledger cross-check only)
- Session logs under `knowledge/logs/sessions/` (historical evidence, not canon)

**Out of scope:** `docs/archive/**`, code changes, MCP/CLI implementation, post-Phase-2 exit reconciliation (separate #2780 exit deliverable before #2778 close).

---

## Live Evidence (GitHub)

Verified via `gh issue view` / `gh pr list` on 2026-06-02.

| Issue | Live state | Expected by #2780 brief |
| --- | --- | --- |
| #2603 | **CLOSED** | closed |
| #2604 | **CLOSED** | closed |
| #2605 | **CLOSED** | closed |
| #2606 | **CLOSED** | closed |
| #2689 | **CLOSED** | closed |
| #2773 | **CLOSED** | closed |
| #2774 | **CLOSED** | closed |
| #2775 | **CLOSED** | closed |
| #2776 | **CLOSED** | closed |
| #2777 | **OPEN** | open |
| #2778 | **OPEN** (PARKED/BLOCKED) | open, parked |
| #2780 | **OPEN** | open (this audit) |
| #2781 | **OPEN** | open |
| #1976 | **OPEN** | open (parent epic) |

**Recent merged PRs (context slice):** #2784, #2786, #2789, #2792, #2793, #2788 — merged on `main` at audit SHA.

**Open PRs:** none blocking SurrealDB canon at audit time (`gh pr list --state open --limit 30`).

---

## Safety Boundary (summary)

| Check | Result |
| --- | --- |
| Active docs imply Live-Go / Echtgeld-Go | **No** — wave/runbook docs state LR **NO-GO** or deny Echtgeld-Go |
| `PERSIST_ALLOWED=True` / `MUTATION_ALLOWED=True` as default in active `docs/surrealdb` | **No** — only negations or “not on main” |
| Trading state in SurrealDB as SSoT | **No** — `context-intelligence-system.md` forbids |
| Gordon / Docker AI as operational gate | **No** in active runbooks; `reports/GORDON_*.md` marked orphaned/historical (#2689/#2793) |
| MCP tool count in operator runbook | **27** — matches `create_bridge().list_tools()` |
| `make context-certify` (default) | **certified**, LR NO-GO, gates False |

**LR SSOT:** [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../live-readiness/LR-AUDIT-STATUS-2026-03-05.md) — **NO-GO** (unchanged).

---

## Inventory Table (surfaces)

| Surface | Count / path | Role |
| --- | --- | --- |
| `docs/surrealdb/` | 81 files | Primary canon + design + wave gates |
| `docs/runbooks/` (context) | 5 files | Operator runbooks |
| `knowledge/decisions/` | `CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md` | Governance decision #2775 |
| `tools/mcp/context_bridge.py` | 27 tools | Live MCP inventory |
| `Makefile` | `context-*`, `context-certify`, `context-doctor` | Operator entrypoints |
| `reports/GORDON_*.md` | 3+ files | **Historical** (#2689) |
| `knowledge/logs/sessions/*surreal*` | ~25 files | Session evidence (historical) |

Full per-file classification: see [Classification Table](#classification-table) below.

---

## Classification Table

### Tier A — Canonical (operator + architecture)

| File | Class |
| --- | --- |
| `docs/surrealdb/context-intelligence-system.md` | canonical |
| `docs/surrealdb/context-mcp-bridge-contract.md` | canonical |
| `docs/surrealdb/local-context-runtime-contract.md` | canonical |
| `docs/surrealdb/data-ownership-matrix.md` | canonical |
| `docs/surrealdb/context-intelligence-namespace-layout.md` | canonical |
| `docs/runbooks/surrealdb_context_mcp_access.md` | runbook (canonical operator) |
| `docs/runbooks/surrealdb_context_query.md` | runbook |
| `docs/runbooks/surrealdb_context_import.md` | runbook |
| `docs/runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md` | runbook |
| `docs/runbooks/surrealdb_append_only_enforcement.md` | runbook |
| `knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md` | canonical (governance) |
| `agents/AGENTS.md` (Brain Evidence + MCP notes) | canonical pointer |

### Tier B — Runbooks / contracts (specialized)

All `*-runbook.md`, `*-contract*.md`, `context-*-contract*.md`, `memory-write-gate-v1.md`, `decision_replay_query_contract.md`, `context-importer-cli-contract.md`, `context-indexer-cli-contract.md`, wave operator runbooks (e.g. `context-wave19-control-room-runbook.md`) → **runbook** or **canonical contract** (subset).

### Tier C — Design / gated future (not activated)

| Pattern | Class |
| --- | --- |
| `productive-memory-audit-trail-*.md`, `mcp-memory-write-surface-v1.md`, `memory-write-path-t4-runbook-v1.md` | design |
| `productive-memory-audit-trail-mcp-phase2-design-v1.md` | design |
| `dual-write-mirror-strategy.md`, `rollback-cutover-plan.md` | design |
| Wave completion gates `context-wave*-completion-gates.md`, `wave16-completion-gates.md` | historical checkpoint |

### Tier D — Historical / archive candidate

| Pattern | Class |
| --- | --- |
| `context-pr-slicing-plan.md`, early wave gates (wave7–14) | historical |
| `docs/surrealdb/context-intelligence/external-reference-scan.md` | historical scan |
| `reports/GORDON_*.md`, `reports/EXECUTION_QUEUE.md` (Gordon refs) | historical (bannered) |
| `knowledge/logs/sessions/2026-05-*` | historical evidence |

**Note:** 81 files under `docs/surrealdb/` are predominantly **runbook**, **design**, or **historical wave gates**; only ~10 files are day-to-day **canonical** planning inputs for Phase 2.

---

## Contradiction Matrix

| ID | File / statement | Live evidence | Status | Required fix |
| --- | --- | --- | --- | --- |
| C1 | `productive-memory-audit-trail-v1.md` header: parent #2606 **(stays OPEN)** | `gh`: #2606 **CLOSED** | **fixed** | Reconcile header (this PR) |
| C2 | Same pattern in `productive-memory-audit-trail-mcp-phase2-design-v1.md`, `productive-memory-audit-trail-endpoint-design-v1.md`, `db-runtime-ci-proof-path-v1.md`, `cross-session-memory-rediscovery-v1.md`, `claim-evidence-at-rest-v1.md` | #2606 CLOSED | **fixed** | Reconcile headers |
| C3 | `memory-reality-slice1-audit.md` § addendum: "Epic #2606 remains OPEN" | #2606 CLOSED; same doc later says CLOSED | **fixed** | Single line reconcile |
| C4 | `productive-memory-audit-trail-endpoint-design-v1.md` table: "#2606 Stays OPEN" | CLOSED | **fixed** | Table row |
| C5 | `knowledge/logs/sessions/2026-05-29-2605-mcp-agent-surface-smoke-slice3.md`: **26 tools** | Bridge now **27** (`cdb_context_memory_write_intent`) | **deferred** | Historical session log; runbook documents delta |
| C6 | `surrealdb_context_mcp_access.md` status **Draft** | Substance matches merged main + certification | **deferred** | Promote to Active in post-Phase-2 or follow-up doc issue |
| C7 | Wave `*-completion-gates.md` OPEN issue checklists | Many child issues now CLOSED | **deferred** | Mark wave gates historical; do not use as live issue tracker |
| C8 | `CURRENT_STATUS.md` vs GitHub | Ledger; may lag merges | **acceptable** | Treat as ledger only (per canon) |
| C9 | `context-agent-handoff.md` generic `state = OPEN` | Template example, not issue claim | **no fix** | Clarified in audit |
| C10 | Gordon in `services/execution/EXECUTION_SERVICE_STATUS.md` | Historical note present | **deferred** | Out of surrealdb path; #2689 closed |

**No contradiction found** implying Live-Go, default `PERSIST_ALLOWED=True`, or default `MUTATION_ALLOWED=True` in active `docs/surrealdb/`.

---

## Required Fixes

| Priority | Item | Owner |
| --- | --- | --- |
| P0 (this PR) | C1–C4 #2606 OPEN → CLOSED reconcile in design doc headers | #2780 |
| P1 (deferred) | Wave completion gate docs → banner "historical checkpoint" | Post-Phase-2 or #2777 |
| P1 (deferred) | MCP runbook status Draft → Active after #2778 scope | #2778 exit gate |
| P2 (deferred) | Post-Phase-2 full doc reconciliation (#2780 exit) | Before #2778 close |

---

## Fixes Applied (this delivery)

1. Reconciled **#2606 parent state** from `(stays OPEN)` to `(CLOSED 2026-05-31; design/historical)` in six `docs/surrealdb/` files (see git diff).
2. Added this audit report at `docs/surrealdb/SURREALDB_PRE_PHASE2_DOCS_CANON_AUDIT.md`.

**Not changed:** session logs, archive trees, governance under `knowledge/governance/**`, `CURRENT_STATUS.md`, code/runtime.

---

## Deferred / Post-Phase-2 Exit Items

- Post-Phase-2 documentation reconciliation report (required before #2778 epic close per #2778 body).
- Wave 7–21 completion gate files: classify as historical in bulk or archive subtree.
- `surrealdb_context_mcp_access.md`: formal status promotion + host-matrix re-verification.
- #2777 / #2781 parent reconcile docs alignment with closed Phase-1 children.

---

## Decision

**PASS_WITH_DEFERRED_EXIT_ITEMS**

**Rationale:**

- Complete inventory and classification for scoped surfaces.
- Contradiction matrix produced; **safety-critical** stale claims (#2606 OPEN in active design headers) **fixed**.
- Live GitHub Phase-1 closeout issues (#2603–#2606, #2689, #2773–#2776) match closed state.
- MCP **27** tools, all `readOnly` in schema; `make context-certify` → **certified**, LR **NO-GO**.
- Remaining gaps are **non-blocking** for using canon as Phase-2 **planning** input: historical wave gates, session log tool counts, exit audit not yet run.

**Does not activate Phase 2.** #2778 remains **PARKED** until G1 (#2777, #2781) and other entry gates pass separately.

---

## Impact on #2778 (G8 pass/fail)

| Gate | Result | Evidence |
| --- | --- | --- |
| **G8 — Documentation Canon Entry Gate** | **PASS** (with deferred items above) | This report |
| G0–G7 | **Not re-run in full** | #2777/#2781 OPEN; dirty `main` worktree elsewhere — use clean branch for implementation |
| Epic activation | **FAIL / PARKED** | Explicit per #2778; no Jannek GO for Phase-2 implementation |

---

## Validation (commands)

```text
Repo SHA: 4f220eaaae797133ac2f16fb1e6a830772aefc95
Branch: docs/2780-pre-phase2-canon-audit (clean worktree from origin/main)

python -c "from tools.mcp.context_bridge import create_bridge; tools=create_bridge().list_tools(); print(len(tools)); print(all((t.get('readOnly') or t.get('read_only')) for t in tools))"
# 27
# True

make context-certify
# final_verdict: certified, tool_count: 27, lr_note: NO-GO, PERSIST_ALLOWED: False, MUTATION_ALLOWED: False

rg "PERSIST_ALLOWED\s*=\s*True|MUTATION_ALLOWED\s*=\s*True" docs/surrealdb \
  --glob '!SURREALDB_PRE_PHASE2_DOCS_CANON_AUDIT.md'
# memory-write-path-t4-runbook-v1.md:140 — negation ("No code-level PERSIST_ALLOWED=True on main"); safe

rg "stays OPEN" docs/surrealdb --glob '!SURREALDB_PRE_PHASE2_DOCS_CANON_AUDIT.md'
# (empty — six design-doc headers reconciled in this PR; audit matrix rows are meta, not live claims)
```

**Not run:** `make context-smoke-db`, `make context-import-local`, any `--apply`, Docker stack.

---

## Brain Evidence (audit session)

```text
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - gh issue view (2780, 2778, 1976, 2603-2606, 2689, 2773-2777, 2781)
  - gh pr list --search "SurrealDB OR Context OR MCP..."
  - python create_bridge().list_tools()
  - make context-certify
  - rg safety / issue-state scans on docs/surrealdb
records_or_results:
  - MCP tool_count=27, readOnly schema=True for all tools
  - context-certify: certified, LR NO-GO
repo_crosscheck:
  - docs/runbooks/surrealdb_context_mcp_access.md §1.5.1 (27 tools)
  - knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md
impact_on_plan:
  - G8 PASS_WITH_DEFERRED; #2778 stays PARKED; minimal #2606 header fixes only
limitations:
  - No surrealdb-local query records; no full line-by-line read of all 81 files
  - Post-Phase-2 exit audit not performed (by design)
```

---

## References

- PRs: #2784, #2786, #2789, #2792, #2793, #2788 (merged)
- Issues: #2780 (this audit), #2778 (G8), #1976 (parent)
