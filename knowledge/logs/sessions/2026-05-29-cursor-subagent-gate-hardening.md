# Session: Cursor subagent gate hardening

Date: 2026-05-29  
Agent: cdb-docs-canon-maintainer (Cursor)  
GO: `GO CURSOR SUBAGENT GATE HARDENING`

## Scope

Docs-only hardening after PR #2729 smoke test. No runtime, workflow, infra, MCP
mutation, LR/live/trading implication. No `CURRENT_STATUS.md` update in slice.

## Changes

- `.cursor/agents/_CDB_SUBAGENT_CONTRACT.md` — Parent agent enforcement; absolute
  `gh`-only GitHub writes; MCP/API read-only default; Zone A vs Write-Zone with
  `CDB_AGENT_POLICY` precedence.
- `.cursor/agents/README_CDB_CURSOR_SUBAGENTS.md` — Write-gates summary table.
- `agents/AGENTS.md` — Cursor subagent operational surface / discovery; parent
  enforcement; gh-only; Zone A clarification.

## Validation

- YAML frontmatter of 13 `cdb-*.md` unchanged; contract refs intact.
- Formal frontmatter script: PASS.
- Risk phrase grep: no autonomous merge/deploy/live-go additions.

## LR / Board

Unchanged. LR NO-GO. Board `trade-capable` orthogonal.
