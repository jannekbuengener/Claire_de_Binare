---
relations:
  role: doc
  domain: agents
  upstream: []
  downstream: []
---
# Defines roles and responsibilities for agents.

Context Brain default posture (read-only, conditional): [`knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`](../../knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md); Brain Evidence Gate: [`agents/AGENTS.md`](../AGENTS.md) § Brain Evidence Gate.

## Where to write / Where not to write
*   **Write here:** Definitions of agent roles, their responsibilities, and high-level mandates.
*   **Do NOT write here:** Individual agent prompts (use [`agents/prompts/`](../prompts/README.md)), task lists (use [`agents/tasklists/`](../tasklists/README.md)), governance policy (use [`knowledge/governance/`](../../knowledge/governance/README.md)).

## Key entrypoints

| Role file | Surface |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Claude Code session lead |
| [`CODEX.md`](CODEX.md) | Codex CLI |
| [`GEMINI.md`](GEMINI.md) | Gemini |
| [`OPENCODE.md`](OPENCODE.md) | OpenCode |
| [`COPILOT.md`](COPILOT.md) | GitHub Copilot |

Support/audit role variants in this directory remain direct file links when needed.
