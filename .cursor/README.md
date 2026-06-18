# Cursor Root Surface (`/.cursor/`)

Repo-versionierte Cursor-IDE-Konfigurationsfläche. Teil des CDB-Agent-Root-Surface-Systems.

## Struktur

| Pfad | Zweck |
|------|-------|
| `README.md` | Diese Datei — Surface-Beschreibung |
| `agents/` | Cursor-Subagent-Definitionen (Helper-Rollen; Delegation only) |
| `rules/` | Cursor-Regeln (Bootloader, Brain Evidence, Safety Boundaries) |
| `skills/` | Repo-versionierte Session-Skills für Cursor |
| `mcp.json` | MCP-Server-Konfiguration (Beispiel; lokale Secrets ggf. anpassen) |

## Einstiegspunkte

- **Subagent Registry**: `agents/README_CDB_CURSOR_SUBAGENTS.md`
- **Skills**: `skills/README.md` — Vollständiger Skill-Katalog
- **Rules**: `rules/` — Fail-closed session rules
- **Onboarding-Intent**: `python -m tools.onboarding_orchestrator`

## Onboarding-Route

Bei `/onboarding`-Intent: `python -m tools.onboarding_orchestrator`

Default: Read-only Status Card. Kein `.env`, keine Secrets, kein Docker, kein Issue/PR ohne explizite Auswahl.

## Safety Boundaries

- LR remains **NO-GO**
- `trade-capable` ist nicht `Live-Go`
- Keine Echtgeld-Transaktionen
- Keine Runtime-/Docker-/DB-/MCP-Mutationen
- Lokale Workspace-State-Dateien bleiben unversioniert
