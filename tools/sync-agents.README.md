# sync-agents.ps1

Synchronizes the five agent markdown files between the Docs Hub (canonical) and the Working repo.

## Usage
- Default pull (Docs Hub -> Working repo root): `.\tools\sync-agents.ps1`
- Dry run preview: `.\tools\sync-agents.ps1 -DryRun`
- Push (Working -> Docs Hub, requires confirmation): `.\tools\sync-agents.ps1 -Push -Force`
- Custom paths: `.\tools\sync-agents.ps1 -DocsHubPath 'D:\Docs' -WorkingRepoPath 'D:\Work'`

## Notes
- Always backs up any overwritten target under `tools\_backups\agents\<timestamp>\`.
- Canonical source is Docs Hub unless `-Push` is set. Push is blocked without `-Force`.
- Files synced exactly (no line-ending normalization): `AGENTS.md`, `CLAUDE.md`, `CODEX.md`, `COPILOT.md`, `GEMINI.md`.

## Acceptance test
1) Run `.\tools\sync-agents.ps1 -DryRun`
2) Run `.\tools\sync-agents.ps1`
3) Verify `AGENTS.md`/`CLAUDE.md`/`CODEX.md`/`COPILOT.md`/`GEMINI.md` exist in the Working repo root.
4) Verify a backup directory exists under `tools\_backups\agents\`.
