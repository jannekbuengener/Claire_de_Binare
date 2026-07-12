# VS Code Root Surface (`/.vscode/`)

Repo-versionierte VS-Code-Konfigurationsfläche. VS Code ist ein repo-backed Helper-Surface, keine Autorität.

## Wichtige Dateien

| Datei | Zweck |
|-------|-------|
| `README.md` | Diese Datei — Surface-Beschreibung |
| `extensions.json` | Empfohlene Extensions für das Repo |
| `settings.json` | Workspace-Einstellungen (CI/CD-Helfer, Formatierung, Suche) |

## Role

VS Code dient als **repo-backed Helper-Surface** für:
- Standard-Formatierung (Black, Ruff)
- CI/CD-Hilfs-Tasks (Emoji-Check, Auto-Fix)
- Extension-Empfehlungen
- Search/File-Watcher-Excludes

Keine Autorität für Governance-, Stage- oder LR-Entscheidungen.

## Onboarding-Route

Bei `/onboarding`-Intent: `python -m tools.onboarding_orchestrator`

Siehe auch: [`AGENTS.md`](../AGENTS.md), [`docs/onboarding/AGENT_ROOT_SURFACE_MATRIX.md`](../docs/onboarding/AGENT_ROOT_SURFACE_MATRIX.md)

## Safety Boundaries

- LR remains **NO-GO**
- `trade-capable` ist nicht `Live-Go`
- Keine Echtgeld-Transaktionen
- Keine Runtime-/Docker-/DB-/MCP-Mutationen
