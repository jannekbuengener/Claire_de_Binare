# Issue #500 Closure Note (Current Repo State)

Date: 2026-03-10
Scope: `cdb_autoclaude` / AutoCloud review under the rule "do not revive".

## Current repo state

- No dedicated `cdb_autoclaude` compose stack, workflow, or runbook exists in the tracked repo.
- The remaining tracked artifacts are a generic Graphiti/Ollama memory overlay:
  - `infrastructure/compose/memory.yml`
  - `infrastructure/scripts/init-memory.ps1`
  - `infrastructure/scripts/init-memory.sh`
  - `infrastructure/scripts/verify-graphiti.py`
  - `infrastructure/config/graphiti/graphiti_config.yaml`
- `.auto-claude/` exists only as ignored local workspace data and is not a versioned operator path.

## What was misleading

- Active comments and script output still referred to "Auto-Claude integration".
- The default Graphiti group id still used the abandoned name `auto-claude`.
- A local issue tracker note still listed "stand up isolated cdb_autoclaude stack" as if it were backlog work.

## Repo closure slice applied

- Active memory overlay paths were reworded as generic local MCP/Graphiti helpers.
- Default Graphiti group id was changed from `auto-claude` to `cdb-memory`.
- `.auto-claude/` is now explicitly described in `.gitignore` as legacy local data only.
- The local tracker entry is marked obsolete/cancelled instead of actionable backlog.

## Maintainer conclusion

Issue `#500` should be treated as obsolete/cancelled.
The repo no longer presents `cdb_autoclaude` / AutoCloud as an active stack to build or operate.

## Remaining limits

- The generic memory overlay still exists for Graphiti/Ollama experimentation; this note does not remove it.
- Existing local environments that intentionally used the old Graphiti group id `auto-claude` may need to override `GRAPHITI_GROUP_ID` explicitly if they want continuity.
