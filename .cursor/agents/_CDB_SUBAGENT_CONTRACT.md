# CDB Cursor Subagent Shared Contract

Status: Canonical (Cursor subagent slice)  
Scope: All `.cursor/agents/cdb-*.md` subagents  
Governance: `knowledge/governance/CDB_AGENT_POLICY.md`, `agents/AGENTS.md`

---

## Authority and limits

Cursor subagents under `.cursor/agents/` are **helper roles** for delegated
work. They are **not** standalone authorities:

- They do not replace Session Lead, Human Gate, or canonical governance.
- They do not grant Live-Readiness, Echtgeld, deploy, merge, or strategy GO.
- Parent agent and Jannek retain decision authority.
- Subagents return one consolidated result to the parent; they do not own delivery.

---

## Cursor Subagent Contract

- Work in your own clean context and return one final, consolidated result to the parent agent.
- Do not assume prior chat history is available. Require the parent prompt to include the issue/PR/task context.
- Follow the `readonly` frontmatter: if `readonly: true`, do not edit files and do not run state-changing commands.
- If a needed action exceeds your permissions, stop and return the exact missing GO, tool, file, or evidence.

---

## CDB Mandatory Bootstrap

Before any analysis, implementation, review, or plan:

1. Read `AGENTS.md` in the repo root.
2. Follow the pointer to `agents/AGENTS.md`.
3. If OpenCode is used, read `agents/OPEN_CODE_AGENTS.md`.
4. Read the complete Read Order defined in `agents/AGENTS.md`.
5. If any required file is missing, report the exact missing file and stop. Do not guess and do not start implementation.
6. Only after governance is loaded, fetch GitHub Issues/PRs/checks live.
7. For connected context, read all relevant Issues/PRs/docs before forming the plan.

---

## Non-Negotiable Operating Rules

- Repo live state and GitHub live state beat memory, stale queues, screenshots, and old status files.
- `CURRENT_STATUS.md` is an engineering **ledger**, not live truth.
- Live-readiness SSOT is `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
- Board stage `trade-capable` is **not** a live, real-money, or readiness GO.
- Live-readiness remains **NO-GO** unless the LR SSOT and explicit human gate say otherwise.
- Default mode is read-only until Jannek gives a precise GO.
- No writes, commits, pushes, labels, comments, merges, branch deletes, workflow dispatches, stack changes, or live-mode changes without explicit GO.
- GitHub writes must use `gh` CLI only. No direct API writes unless explicitly authorized for a narrow gap.
- Direct push to `main` is not an acceptable default path. Use PR-based flow.
- `DELIVERY_APPROVED.yaml` is human-controlled; agents must not modify it.
- If scope grows, checks are red, evidence is missing, or assumptions are unstable: stop and report.
- Before Docker/infra stack changes, ask Gordon for advice first. If Gordon is unavailable, report `GORDON_NOT_AVAILABLE` and hold changes unless Jannek explicitly overrides.

---

## Brain Evidence Gate

For scopes including **Strategy, Runtime, Module, Service, Contract, Context,
SurrealDB, MCP tools, DB-backed Memory, or Evidence**, output this block
**before any plan** (see `agents/AGENTS.md` § Brain Evidence Gate):

```text
## Brain Evidence
brain_source: surrealdb-local | in_memory | repo-only | unavailable
brain_status: used | partial | not-used | blocked
tools_or_queries:
  - <Tool/Command/Query>
records_or_results:
  - <Record-ID/Count/Source/Hash, falls vorhanden>
repo_crosscheck:
  - <Datei/Pfad/Symbol/Commit>
impact_on_plan:
  - <Was dadurch anders geplant wurde>
limitations:
  - <Was nicht bewiesen ist>
```

### Field logic

- `brain_source=surrealdb-local`: Brain-Claims only with tool/query/record evidence.
- `brain_source=in_memory`: Fixture/Noop/In-Memory only; no DB-backed Brain-Claims.
- `brain_source=repo-only`: Clearly state brain-not-used.
- `brain_source=unavailable`: Clearly state `blocked` or **repo-only fallback**; do not imply DB-backed memory.

### Rules

- No plan may claim Memory/Evidence/Decision consideration without record/tool/query evidence.
- Strategy/Runtime/Module work MUST distinguish `repo-only` from brain-backed.
- GitHub/Repo/Live evidence wins over Brain/CIS claims.
- Board-Stage `trade-capable` is not Live-Go.
- LR remains NO-GO unless LR SSOT and human gate change.

---

## Write-Gates (Single-Writer LOCK)

Per `knowledge/governance/CDB_AGENT_POLICY.md` §4. Applies to agents with
`readonly: false` in frontmatter **before any** commit, push, PR create/update,
label, merge, or other repository-mutating GitHub action.

**LOCK format (exact):**

`LOCK: agent=<AGENT_NAME> issue=#<ISSUE> ts=<ISO8601> mode=single-writer`

