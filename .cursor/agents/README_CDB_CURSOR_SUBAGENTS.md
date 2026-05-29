# CDB Cursor Subagents

Status: Canonical (Cursor IDE subagent slice)  
Path: `.cursor/agents/`  
Shared contract: [`.cursor/agents/_CDB_SUBAGENT_CONTRACT.md`](_CDB_SUBAGENT_CONTRACT.md)

## Purpose

Cursor custom subagents for delegated CDB work. They are **helper roles**, not
standalone authorities — see shared contract § Authority and limits.

Invocation example:

```text
/cdb-repository-auditor Prüfe read-only die Agent-Dateien. Keine Writes.
```

## Structure

Each agent is a Markdown file with Cursor-compatible YAML frontmatter:

```yaml
name: cdb-<role>
description: ...
model: inherit
readonly: true|false
is_background: false
```

Role-specific content lives in the agent file; bootstrap, operating rules, Brain
Evidence, LOCK, session skills, and output shape live in the shared contract.

## Readonly policy

| `readonly` | Agents |
| --- | --- |
| `false` (write after GO + session-start + LOCK) | `cdb-ci-debugger`, `cdb-context-intelligence-engineer`, `cdb-docs-canon-maintainer`, `cdb-implementation-engineer` |
| `true` (always read-only) | all other `cdb-*` agents |

## Files

- `_CDB_SUBAGENT_CONTRACT.md` — shared governance (mandatory for all subagents)
- `cdb-ci-debugger.md`
- `cdb-code-reviewer.md`
- `cdb-context-intelligence-engineer.md`
- `cdb-control-orchestrator.md`
- `cdb-docs-canon-maintainer.md`
- `cdb-governance-gatekeeper.md`
- `cdb-implementation-engineer.md`
- `cdb-market-research-analyst.md`
- `cdb-repository-auditor.md`
- `cdb-security-triage.md`
- `cdb-stack-ops-auditor.md`
- `cdb-system-architect.md`
- `cdb-validation-evidence-analyst.md`

## Registry

Canonical pointer: `agents/AGENTS.md` § Cursor Subagents.  
Canon matrix: `docs/meta/WORKING_REPO_CANON.md`.

## Governance notes

- LR SSOT: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` (NO-GO default).
- `CURRENT_STATUS.md` is a ledger, not live truth.
- Board stage `trade-capable` is not Live-Go.
- No subagent grants merge, deploy, live trading, or Echtgeld GO.
- **`CDB_AGENT_POLICY.md` wins** on conflict; see shared contract § Zone A vs Write-Zone.

## Write gates (summary)

| Gate | Rule |
| --- | --- |
| Parent enforcement | Parent agent enforces Jannek GO, session-start, LOCK, Brain Evidence, scope — not the subagent alone. |
| `readonly: false` | Technical capability only; fail-closed without GO + session-start + LOCK (when issue-scoped). |
| GitHub mutations | **`gh` CLI only** — PRs, comments, labels, reviews, merges, branch deletes, workflow dispatch. |
| MCP / API / connectors | Read / inspect / dry-run only unless separate explicit GO names tool + action. |
| Zone A discovery | Read-only repo/GitHub inspection allowed; mutating actions = Write-Zone. |

Full rules: [`_CDB_SUBAGENT_CONTRACT.md`](_CDB_SUBAGENT_CONTRACT.md) (§ Parent agent enforcement, § Non-Negotiable Operating Rules, § Zone A vs Write-Zone).

## Reload

After changes, reload Cursor and smoke-test one read-only and one write agent
(with explicit „kein GO“ — must stop).
