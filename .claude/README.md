# Claude Root Surface (`/.claude/`)

Repo-versionierte Claude-Code-Konfigurationsfläche. Teil des CDB-Agent-Root-Surface-Systems.

## Struktur

| Pfad | Zweck |
|------|-------|
| `README.md` | Diese Datei — Surface-Beschreibung |
| `CLAUDE_BOOTLOADER.md` | Claude-Bootloader (Read-Order, Write-Permissions) |
| `skills/` | Repo-versionierte Session-Skills für Claude Code |

## Einstiegspunkte

- **Bootloader**: `CLAUDE_BOOTLOADER.md` (Read-Order, Write-Permissions, Agent-Memory-Pfade)
- **Skills**: `skills/` — Vollständige Listung in `.cursor/skills/README.md`
- **Onboarding-Intent**: `python -m tools.onboarding_orchestrator`
- **Skill Registry**: `.claude/skills/` — siehe auch `.cursor/skills/README.md` für Skill-Katalog

## Onboarding-Route

Bei `/onboarding`-Intent: `python -m tools.onboarding_orchestrator`

Default: Read-only Status Card. Kein `.env`, keine Secrets, kein Docker, kein Issue/PR ohne explizite Auswahl.

**Evidence-Abgrenzung nach /onboarding:** Antwort muss enthalten: Status, State, warnings, allowed_next_actions, check_scope, skipped_checks, Evidence-Abgrenzung (was geprüft, was nicht) und Safety-Grenzen. Ohne git/gh/check-Kommandos: "Repo-/Canon-Prüfung durchgeführt; GitHub-/Check-Live nicht geprüft."

## Safety Boundaries

- LR remains **NO-GO**
- `trade-capable` ist nicht `Live-Go`
- Keine Echtgeld-Transaktionen
- Keine Runtime-/Docker-/DB-/MCP-Mutationen
- Lokale State-Dateien (`settings.json`, `settings.local.json`) bleiben unversioniert
