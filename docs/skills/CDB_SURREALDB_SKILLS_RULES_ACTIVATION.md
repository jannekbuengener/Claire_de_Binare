# CDB SurrealDB Skills / Rules Activation

Status: active slice output for `#3482`

## Purpose

This document records the CDB-owned activation of official SurrealDB skill topics
and agent-rule topics across the repo-versioned agent surfaces.

This slice is separate from `#3493`.
`#3493` proved inventory and exposure state.
`#3482` activates curated, script-free SurrealDB guidance on the allowed CDB
surfaces.

## Official Sources

- Agent Skills docs: `https://surrealdb.com/docs/build/ai-agents/agent-skills`
- Agent Rules docs: `https://surrealdb.com/docs/build/ai-agents/agent-rules`
- Agent Skills repo: `https://github.com/surrealdb/agent-skills`
- Skills source commit inspected: `95628976`
- Rules source repo/path: `https://github.com/surrealdb/docs.surrealdb.com/tree/main/public/integrations/agent-rules`
- Rules source commit inspected: `a69077df`

## Activation Model

- CDB does not vendor the official SurrealDB skills verbatim.
- CDB activates curated, script-free wrappers derived from the official sources.
- CDB only adds rules where a canonical rule surface already exists.
- CDB Governance wins over upstream best practice whenever they conflict.

## Surface Matrix

| Surface | Skills | Rules | Status |
| --- | --- | --- | --- |
| OpenCode | `surrealql`, `surrealdb-vector`, `surrealdb-python` | no canonical rule surface | ACTIVE skills / GAP rules |
| Cursor | `surrealql`, `surrealdb-vector`, `surrealdb-python` | `.cursor/rules/*.mdc` | ACTIVE |
| Codex | `surrealql`, `surrealdb-vector`, `surrealdb-python` | no canonical rule surface | ACTIVE skills / GAP rules |
| Claude | `surrealql`, `surrealdb-vector`, `surrealdb-python` | no canonical rule surface | ACTIVE skills / GAP rules |
| Gemini | no tracked activation in this slice | no canonical rule surface | NOT_APPLICABLE |

## Why Gemini Stays Inactive

- `.gemini/skills` is not a canon activation target for this slice.
- The repo allowlist treats `.gemini/` differently from the main skill surfaces.
- Local Gemini SurrealDB candidates remain untouched and untracked.

## Rules Scope

- Official rule concept verified against SurrealDB docs.
- Only `.cursor/rules/` exists as a canonical rule surface in this repo.
- Therefore only Cursor receives tracked SurrealDB rules in this slice.
- OpenCode, Codex, and Claude are documented as `GAP` for rules rather than
  forcing a non-canonical surface.

## Safety Boundaries

- No installers executed.
- No `npx skills add` execution.
- No copied helper scripts.
- No DB writes.
- No MCP mutations.
- No Live-Go.
- No Echtgeld-Go.
- No secrets or example root credentials carried into tracked skills.

## Local Candidate Assessment

- `.opencode/skills/*` and `.cursor/skills/*` candidates were present locally and inspected.
- `surrealql` candidates were outdated versus current inspected upstream and included
  disallowed `npx` formatter guidance.
- `surrealdb-python` candidates included upstream server-start and root-credential examples.
- The tracked result is therefore curated, not blind adoption.

## Remaining Gaps

- No canonical rule surface exists yet for OpenCode, Codex, or Claude.
- Gemini SurrealDB candidates remain intentionally inactive.
- This slice activates only the required official SurrealDB skills:
  `surrealql`, `surrealdb-vector`, and `surrealdb-python`.
