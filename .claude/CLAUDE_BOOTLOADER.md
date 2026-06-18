# CLAUDE BOOTLOADER (WORKSPACE POINTER)

You MUST load and follow that file before proceeding.

This file exists only to ensure automatic workspace loading.

# CLAUDE BOOTLOADER (MANDATORY)

This bootloader is the first file to be loaded in every session.

READ ORDER:
1) Session Entry Point (Working Repo):
   D:\Dev\Workspaces\Repos\Claire_de_Binare\AGENTS.md
   Follow all pointers defined there to canonical documentation.

2) AgentMemory Overlay (local, persistent):
   - D:\Dev\AI\AgentMemory\cdb\00_canon   (read-only snapshots)
   - D:\Dev\AI\AgentMemory\cdb\10_working (working memory)

WRITE PERMISSIONS (strict):
- Allowed:
  - D:\Dev\AI\AgentMemory\cdb\10_working
  - D:\Dev\AI\AgentMemory\cdb\20_decisions
  - D:\Dev\AI\AgentMemory\cdb\30_evidence
  - D:\Dev\Workspaces\Repos\Claire_de_Binare (Arbeits Repo — einziges produktives Repo)
  - D:\Dev\Workspaces\Prompts (Aktuelle Arbeitsanweisungen und Todo´s)
  - D:\Dev\Workspaces\Worktrees (Backups)
  - D:\Dev\Config\MCP (Team-MCP)
  - D:\Dev\AI\Claude (deine config)

- Forbidden:
  - Canonical docs
  - Governance / policy sources

SESSION END:
- Write a handoff summary to:
  D:\Dev\AI\AgentMemory\cdb\10_working\handoff.md

You speak only german.
If any referenced path is missing or inaccessible: STOP and ask Jannek.
