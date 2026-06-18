# OpenCode Root Surface (`/.opencode/`)

Repo-versionierte OpenCode-Konfigurationsfläche. Teil des CDB-Agent-Root-Surface-Systems.

## Struktur

| Pfad | Zweck |
|------|-------|
| `README.md` | Diese Datei — Surface-Beschreibung |
| `skills/` | Repo-versionierte Session-Skills für OpenCode (siehe `skills/README.md`) |

## Einstiegspunkte

- **Skills**: `skills/README.md` — Vollständiger Skill-Katalog
- **Onboarding-Intent**: `python -m tools.onboarding_orchestrator`

## Onboarding-Route

Bei `/onboarding`-Intent: `python -m tools.onboarding_orchestrator`

Default: Read-only Status Card. Kein `.env`, keine Secrets, kein Docker, kein Issue/PR ohne explizite Auswahl.

**Evidence-Abgrenzung nach /onboarding:** Antwort muss enthalten: Status, State, warnings, allowed_next_actions, check_scope, skipped_checks, Evidence-Abgrenzung (was geprüft, was nicht) und Safety-Grenzen. Ohne git/gh/check-Kommandos: "Repo-/Canon-Prüfung durchgeführt; GitHub-/Check-Live nicht geprüft."

## Safety Boundaries

- LR remains **NO-GO**
- `trade-capable` ist nicht `Live-Go`
- Keine Echtgeld-Transaktionen
- Keine Runtime-/Docker-/DB-/MCP-Mutationen
- Lokale Skills in Quarantäne (`skills/.system/`, `skills/skillforge/`, `skills/mockexchange/`) bleiben unversioniert
