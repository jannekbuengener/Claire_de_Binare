# CDB Agent Senses — Operator Runbook

| Field | Value |
| --- | --- |
| Status | **active** |
| Issue | [#2855](https://github.com/jannekbuengener/Claire_de_Binare/issues/2855) |
| Parent meta | [#2847](https://github.com/jannekbuengener/Claire_de_Binare/issues/2847) |
| Scope | Docs-only operator map; no runtime activation |
| LR | **NO-GO** — see [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../live-readiness/LR-AUDIT-STATUS-2026-03-05.md) |
| Board | `trade-capable` is **not** live-go — see [`CONTROL_REGISTER.md`](CONTROL_REGISTER.md) |

This page is the **single operator-facing map** of what agents can “sense,” how evidence
is ranked, when repo-only is enough, and how fail-closed fallbacks work. Canonical
governance detail stays in [`agents/AGENTS.md`](../../agents/AGENTS.md); MCP wiring
stays in [`surrealdb_context_mcp_access.md`](surrealdb_context_mcp_access.md).

---

## 1. What agents can sense (tool layers)

| Layer | What it is | Typical access | Live truth? |
| --- | --- | --- | --- |
| **GitHub live** | Issues, PRs, checks, branches, comments | `gh` CLI (Write-Zone needs GO) | **Yes** for process state |
| **Repo live** | Code, contracts, runbooks, tests in working tree | `git`, file reads, `rg` | **Yes** for canon content at HEAD |
| **Context / MCP (read-only)** | Bridge + stdio tools (`tools/mcp/`) | `cdb_context` in `claire-de-binare.mcp.json` | Tool output + contract fields |
| **SurrealDB context (local)** | Guarded read adapter | Explicit `adapter_config_path`; localhost only | Only with **record evidence** |
| **Ledger / status snapshots** | `CURRENT_STATUS.md`, session logs, evidence packs | File read | **No** — historical / derived |
| **In-memory / fixtures** | Noop bundle, test fixtures, `briefing.session_context` | MCP/bridge in dev | **No** DB-backed claims |
| **Tests / harness** | Unit/integration proofs, live-invoke matrix | `pytest`, `make context-live-invoke` | Proof of behavior, not live ops |
| **Safety gates** | `PERSIST_ALLOWED`, `MUTATION_ALLOWED`, LR, Human-GO | Module constants + policy | **Authoritative** for write scope |

**Rule:** Higher layers in the [evidence ladder](#2-evidence-quality-ladder) win on
conflict. Never treat ledger text or briefing JSON as live GitHub truth.

---

## 2. Evidence quality ladder

Aligned with [`agents/AGENTS.md`](../../agents/AGENTS.md) § Brain Evidence Gate and
[`knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`](../../knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md).

| Rank | Source | Use when |
| --- | --- | --- |
| 1 | **Live GitHub** | Issue/PR state, required checks, mergeability, comments |
| 2 | **Repo live** | Governance, code, contracts, runbooks at checked-out commit |
| 3 | **Verified DB/MCP evidence** | SurrealDB-local reads with tool/query/**record** proof ([#2851](https://github.com/jannekbuengener/Claire_de_Binare/issues/2851)) |
| 4 | **Governance files** | Constitution, agent policy, invariants (stable rules) |
| 5 | **Ledger / snapshots** | `CURRENT_STATUS.md`, dated evidence markdown |
| 6 | **Memory / assumptions** | Session hints only; lowest trust |

**Fail-closed:** If layer 3 is missing, stale, contradictory, or unprovable →
degrade to repo reads (layer 2) and state limitations explicitly. Do not invent
DB-backed claims.

---

## 3. `brain_source` and `brain_status` (operator reading)

| `brain_source` | Meaning | `brain_status` pairing |
| --- | --- | --- |
| `repo-only` | No SurrealDB-backed brain used | **`not-used`** (default) |
| `in_memory` | Fixtures / Noop / session-only briefing | **`not-used`** — no DB claims |
| `surrealdb-local` | Real localhost adapter read | **`used`** or **`partial`** only with record evidence |
| `unavailable` | MCP/DB path blocked | **`blocked`** or repo-only fallback |

### What counts as DB-backed evidence

- Real **tool invocation** with handler dispatch (not `unknown_tool` / `not_implemented`)
- **Query or lookup fingerprint** and **record IDs** or content fingerprints per
  [`DB_RECORD_EVIDENCE_CONTRACT.md`](../contracts/context_tooling/DB_RECORD_EVIDENCE_CONTRACT.md)
- **`metadata.source`** derived from guarded adapter (`surrealdb-local`), not typed by the caller alone ([#2638](https://github.com/jannekbuengener/Claire_de_Binare/issues/2638))

### What does **not** count

- Caller-supplied `brain_source`, `brain_status`, or `metadata.source` without invocation proof
- Text in a Brain Evidence block with no `tools_or_queries` / `records_or_results`
- Stale `CURRENT_STATUS.md` or ledger markdown contradicting `gh issue view` / `gh pr view`
- Benchmark markdown alone without JSON/harness correlation ([#2850](https://github.com/jannekbuengener/Claire_de_Binare/issues/2850))

---

## 4. Full tool stack vs docs-only

Benchmark evidence ([#2843](https://github.com/jannekbuengener/Claire_de_Binare/issues/2843), [#2845](https://github.com/jannekbuengener/Claire_de_Binare/issues/2845)):

| Mode | Includes | Typical verdict enum |
| --- | --- | --- |
| **Docs-only** | Runbooks + `CURRENT_STATUS` + issue prose | Stale risk on GitHub state; cannot prove 27/27 live tools |
| **Full tool stack** | GitHub + repo + MCP bridge/stdio + harness/tests | `FULL_TOOL_STACK_BETTER_WITH_LIMITS` or better when limits cleared |

**Operator takeaway:** For Context/MCP hardening or “is the brain real?” questions,
require **full stack** rechecks (`make context-live-invoke`, `gh` live state). Docs-only
is enough for **stable rules** (governance, safety boundaries), not for **live** issue/PR/check truth.

---

## 5. Harness and certification verdicts (interpretation)

From live-invocation and certification harnesses (see
[`CDB_ALL_TOOLS_LIVE_INVOCATION_PROOF_2026-06-03.md`](../evidence/context_tooling/CDB_ALL_TOOLS_LIVE_INVOCATION_PROOF_2026-06-03.md)):

| Verdict | Operator meaning |
| --- | --- |
| **PASS** | Expected success or **expected** fail-closed refusal (e.g. bridge write-intent `status=refused`) |
| **PASS_WITH_LIMITS** | Accepted limitation — documented `missing_*` or environment gap ([#2852](https://github.com/jannekbuengener/Claire_de_Binare/issues/2852) ratification) |
| **ACCEPTED_LIMITATION** | Ratified PASS_WITH_LIMITS row; recheck trigger documented |
| **BLOCKED_SAFETY** | Policy/Smart Mode blocked MCP call — **not** handler FAIL ([#2854](https://github.com/jannekbuengener/Claire_de_Binare/issues/2854)) |
| **FAIL** | Unexpected behavior — fix or open P0 child (e.g. scope drift) |
| **BLOCKED** | Certification/readiness gate failed — no adoption claim |

**Impact-map example (memory write gate):**

- Bridge `cdb_context_memory_write_intent` + `operation_mode=agent_memory_write` → **PASS** (`refused`)
- Same intent via MCP stdio under Smart Mode → **BLOCKED_SAFETY** (accepted boundary)
- Treating BLOCKED_SAFETY as FAIL is a **classification error**, not a safety regression.

---

## 6. Root and target visibility ([#2853](https://github.com/jannekbuengener/Claire_de_Binare/issues/2853))

Local working repo root and GitHub **target** repo are **separate** concepts:

| Concept | SSOT |
| --- | --- |
| Cross-repo inventory | `infrastructure/config/mcp/cross_repo_root_inventory.json` |
| Operator table | `make context-root-inventory` |
| Evidence | [`CDB_CROSS_REPO_ROOT_INVENTORY_2026-06-03.md`](../evidence/context_tooling/CDB_CROSS_REPO_ROOT_INVENTORY_2026-06-03.md) |

**CWD drift:** MCP host `host_cwd` may differ from `resolved_repo_root`. Use
`context.readiness` fields (`root_drift_detected`, `effective_scan_root`) — see
[#2848](https://github.com/jannekbuengener/Claire_de_Binare/issues/2848). Do not assume
canon files exist relative to the IDE cwd alone.

---

## 7. Negative controls ([#2854](https://github.com/jannekbuengener/Claire_de_Binare/issues/2854))

Write/mutation blockades are **expected PASS/BLOCKED_SAFETY**, not defects:

| Flag | Default | Evidence |
| --- | --- | --- |
| `PERSIST_ALLOWED` | `False` | `tools/surrealdb/memory_write_gate.py` |
| `MUTATION_ALLOWED` | `False` | `tools/mcp/memory_write_intent_tools.py` |

Matrix and regression: [`CDB_NEGATIVE_CONTROLS_MATRIX_2026-06-03.md`](../evidence/context_tooling/CDB_NEGATIVE_CONTROLS_MATRIX_2026-06-03.md),
`make context-negative-controls`.

---

## 8. Fallback rules (operator checklist)

1. **GitHub first** for open/closed issues, PR merge state, required checks.
2. **Repo read** for governance, code paths, and runbooks at `git rev-parse HEAD`.
3. **MCP capability resolution** before planning Context work (§1.5 in
   [`surrealdb_context_mcp_access.md`](surrealdb_context_mcp_access.md)).
4. If MCP/DB unavailable → `brain_source=repo-only`, `brain_status=not-used`, list limitations.
5. If DB claim needed → satisfy [#2851](https://github.com/jannekbuengener/Claire_de_Binare/issues/2851) contract + JSON evidence ([#2850](https://github.com/jannekbuengener/Claire_de_Binare/issues/2850)).
6. **Never** enable productive writes, `PERSIST_ALLOWED=True`, or `MUTATION_ALLOWED=True` without explicit Human-GO and separate scope.

Trust scoring thresholds remain **out of scope** here — see [#2856](https://github.com/jannekbuengener/Claire_de_Binare/issues/2856).

---

## 9. Safety boundaries (always state)

- **LR:** NO-GO — no live capital / Echtgeld without human gate.
- **Board stage** `trade-capable` ≠ strategy validation or LR-GO.
- **No** productive SurrealDB writes or MCP mutations by default.
- **No** secrets in issues, PRs, logs, or evidence packs.
- Context Brain / MCP read results **do not** authorize merges, runtime changes, or code edits alone.

---

## 10. Recommended operator recheck commands

```bash
# Git / GitHub live
git fetch origin --prune
git status -sb
git rev-parse HEAD origin/main
gh issue view <N> --json state,title,labels
gh pr view <N> --json state,mergeable,statusCheckRollup

# Context / MCP read-only proof
make context-doctor
make context-certify
make context-live-invoke
make context-live-invoke FORMAT=json   # when JSON evidence needed
make context-negative-controls
make context-root-inventory

# Focused unit regression (no live DB required for most)
pytest -q tests/unit/tools/mcp/ -m unit
pytest -q tests/unit/surrealdb/test_negative_controls_regression.py -m unit
```

Redact secrets before sharing JSON or certification output externally.

---

## 11. Related SSOT (do not duplicate)

| Topic | Path |
| --- | --- |
| Agent registry + Brain Evidence Gate | [`agents/AGENTS.md`](../../agents/AGENTS.md) |
| MCP access + capability protocol | [`surrealdb_context_mcp_access.md`](surrealdb_context_mcp_access.md) |
| DB record evidence contract | [`docs/contracts/context_tooling/DB_RECORD_EVIDENCE_CONTRACT.md`](../contracts/context_tooling/DB_RECORD_EVIDENCE_CONTRACT.md) |
| JSON invocation evidence | [`docs/contracts/context_tooling/TOOL_INVOCATION_JSON_EVIDENCE.md`](../contracts/context_tooling/TOOL_INVOCATION_JSON_EVIDENCE.md) |
| Context tooling evidence index | [`docs/evidence/context_tooling/README.md`](../evidence/context_tooling/README.md) |
| Benchmark #2 proof | [`docs/evidence/context_tooling/CDB_ALL_TOOLS_LIVE_INVOCATION_PROOF_2026-06-03.md`](../evidence/context_tooling/CDB_ALL_TOOLS_LIVE_INVOCATION_PROOF_2026-06-03.md) |

---

## Non-goals (this issue)

- Trust scoring policy ([#2856](https://github.com/jannekbuengener/Claire_de_Binare/issues/2856))
- Security alert triage ([#2860](https://github.com/jannekbuengener/Claire_de_Binare/issues/2860)–#2869, PR [#2877](https://github.com/jannekbuengener/Claire_de_Binare/pull/2877))
- Runtime BLUE/RED, productive DB writes, or MCP mutations
