# Codex MCP Config Reference

Codex loads MCP servers from **global** `~/.codex/config.toml` and **project**
`.codex/config.toml` (merged per Codex precedence). The CDB Context MCP server
(`cdb_context`) is the repo-native stdio process `python -m tools.mcp.server` and
must run with **cwd** set to the Claire de Binare repo root so `tools.*` imports
resolve.

## Project-local Codex (recommended)

**Claire de Binare** — [`.codex/config.toml`](../../.codex/config.toml) at repo root
(relative `command`, absolute `cwd`).

**sample-brain** — `.codex/config.toml` in the sample-brain checkout points
`cdb_context` at `D:/Dev/Workspaces/Repos/Claire_de_Binare` (cross-repo).

Example (sample-brain or global):

```toml
[mcp_servers.cdb_context]
enabled = true
command = "D:/Dev/Workspaces/Repos/Claire_de_Binare/.venv/Scripts/python.exe"
args = ["-m", "tools.mcp.server"]
cwd = "D:/Dev/Workspaces/Repos/Claire_de_Binare"
```

After editing, restart or reconnect MCP in the Codex app so the stdio server
reloads.

## Via OpenCode

1. Ensure `opencode.jsonc` in repo root includes the `cdb_context` MCP entry.
2. When OpenCode invokes Codex (via agent delegation), `cdb_context` tools
   are available in the MCP inventory.

## Via Claude Code

1. Copy `agents/templates/claude_mcp.json.template` to your user-level
   `.mcp.json` (see Claude Code docs for the correct path).
2. When Claude Code delegates to Codex, MCP tools are available.

## Canonical repo config

- Cursor (CDB): `.cursor/mcp.json`
- Canon / sync source: `claire-de-binare.mcp.json` (`cdb_context` + optional `redis`)
- OpenCode: `opencode.jsonc`

## Validation

```bash
# From CDB repo root, verify bridge works
python -c "from tools.mcp.context_bridge import create_bridge; b=create_bridge(); print(len(b.list_tools()))"
# Expected: 26

pwsh -File agents/templates/onboarding_mcp_setup.ps1
```

## Fallback

If `context.briefing` is not in the active MCP tool inventory:
- Report `brain_source=repo-only`, `brain_status=not-used`
- Use repo evidence for all claims
- Do not claim DB-backed Brain/Evidence/Memory
