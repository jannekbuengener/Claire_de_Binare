# Session: Cursor subagent canon hardening

Date: 2026-05-29  
Scope: `.cursor/agents/**` + registry pointers  
GO: `GO CURSOR SUBAGENT CANON HARDENING`

## Summary

- Extracted shared governance into `.cursor/agents/_CDB_SUBAGENT_CONTRACT.md`.
- Refactored 13 `cdb-*.md` subagents to reference shared contract; removed duplicated boilerplate.
- Write agents: explicit Write scope with Jannek-GO, session-start/close, LOCK.
- `cdb-context-intelligence-engineer`: Brain Evidence + MCP Capability Resolution + repo-only fallback.
- Registry pointers: `agents/AGENTS.md`, `docs/meta/WORKING_REPO_CANON.md`, root `AGENTS.md`.

## Validation

- Python `yaml.safe_load` on all 13 agent frontmatter files: PASS.
- Required keys present; 4 write / 9 read-only agents unchanged in policy.
- No autonomous merge/deploy/live-trading language introduced.

## Governance

- LR remains NO-GO; no live/runtime/workflow changes.
- `CURRENT_STATUS.md` referenced only as ledger in shared contract.

## PR

- Branch: `docs/cursor-subagent-canon`
- Title: `docs(agents): canonize Cursor subagents`
