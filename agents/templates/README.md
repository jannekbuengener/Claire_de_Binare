# Agent MCP Config Templates

This directory contains MCP configuration templates for each agent surface.

## Files

| File | Surface | Type | Status |
|------|---------|------|--------|
| `../opencode.jsonc` (repo root) | OpenCode | repo-tracked config | Active |
| `claude_mcp.json.template` | Claude / Cloud Code | template (needs manual copy) | Needs manual install |
| `gemini_mcp_config.yml.template` | Gemini workflow | inline config snippet (needs manual embed) | Needs manual install |
| `codex_mcp_config.md` | Codex | reference only (no separate MCP surface) | Via host agent |
| `codex_config.example.toml` | Codex | template (copy to `.codex/config.toml`) | Needs manual install |
| `onboarding_mcp_setup.ps1` | Onboarding / any agent | validation script | Run from repo root |

## Distinction

- **repo-tracked config**: auto-loaded by the agent host when running in this repo.
- **template**: requires manual copy/embed into host-specific config location.
- **reference**: documentation only, no separate config file.

## Common pattern

All templates reference the same `cdb_context` stdio server as `claire-de-binare.mcp.json`:

```json
{
  "command": ".venv/Scripts/python.exe",
  "args": ["-m", "tools.mcp.server"]
}
```

**Portability:** On Windows-local CDB checkouts, use the repo `.venv` interpreter (relative path above). On Linux/macOS, use `.venv/bin/python` with the same args. The MCP host must use **cwd = repo root** so `tools.*` resolves. Do not use HTTP `127.0.0.1:8811` as the primary Context MCP path.

The canonical sync source is `claire-de-binare.mcp.json` at repo root (Cursor: `.cursor/mcp.json`).

Repo-local skills (non-MCP): `.cursor/skills/`, `.codex/cdb_skills/`, `.opencode/skills/`.

## Validation

After setup, run from repo root:

```bash
pwsh -File agents/templates/onboarding_mcp_setup.ps1
```
