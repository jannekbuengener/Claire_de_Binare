# CDB GitHub Triage (Cursor SDK)

Terminal-CLI für wiederkehrende GitHub-Triage im CDB-Repo — ohne neuen Cursor-Chat. Nutzt `@cursor/sdk` mit **local runtime** gegen das Repo-Root (`cwd` = zwei Ebenen über `tools/cursor-sdk/`).

## Voraussetzungen

- Node.js 20+
- [`CURSOR_API_KEY`](https://cursor.com/dashboard/integrations) (User- oder Service-Account-Key)
- `gh auth status` muss im CDB-Repo funktionieren

## Setup

```powershell
cd D:\Dev\Workspaces\Repos\Claire_de_Binare\tools\cursor-sdk
copy .env.example .env   # CURSOR_API_KEY eintragen
npm install
```

## Nutzung

```powershell
# Standard-Triage (liest CURRENT_STATUS.md, gh pr/issue list, Top-3 Aktionen)
npm run triage

# Eigener Fokus
npm run triage -- --prompt "Fokus: #3612 und offene Dependabot-PRs"

# Follow-up mit Kontext vom letzten Lauf (Agent.resume)
npm run triage -- --follow-up "Welche blockierten PRs brauchen nur Rebase?"

# Neuen Agent starten (State ignorieren)
npm run triage -- --fresh
```

## Verhalten

- **Nur Triage** — kein Merge, kein Issue-Kommentar, kein Push (Default-Prompt).
- **State** — `.state.json` speichert `agentId` und `lastRunId` für Resume.
- **Exit-Codes** — `0` finished, `1` Startup-Fehler, `2` Run-Status error, `75` retryable startup failure.
- **`settingSources: []`** — kein versehentliches Laden von Team/MDM-Settings.

## Dateien

| Datei | Zweck |
|-------|-------|
| `src/cdb-triage.ts` | CLI-Einstieg |
| `.state.json` | Persistierter Agent-State (gitignored) |
| `.env` | Lokaler API-Key (gitignored) |
