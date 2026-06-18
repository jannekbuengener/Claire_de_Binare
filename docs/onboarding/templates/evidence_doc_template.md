# Evidence Document Template

Status: Template
Issue: `<issue-number>`
Date: `<YYYY-MM-DD>`
Scope: `<bounded scope>`

Docs/UI sind Orientierung, keine Autoritaet. LR bleibt NO-GO. No Live-Go. No
Echtgeld-Go.

## Summary

- `<one-sentence result>`
- `<what this evidence proves>`
- `<what this evidence does not prove>`

## Scope

In scope:

- `<path or artifact>`

Out of scope:

- `<explicit exclusions>`

## Brain Evidence

```text
## Brain Evidence
brain_source: `<surrealdb-local | in_memory | repo-only | unavailable>`
brain_status: `<used | partial | not-used | blocked>`
tools_or_queries:
  - `<tool, command, query, or repo read>`
records_or_results:
  - `<record id, count, source, hash, or explicit none>`
repo_crosscheck:
  - `<file/path/commit/issue>`
impact_on_plan:
  - `<evidence-driven effect>`
limitations:
  - `<unproven area>`
```

## Bootloader Evidence

| Surface | Evidence |
|---|---|
| `AGENTS.md` | `<root pointer resolved>` |
| `agents/AGENTS.md` | `<Read Order resolved>` |
| `CDB_AGENT_POLICY.md` section 4 | `<write-gate read>` |
| Status surfaces | `<CONTROL_REGISTER / CURRENT_STATUS / LR audit read>` |

## Live Evidence

| Check | Result |
|---|---|
| `git fetch origin --prune` | `<result>` |
| `git status -sb` | `<result>` |
| `git rev-parse HEAD` | `<sha>` |
| `git rev-parse origin/main` | `<sha>` |
| `gh issue view <issue>` | `<open/closed plus relevant facts>` |
| `gh pr list ...` | `<matching PR state>` |

## Findings

| Finding | Evidence | Impact | Classification |
|---|---|---|---|
| `<finding>` | `<file/line/issue/run>` | `<effect>` | `<pass/warn/block>` |

## Validation

| Command | Result | Notes |
|---|---|---|
| `<command>` | `<exit/result>` | `<scope note>` |

## Follow-ups

- `<follow-up issue or none>`

## Restunsicherheiten

- `<known uncertainty or none>`

## Status

`<PASS | PASS_WITH_LIMITS | BLOCKED | HOLD_<reason>>`
