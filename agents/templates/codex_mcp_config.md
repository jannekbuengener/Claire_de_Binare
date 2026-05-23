# Codex MCP Config Reference

Codex does not have a separate MCP config surface. Codex is invoked through
**OpenCode** (for repo-native dev work) or **Claude Code** (for session-led
architecture work). The CDB Context MCP server is available to Codex through
the calling agent's MCP configuration.

## Via OpenCode

1. Ensure `opencode.jsonc` in repo root includes the `cdb_context` MCP entry.
2. When OpenCode invokes Codex (via agent delegation), `cdb_context` tools
   are available in the MCP inventory.

## Via Claude Code

1. Copy `agents/templates/claude_mcp.json.template` to your user-level
   `.mcp.json` (see Claude Code docs for the correct path).
2. When Claude Code delegates to Codex, MCP tools are available.

## Validation

```bash
# From repo root, verify bridge works
python -c "from tools.mcp.context_bridge import create_bridge; b=create_bridge(); print(len(b.list_tools()))"
# Expected: 26
```

## Fallback

If `context.briefing` is not in the active MCP tool inventory:
- Report `brain_source=repo-only`, `brain_status=not-used`
- Use repo evidence for all claims
- Do not claim DB-backed Brain/Evidence/Memory