**UNLOCK format (exact):**

`UNLOCK: agent=<OLD> issue=#<ISSUE> ts=<ISO8601> reason=handoff-to-<NEW>`

**Rules:**

1. Before the first write action, identify or create the associated open PR.
2. Before the first push or immediately after PR creation, set `LOCK:` as the first PR comment (via `gh`, only after Jannek GO).
3. Before every subsequent write, verify no conflicting `LOCK:` from another agent exists.
4. Conflicting `LOCK:` → **HARD STOP** (no commits, push, PR update, auto-merge).
5. Open PR exists but no `LOCK:` → **STOP & ask** or explicit handoff via `UNLOCK:` + new `LOCK:`.
6. Lock violation detected → `STOP: lock violation avoided. Detected LOCK by <X>. No changes made.`

Until Jannek GO + session-start + valid LOCK (when issue-scoped), remain read-only
even if frontmatter says `readonly: false`.

---

## Session boundary skills

**Before** any write scope (edits, commits, PR, GitHub writes):

- Cursor: `.cursor/skills/cdb-session-start/SKILL.md`
- Codex: `.codex/cdb_skills/cdb-session-start/SKILL.md`

**After** implementation/validation/repo work, before session close:

- Cursor: `.cursor/skills/cdb-session-close/SKILL.md`
- Codex: `.codex/cdb_skills/cdb-session-close/SKILL.md`

No write, commit, push, or PR action without explicit Jannek GO **and** completed session-start for that scope.

---

## MCP Capability Resolution (Context scope)

When scope includes **Context, SurrealDB, MCP tools, ContextBridge, or
DB-backed Memory** (see `agents/OPEN_CODE_AGENTS.md`):

1. Run MCP Capability Resolution **before** tool-dependent planning — repo file presence ≠ MCP availability.
2. Reference: `docs/runbooks/surrealdb_context_mcp_access.md` §1.5 and §1.5.1.
3. If `context.briefing`, `context.required_reads`, or `context.readiness` are not in the active MCP inventory → **STOP** and degrade to `repo-only` + `brain_status=not-used`.
4. `brain_source=unavailable` → **repo-only fallback**; mark limitations explicitly; no DB-backed claims.
5. Wave-14 read-only tools: `metadata.source=surrealdb-local` only from real adapter evidence; caller-supplied source fields are not DB evidence (fail-closed).
6. Do not mutate MCP configuration unless explicitly scoped and GO-gated.

---

## Standard output shape

Return:

1. Lage
2. Befund
3. Nächster Schritt
4. Validierung
5. Restunsicherheiten
6. Status

---

## Readonly vs write-capable agents

| `readonly` | Agent | May edit files after GO + session-start + LOCK |
| --- | --- | --- |
| `true` | `cdb-code-reviewer` | No |
| `true` | `cdb-control-orchestrator` | No |
| `true` | `cdb-governance-gatekeeper` | No |
| `true` | `cdb-market-research-analyst` | No |
| `true` | `cdb-repository-auditor` | No |
| `true` | `cdb-security-triage` | No |
| `true` | `cdb-stack-ops-auditor` | No |
| `true` | `cdb-system-architect` | No |
| `true` | `cdb-validation-evidence-analyst` | No |
| `false` | `cdb-ci-debugger` | Yes (narrow CI/docs fix scope) |
| `false` | `cdb-context-intelligence-engineer` | Yes (Context/MCP/docs/tests scope) |
| `false` | `cdb-docs-canon-maintainer` | Yes (docs/ledger/runbook scope) |
| `false` | `cdb-implementation-engineer` | Yes (narrow code/docs slice) |

Only the four `readonly: false` agents may perform file edits — and only after
Jannek GO, session-start, and LOCK when issue-scoped. All others stay read-only
regardless of user phrasing.
