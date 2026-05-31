# Codex MCP Config Reference

Codex loads MCP servers from **global** `~/.codex/config.toml` and **project**
`.codex/config.toml` (merged per Codex precedence). The CDB Context MCP server
(`cdb_context`) is the repo-native stdio process `.venv/Scripts/python.exe -m tools.mcp.server`
(Windows-local CDB) and must run with **cwd** set to the Claire de Binare repo root
so `tools.*` imports resolve. On Linux/macOS use `.venv/bin/python` with the same args.

## Project-local Codex (recommended)

**Claire de Binare** — copy [`codex_config.example.toml`](codex_config.example.toml)
to `.codex/config.toml` at repo root (`.codex/` is gitignored; use relative `command` and
`cwd = "."`).

**sample-brain** — `.codex/config.toml` in the sample-brain checkout may point
`cdb_context` at the CDB repo (cross-repo); keep `cwd` on the CDB checkout root.

Example (after copy; adjust `command` on Linux/macOS):

```toml
[mcp_servers.cdb_context]
enabled = true
command = ".venv/Scripts/python.exe"
args = ["-m", "tools.mcp.server"]
cwd = "."
```

After editing, restart or reconnect MCP in the Codex app so the stdio server
reloads.

## Via OpenCode

1. Ensure `opencode.jsonc` in repo root includes the `cdb_context` MCP entry
   (portable `python` in the tracked config; Windows-local optional override to
   `.venv/Scripts/python.exe` via user-level `~/.config/opencode/opencode.jsonc`).
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
# From CDB repo root (Windows-local venv)
.venv/Scripts/python.exe -c "from tools.mcp.context_bridge import create_bridge; b=create_bridge(); print(len(b.list_tools()))"
# Expected: 26

pwsh -File agents/templates/onboarding_mcp_setup.ps1
```

Linux/macOS: replace `.venv/Scripts/python.exe` with `.venv/bin/python`.

## Fallback

If `context.briefing` is not in the active MCP tool inventory:
- Report `brain_source=repo-only`, `brain_status=not-used`
- Use repo evidence for all claims
- Do not claim DB-backed Brain/Evidence/Memory
