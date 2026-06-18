# Codex Root Surface (`/.codex/`)

Repo-versionierte Codex-Konfigurationsfläche. Teil des CDB-Agent-Root-Surface-Systems.

## Struktur

| Pfad | Zweck |
|------|-------|
| `README.md` | Diese Datei — Surface-Beschreibung |
| `cdb_skills/` | Repo-versionierte Session-Skills für Codex (siehe `cdb_skills/README.md`) |

## Einstiegspunkte

- **Skills**: `cdb_skills/` — Vollständiger Skill-Katalog in `cdb_skills/README.md`
- **Onboarding-Intent**: `python -m tools.onboarding_orchestrator`
- **Skill Registry**: `.codex/cdb_skills/` — siehe auch `.cursor/skills/README.md` für Skill-Katalog

## Onboarding-Route

Bei `/onboarding`-Intent: `python -m tools.onboarding_orchestrator`

Default: Read-only Status Card. Kein `.env`, keine Secrets, kein Docker, kein Issue/PR ohne explizite Auswahl.

**Evidence-Abgrenzung nach /onboarding:** Antwort muss enthalten: Status, State, warnings, allowed_next_actions, check_scope, skipped_checks, Evidence-Abgrenzung (was geprüft, was nicht) und Safety-Grenzen. Ohne git/gh/check-Kommandos: "Repo-/Canon-Prüfung durchgeführt; GitHub-/Check-Live nicht geprüft."

## Safety Boundaries

- LR remains **NO-GO**
- `trade-capable` ist nicht `Live-Go`
- Keine Echtgeld-Transaktionen
- Keine Runtime-/Docker-/DB-/MCP-Mutationen
- Lokale Konfiguration (`config.toml`) bleibt unversioniert (maschinenspezifische Pfade)
