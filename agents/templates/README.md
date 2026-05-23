# Agent MCP Config Templates

This directory contains MCP configuration templates for each agent surface.

## Files

| File | Surface | Type | Status |
|------|---------|------|--------|
| `../.opencode.jsonc` (repo root) | OpenCode | repo-tracked config | Active |
| `claude_mcp.json.template` | Claude / Cloud Code | template (needs manual copy) | Needs manual install |
| `gemini_mcp_config.yml.template` | Gemini workflow | inline config snippet (needs manual embed) | Needs manual install |
| `codex_mcp_config.md` | Codex | reference only (no separate MCP surface) | Via host agent |
| `onboarding_mcp_setup.ps1` | Onboarding / any agent | validation script | Run from repo root |

## Distinction

- **repo-tracked config**: auto-loaded by the agent host when running in this repo.
- **template**: requires manual copy/embed into host-specific config location.
- **reference**: documentation only, no separate config file.

## Common pattern

All templates reference the same `cdb_context` server entry:

```json
{
  "command": "python",
  "args": ["-m", "tools.mcp.server"]
}
```

The canonical config lives in `claire-de-binare.mcp.json` at repo root.

## Validation

After setup, run from repo root:

```bash
pwsh -File agents/templates/onboarding_mcp_setup.ps1
```
