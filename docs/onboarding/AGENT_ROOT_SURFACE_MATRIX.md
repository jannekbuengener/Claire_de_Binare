# Agent Root Surface Matrix

Versionierte Repo-Root-Flächen für Cross-Agent-Onboarding.

## Surfaces

| Surface | Tracked Safe Files | Ignored Private/Generated | Onboarding Route | Owner/Role |
|---------|-------------------|--------------------------|-----------------|------------|
| `.claude/` | `README.md`, `CLAUDE_BOOTLOADER.md`, `skills/` | `settings.json`, `settings.local.json`, `scheduled_tasks.lock` | `python -m tools.onboarding_orchestrator` via `AGENTS.md` | Claude Code — Bootloader, Session-Skills |
| `.codex/` | `README.md`, `cdb_skills/` | `config.toml`, `config.agents.snippet.toml`, `.system/` (extern), `skillforge/`, `mockexchange/` | `python -m tools.onboarding_orchestrator` via `AGENTS.md` | Codex CLI — Session-Skills (repo-versioniert) |
| `.cursor/` | `README.md`, `agents/`, `rules/`, `skills/`, `mcp.json` | `settings.json` (local workspace state), `.system/`, `skillforge/`, `mockexchange/` | `python -m tools.onboarding_orchestrator` via `AGENTS.md` | Cursor IDE — Subagents, Regeln, Session-Skills |
| `.gemini/` | `README.md`, `settings.json`, `onboarding.md` | `github_issue_body.txt`, lokale Session-State-Dateien | `python -m tools.onboarding_orchestrator` via `onboarding.md` und `GEMINI.md` | Gemini — IDE-Konfiguration, Onboarding-Router |
| `.opencode/` | `README.md`, `skills/` | `.system/` (extern), `skillforge/`, `mockexchange/` | `python -m tools.onboarding_orchestrator` via `AGENTS.md` und `skills/` | OpenCode CLI — Session-Skills (repo-versioniert) |
| `.vscode/` | `README.md`, `extensions.json`, `settings.json` | Keine (nur repo-sichere Dateien versioniert) | `python -m tools.onboarding_orchestrator` via `AGENTS.md` | VS Code — Helper-Surface (keine Autorität) |

## Kanonische Onboarding-Route

```
user: "/onboarding", "onboarding", "onboarding durchführen", "mach onboarding", "fresh agent onboarding"
→ agent: python -m tools.onboarding_orchestrator
→ result: Read-only CDB Onboarding Status Card
→ next: User wählt nächsten Schritt (explizit)
```

## Safety Boundaries (alle Surfaces)

| Regel | Status |
|-------|--------|
| LR Live-Go | **NO-GO** |
| `trade-capable` = Live-Go | **false** |
| Echtgeld-Autorisierung | **Keine** |
| Runtime-/Docker-/DB-/MCP-Mutation | **Keine ohne expliziten Human-GO** |
| Secrets in Outputs | **Verboten** |
| Blanket-Tracking lokaler State | **Verboten** |

## Gitignore-Strategie

```
# Allowlist-Ansatz (pro Surface):
<surface>/*
!<surface>/README.md
!<surface>/<spezifische-safe-dateien>
```

Nicht aufgeführte Dateien in jedem Surface bleiben ignoriert (private/generated/lokal).

## Referenzen

- Agent Registry: `agents/AGENTS.md`
- Root Pointer: `AGENTS.md`
- LR-Status: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- Board-Stage: `docs/runbooks/CONTROL_REGISTER.md`
- Onboarding Orchestrator: `tools/onboarding_orchestrator.py`
