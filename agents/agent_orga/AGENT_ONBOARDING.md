# Agent Onboarding Canon

**Status:** Canonical onboarding entrypoint  
**Scope:** Agent discovery, read order, local adapter setup, validation  
**Authority boundary:** `agents/AGENTS.md` and `knowledge/governance/CDB_AGENT_POLICY.md` win on conflict.

## Start here

1. Read [`agents/AGENTS.md`](../AGENTS.md).
2. Follow its numbered mandatory Read Order.
3. Select the adapter or role surface needed for the current host.
4. Validate referenced paths before using an agent or Context-MCP capability.

`knowledge/CDB_KNOWLEDGE_HUB.md` is historical/reference only and is not part of onboarding or autoload.

## Canonical surfaces

| Purpose | Canonical path |
|---|---|
| Agent registry and mandatory read order | [`agents/AGENTS.md`](../AGENTS.md) |
| Agent policy | [`knowledge/governance/CDB_AGENT_POLICY.md`](../../knowledge/governance/CDB_AGENT_POLICY.md) |
| Repository canon | [`docs/meta/REPOSITORY_CANON.md`](../../docs/meta/REPOSITORY_CANON.md) |
| Root adapter inventory | [`docs/onboarding/AGENT_ROOT_SURFACE_MATRIX.md`](../../docs/onboarding/AGENT_ROOT_SURFACE_MATRIX.md) |
| Machine-readable autoload paths | [`agents/AUTOLOAD_MANIFEST.yaml`](../AUTOLOAD_MANIFEST.yaml) |
| Context MCP operator guide | [`docs/runbooks/surrealdb_context_mcp_access.md`](../../docs/runbooks/surrealdb_context_mcp_access.md) |
| Current repo status | [`CURRENT_STATUS.md`](../../CURRENT_STATUS.md) |

## Adapter and role discovery

Agent definitions and adapters are repository-versioned. They are not restricted to a fixed Claude-to-Codex chain.

- Shared registry and roles: `agents/`, `agents/roles/`
- Claude: `.claude/`
- Codex: `.codex/`
- Cursor: `.cursor/`
- Gemini: `.gemini/`
- OpenCode: `.opencode/`
- VS Code helper surface: `.vscode/`

Choose the surface that matches the active host. No adapter receives authority beyond the shared policy and Human Gate.

## Context MCP

The repo-native server entrypoint is:

```text
python -m tools.mcp.server
```

Host-specific configuration is documented by the active adapter surface and the Context-MCP runbook. Historical standalone MCP config files are not onboarding entrypoints.

Bridge inventory check:

```bash
python -c "from tools.mcp.context_bridge import create_bridge; print(len(create_bridge().list_tools()))"
```

The current contract expects **27** tools. The executable bridge is the source of truth; this document does not maintain a second tool-name list.

For Context-/MCP-/Memory-/Evidence work, apply the Context Brain Preflight and Brain Evidence rules from `agents/AGENTS.md`. No DB-backed claim is allowed without actual tool/query/record evidence.

## Commands

Use only commands that exist in the repository. Historical agent-specific Make targets are not supported onboarding entrypoints.

Supported validation entrypoints:

```bash
python -m tools.validate_onboarding_docs
python -m tools.validate_readme_links
python -m tools.validate_root_layout
pytest -q tests/unit/agents
```

Host-specific setup scripts may exist under the relevant adapter or `agents/templates/`; verify the path before execution.

## Write and orchestration boundary

- Read-only discovery does not grant write permission.
- Commits, pushes, issue changes, PR actions, workflow dispatches, and merges are Write-Zone actions.
- Effective writes require the current Human-GO and the gates defined by `CDB_AGENT_POLICY.md` and `agents/AGENTS.md`.
- No agent is permanently the universal orchestrator. The active session lead may delegate within the current host and policy boundary.
- The historical Knowledge Hub is not a write target or current handoff queue.

## Deep-link compatibility

The previous Quickstart, Setup Guide, Autoload Manifest copy, and orchestration-plan paths remain as short pointers. They contain no second onboarding procedure.

## Maintenance rule

Update onboarding behavior here only after the underlying registry, policy, adapter, manifest, command, or executable inventory has changed. Never document a command, config, role file, or tool count without repository evidence and a matching contract test.
