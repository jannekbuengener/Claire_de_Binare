# #1976 Real-Task-Proof Run — #2513 Trivy Triage Context (2026-06-03 execution)

| Field | Value |
| --- | --- |
| **Real task** | [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513) — read-only operator validation of upstream-blocked Trivy residuals (no dismissals) |
| **RTP issue** | [#2832](https://github.com/jannekbuengener/Claire_de_Binare/issues/2832) — second Real-Task-Proof |
| **Grandparent** | [#1976](https://github.com/jannekbuengener/Claire_de_Binare/issues/1976) |
| **Execution date (UTC)** | 2026-06-03 |
| **Proof base SHA** | `44c2895db1fbd76e1201903a77450a213ff8dd2d` (`origin/main` after PR #2836) |
| **Branch** | `real-task-proof-2832-context-workflow` |
| **Worktree** | `Claire_de_Binare__2780-audit` |
| **Readiness SSOT** | [`SURREALDB_1976_GRANDPARENT_DOD_AND_REAL_TASK_PROOF.md`](SURREALDB_1976_GRANDPARENT_DOD_AND_REAL_TASK_PROOF.md) |
| **RTP verdict** | **`PASS`** |

---

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - gh issue view 2513, 2832, 1976, 2833 (2026-06-03 UTC session)
  - git rev-parse HEAD → 44c2895d; branch real-task-proof-2832-context-workflow
  - PYTHONPATH=. python: PERSIST_ALLOWED/MUTATION_ALLOWED → False/False
  - PYTHONPATH=. python: create_bridge().list_tools() → 27 tools, all_readonly=True
  - python -m tools.surrealdb.context_certify --format json → final_verdict certified
  - build_context_package_v2(target_scope=issue:2513) → pkg_ffb00bafd919 (in_memory)
  - pytest -q test_context_certify, test_context_package_v2, test_context_bridge -m unit → 280 passed
records_or_results:
  - #2513: OPEN (upstream-blocked Trivy tracking)
  - #2832: OPEN (this RTP)
  - #1976: OPEN (epic HOLD)
  - #2833: OPEN (operator closeout)
  - cdb_context MCP not mounted in IDE session (in-process bridge only)
repo_crosscheck:
  - docs/security/TRIAGE_RUNBOOK.md (read-only triage SSOT)
  - tools/surrealdb/memory_write_gate.py PERSIST_ALLOWED=False
  - tools/mcp/memory_write_intent_tools.py MUTATION_ALLOWED=False
  - tools/mcp/context_bridge.py, tools/surrealdb/context_certify.py, context_package_v2.py
  - docs/runbooks/surrealdb_context_mcp_access.md §1.5 capability protocol
impact_on_plan:
  - Read-only Context package + required_reads for #2513 batch triage (no dismissals)
  - RTP §C matrix → PASS for #2832; does not authorize #1976 epic closeout
limitations:
  - No surrealdb-local query/record IDs
  - context_certify: inventory-only doctor (no --include-live-checks)
  - Package v2 built from in-memory artifacts, not DB-backed retrieval
```

---

## Target issue and scope

| Item | Value |
| --- | --- |
| Issue | #2513 |
| Mode | Read-only audit / operator validation |
| Allowed | Context certify, bridge enumerate, package v2, required_reads plan, proof artifact, session log |
| Forbidden | Trivy dismissals, SARIF hiding, Docker/runtime, MCP mutations, secret values |

**Task question (concrete):**

> For #2513: Which repo- and runbook-backed Context surfaces support read-only triage of upstream-blocked Trivy clusters (batches A–G2) without dismissal or runtime?

**Completion criteria (#2832):** Honest RTP artifact on `main` with §C verdict; PR closes #2832 only.

---

## Live GitHub reads (2026-06-03 UTC)

| Object | State | Notes |
| --- | --- | --- |
| #2513 | **OPEN** | 681 Trivy alerts; 547 custom-service upstream-blocked |
| #2832 | **OPEN** | Second RTP (this run) |
| #1976 | **OPEN** | Grandparent epic; HOLD |
| #2833 | **OPEN** | Operator closeout pending |
| `origin/main` | `44c2895d` | Post PR #2836 thermos SSOT |

---

## Repo state

| Item | Value |
| --- | --- |
| Base | `origin/main` @ `44c2895db1fbd76e1201903a77450a213ff8dd2d` |
| Branch | `real-task-proof-2832-context-workflow` |
| Worktree | `D:\Dev\Workspaces\Repos\Claire_de_Binare\Claire_de_Binare__2780-audit` |
| Worktree clean | **yes** (at certify timestamp) |

**Guardrails (repo crosscheck):**

- `PERSIST_ALLOWED = False` — `tools/surrealdb/memory_write_gate.py`
- `MUTATION_ALLOWED = False` — `tools/mcp/memory_write_intent_tools.py`

---

## Files inspected (read-only)

| Path | Action |
| --- | --- |
| `agents/AGENTS.md` | Read Order (bootloader) |
| `docs/security/TRIAGE_RUNBOOK.md` | Dismissal governance SSOT for #2513 |
| `docs/runbooks/surrealdb_context_mcp_access.md` | §1.5 capability protocol |
| `tools/surrealdb/memory_write_gate.py` | PERSIST gate |
| `tools/mcp/memory_write_intent_tools.py` | MUTATION gate |
| `tools/mcp/context_bridge.py` | Bridge / list_tools |
| `tools/surrealdb/context_certify.py` | Operator certification |
| `tools/surrealdb/context_package_v2.py` | Package v2 builder |
| `docs/surrealdb/SURREALDB_1976_GRANDPARENT_DOD_AND_REAL_TASK_PROOF.md` | §B / §F / §G |
| `docs/surrealdb/SURREALDB_1976_REAL_TASK_PROOF_RUN_2026-06-02.md` | RTP #1 template |

---

## Feature surfaces exercised or cross-checked

| Surface | Evidence |
| --- | --- |
| `make context-certify` / `context_certify` | `final_verdict: certified`; 27/27 read-only; gates pass |
| MCP bridge enumerate | `create_bridge().list_tools()` → 27, `all_readonly=True` |
| Context Package v2 | `target_scope=issue:2513` → `package_id=pkg_ffb00bafd919`; 3 artifacts, 3 required_reads |
| Runbook §1.5 | Capability protocol aligned with bridge inventory (L3 bridge verified; IDE host not mounted) |
| Unit tests | 280 passed (certify + package_v2 + context_bridge) |

---

## Read-only triage plan (deliverable for #2513)

**Proposed `required_reads` for batch-oriented triage (no code change; operator workflow):**

| Read surface | Use for #2513 |
| --- | --- |
| `docs/security/TRIAGE_RUNBOOK.md` | Dismissal comment template; Human-GO per batch; G2 Lead-Maintainer rule |
| `github:issue:2513` | Batch table A–G2; severity notes; base-image Slice 6+ boundary |
| `github:issue:2289` | Historical slice context (closed epic) |

**Batch triage order (read-only validation only):**

1. Confirm cluster still upstream-blocked (empty fixed version in Trivy metadata) — no dismissal.
2. Map batch to runbook severity rules (e.g. batch B TLS risk statement; batch G2 CRITICAL review).
3. Use Context package v2 envelope to orient agent on scope before any future Human-GO request.
4. Defer base-image cluster (134 alerts) to separate Slice 6+ planning — out of #2513 custom-service scope.

**Explicit non-actions:** No `gh api` dismissal, no SARIF suppression, no compose/BLUE/RED, no LR/live-trading claims.

---

## Validation commands and results

| Command | Result |
| --- | --- |
| `python -m tools.surrealdb.context_certify --format json` | **certified**; `git_sha=44c2895d`; safety_flags read-only |
| `PYTHONPATH=. python` bridge enumerate | **27** tools, **all_readonly=True** |
| `build_context_package_v2` (`issue:2513`) | **pkg_ffb00bafd919**; in-memory envelope; content_hash in determinism block |
| `pytest -q tests/unit/surrealdb/test_context_certify.py tests/unit/surrealdb/test_context_package_v2.py tests/unit/tools/mcp/test_context_bridge.py -m unit` | **280 passed** (2.22s) |

No `.py` files modified in this slice (docs-only PR).

---

## Real-Task-Proof criteria matrix (§C)

| Criterion | Required | This run | Verdict |
| --- | --- | --- | --- |
| Echtes offenes CDB-Issue | Yes | #2513 selected (read-only triage) | **PASS** |
| Read Order + GitHub-live reads | Yes | Bootloader + timestamped `gh` above | **PASS** |
| Branch/repo status, scope, guardrails | Yes | Branch @ `44c2895d`; PERSIST/MUTATION False | **PASS** |
| Brain Evidence honest | Yes | repo-only; not-used | **PASS** |
| Konkreter Plan/Patch-Entwurf | Yes | required_reads + batch triage plan above | **PASS** |
| Validierungsplan + Ergebnis | Yes | certify certified; pytest 280; package v2 | **PASS** |
| Restunsicherheiten fail-closed | Yes | See §Limitations below | **PASS** |
| No false LR/DB/live claims | Yes | LR NO-GO; no dismissals/runtime | **PASS** |

**Real-Task-Proof verdict:** **`PASS`** (all §C criteria).

**Note:** Epic-close **HOLD** per §B remains; #2833 operator closeout still **OPEN**.

---

## Safety boundaries

| Boundary | Status |
| --- | --- |
| LR | **NO-GO** |
| Board `trade-capable` | Not LR-Go |
| `PERSIST_ALLOWED` | **False** |
| `MUTATION_ALLOWED` | **False** |
| #2513 dismissals | **None** |
| Productive SurrealDB writes | **None** |
| MCP mutations | **None** |
| Secrets in outputs | **None** |

---

## Restunsicherheiten

1. **No live SurrealDB record IDs** — package v2 is in-memory artifact assembly, not adapter-backed retrieval.
2. **IDE MCP host** — `cdb_context` not mounted; L4/L5 per runbook matrix not re-certified in this session.
3. **context_certify doctor** — inventory-only mode; live TCP/MCP/schema checks skipped unless operator runs `--include-live-checks`.
4. **Trivy alert counts** — sourced from #2513 issue body (2026-05-17); not re-fetched from GitHub Code Scanning API in this run.
5. **Post-merge** — merge SHA and #2832 close state must be confirmed live after PR merge.

---

## Post-merge actions (when PR merged)

1. Comment on #2832 with proof path + merge SHA + verdict **PASS**.
2. Close #2832 only (PR body: `Closes #2832` — **not** #1976 / #2833).
3. Comment on #1976: RTP #2 **PASS** for #2832 scoped to #2513; link this file; epic **OPEN/HOLD**; #2833 pending.
4. Reopen #1976 if PR accidentally auto-closes via `closingIssuesReferences`.
5. Update `CURRENT_STATUS.md` ledger from live `gh issue view`.
6. Leave #2833 **OPEN**.

**Explicit non-action:** Do not close #1976 or #2833 from this artifact.
