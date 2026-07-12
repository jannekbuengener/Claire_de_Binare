# Gemini Root Surface (`/.gemini/`)

Repo-versionierte Gemini-Konfigurationsfläche. Teil des CDB-Agent-Root-Surface-Systems.

## Wichtige Dateien

| Datei | Zweck |
|-------|-------|
| `README.md` | Diese Datei — Surface-Beschreibung |
| `settings.json` | Gemini-IDE-Einstellungen (lokale Pfade ggf. anpassen) |
| `onboarding.md` | Onboarding-Router für Gemini-Agenten (siehe auch `GEMINI.md` im Repo-Root) |

## Einstiegspunkte

- **Gemini-Bootloader**: [`GEMINI.md`](../GEMINI.md) (Repo-Root) — primärer Einstiegspunkt mit Read-Order, Tool-First-Pflicht und Onboarding-Intent-Router.
- **Onboarding-Intent**: Siehe `onboarding.md` in diesem Verzeichnis oder `GEMINI.md` §6.
- **Canonical Registry**: [`agents/AGENTS.md`](../agents/AGENTS.md)

## Onboarding-Route

Bei `/onboarding`-Intent: `python -m tools.onboarding_orchestrator`

Default: Read-only Status Card. Kein `.env`, keine Secrets, kein Docker, kein Issue/PR ohne explizite Auswahl.

## Evidence-Abgrenzung (Response Contract)

Nach `/onboarding` MUSS die Antwort enthalten:

| Feld | Erforderlich |
|------|-------------|
| Status, State | Ja |
| warnings, allowed_next_actions | Ja |
| check_scope, skipped_checks | Ja |
| Evidence-Abgrenzung (was geprüft, was nicht) | **Ja** |
| Safety-Grenzen | Ja |

**Wording-Regeln:**
- Ohne ausgeführte `git`/`gh`/`check`-Kommandos: "Repo-/Canon-Prüfung durchgeführt; GitHub-/Check-Live nicht geprüft."
- `CURRENT_STATUS.md` ist Engineering-Ledger, nicht Live-Wahrheit.
- LR-SSOT: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- `trade-capable` ist Board-/Stage-Kontext, kein Live-Go.
- Keine freie Management-Zusammenfassung ohne Evidence-Abgrenzung.

## Safety Boundaries

- LR remains **NO-GO**
- `trade-capable` ist nicht `Live-Go`
- Keine Live-Kapital-Autorisierung
- Keine Runtime-/Docker-/DB-/MCP-Mutationen
