# /onboarding Tabletop Validation — Fresh-Agent Simulation

**Issue:** [#3274](https://github.com/jannekbuengener/Claire_de_Binare/issues/3274)
**Parent:** [#3271](https://github.com/jannekbuengener/Claire_de_Binare/issues/3271)
**Date:** 2026-06-17
**Agent:** OPENCODE/deepseek
**Scope:** Read-only tabletop walkthrough of `/onboarding` slash skill

---

## Brain Evidence Block

```
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - cdb_context_context_show_audit(target_tool="cdb_context_context_quality_score") → handler_status:"unknown_tool", exists:false
records_or_results:
  - audit_0d04f977cf05: registry-only, no handler dispatch
repo_crosscheck:
  - agents/AGENTS.md § Context Brain Preflight Gate (added per #3276)
  - agents/OPEN_CODE_AGENTS.md (Context Brain first routing)
impact_on_plan:
  - Context Brain MCP tools unavailable; repo-only fallback with evidenced reason tool_blocked
  - Simulation runner output contract validated per #3273
limitations:
  - No SurrealDB-backed context/memory/evidence available
  - No MCP-based Context Brain querying possible
context_brain_attempted: true
context_brain_used: false
repo_fallback_used: true
repo_fallback_reason: tool_blocked
```

## Bootloader Evidence

| Step | File | Status | Evidence |
|------|------|--------|----------|
| 1 | `AGENTS.md` (root pointer) | READ | Line 270: "Context Brain first" rule present |
| 2 | `agents/AGENTS.md` | READ | § Context Brain Preflight Gate (l.103-131), § Brain Evidence Gate (l.133-180) |
| 3 | `agents/OPEN_CODE_AGENTS.md` | READ | Line 31: "Context Brain Preflight immer vor Repo-Reads" |
| 4 | `docs/runbooks/CONTROL_REGISTER.md` | READ | stage:trade-capable, LR NO-GO |
| 5 | `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | READ | Verdict NO-GO |
| 6 | `CURRENT_STATUS.md` | READ | Ledger, not live truth |
| 7 | `knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md` | READ | Default: brain_source=repo-only, brain_status=not-used |

## Live Truth

| Source | Check | Result |
|--------|-------|--------|
| GitHub Issues #3271–#3276 | `gh issue view` | All OPEN, state consistent |
| GitHub PRs | `gh pr list --state open` | 6 Dependabot PRs, none conflict |
| git fetch origin main | `git fetch --prune` | Success |
| git status | `git status --porcelain` | Clean (only untracked: .opencode/plans/, docs/decisions/) |
| HEAD vs origin/main | `git rev-parse HEAD` = `git rev-parse origin/main` | `0cbb8eb1` — matched |

## /onboarding Invocation

Simulation triggered: `python -m tools.onboarding_simulation --role agent --mode first-issue-dry-run`

### ONBOARDING_START Output

```
ONBOARDING_START
mode: first-issue-dry-run
role: Agent
writes: disabled
github_writes: disabled
lr: NO-GO
```

## Simulated Agent Walkthrough

### 1. Context Brain Preflight

The agent attempts Context Brain MCP call (`cdb_context_context_show_audit`).
Result: `unknown_tool`, `exists: false`.

- `context_brain_attempted: true`
- `context_brain_used: false`
- `repo_fallback_used: true`
- `repo_fallback_reason: tool_blocked`

Per `agents/AGENTS.md` § Context Brain Preflight Gate: valid fallback, agent may proceed with repo-only context.

### 2. Bootloader Resolution

```
AGENTS.md -> agents/AGENTS.md -> agents/OPEN_CODE_AGENTS.md
```

All three files read and present. Read Order followed.

### 3. Control Context

- `CONTROL_REGISTER.md`: stage `trade-capable` (not Live-Go)
- `LR-AUDIT-STATUS-2026-03-05.md`: LR-050 NO-GO
- `CURRENT_STATUS.md`: ledger read, not treated as live truth

### 4. Live Truth Verification

- `git fetch origin main` — pass
- `git status --porcelain` — clean
- `gh issue view 3271` — OPEN, correct title
- `gh pr list --state open` — no onboarding PR conflicts

### 5. Onboarding Tour

Agent role path from `tools/onboarding_tour.py` delivers:
1. AGENTS.md (root pointer)
2. agents/AGENTS.md (canonical registry)
3. agents/OPEN_CODE_AGENTS.md (shared contract)
4. docs/runbooks/CONTROL_REGISTER.md (board stage)
5. docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md (LR SSOT)

### 6. Doctor / Validator

- `python -m tools.onboarding_doctor` — would execute read-only check (not run in tabletop)
- `python -m tools.validate_onboarding_docs` — PASS (all active surfaces pass)
- `make context-doctor` — reachability check

### 7. First-Issue Dry Run (Simulated)

Scope: docs-only change (e.g., add term to `cdb_glossary.md`).
The simulation runner outputs:

```
First-Issue Dry Run:
  Scope: docs-only change (e.g. add term to cdb_glossary.md).
  1. Branch from origin/main: docs/<issue>-<slug>.
  2. Edit a single safe file under docs/onboarding/.
  3. Run: python -m tools.validate_onboarding_docs.
  4. Run: ruff check .
  5. Commit with conventional commit message.
  6. Push branch.
```

### 8. PR / LOCK Simulation

The simulation runner outputs the full PR workflow including:
- PR body sections: Delivered, Validation, Non-Goals, Safety, Restunsicherheiten
- LOCK: comment before mutation
- Required checks: ci + policy-gate
- Squash-merge after green

### 9. HOLD Conditions

All HOLD conditions enumerated in the simulation output:
- git fetch / gh issue view failures
- Dirty worktree with unknown changes
- Local main behind origin/main
- Context Brain Preflight failure without valid fallback
- Bootloader files missing
- Required checks red and not scope-fixable
- Scope growth beyond allowed surfaces
- Secrets or LR/Live boundaries touched

### 10. Final Verdict

```
Final Verdict: READY_FOR_REAL_FIRST_ISSUE
```

The simulation runner delivers `READY_FOR_REAL_FIRST_ISSUE` for `first-issue-dry-run` mode.
In `check-only` mode it delivers `HOLD_ONBOARDING_GAP`.

## Observed Gaps

| Gap | Severity | Follow-up |
|-----|----------|-----------|
| No `.cursor/skills/onboarding/` mirror exists | Low | #3272 created only `.opencode/skills/onboarding/` — Cursor mirror deferred |
| No `.codex/cdb_skills/onboarding/` mirror exists | Low | Codex surface not in scope; deferred |
| Context Brain MCP tools are `unknown_tool` in this session | Medium | This is expected: MCP surface varies per environment. Bootloader handles via `repo_fallback_reason=tool_blocked` |

## Final Verdict

**Verdict: `READY_FOR_REAL_FIRST_ISSUE`**

The `/onboarding` flow produces a complete, safe, read-only onboarding path:
1. Bootloader reads are coherent and enforceable.
2. Context Brain Preflight Gate provides mandatory attempt + evidenced fallback.
3. Live truth (GitHub + repo) is checked before ledger.
4. Tour, doctor, and validator surfaces are all accessible.
5. First-issue sandbox and PR/LOCK workflow are simulated correctly.
6. HOLD conditions cover all critical failure modes.
7. Final verdict is deterministic based on mode input.

The flow is safe for a fresh agent to execute without additional prompt scaffolding.
No runtime, Docker, trading, LR, DB, or MCP mutations occur.

---

## Safety Boundaries

- LR remains **NO-GO**.
- Board stage `trade-capable` is **not** Live-Go.
- No Echtgeld-Go.
- This validation is read-only: no file writes, no GitHub writes, no Docker/runtime/DB/MCP mutation.

---

*Evidence document generated per #3274 tabletop validation contract.*
