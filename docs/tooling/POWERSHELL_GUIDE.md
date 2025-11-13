---
applyTo:
  - "scripts/**/*.ps1"
## - "*.ps1"

# PowerShell-Skripte – Richtlinien

## Stil
- Nutze `Set-StrictMode -Version Latest` und `ErrorActionPreference = 'Stop'` zu Beginn.
- Parameter immer mit `[CmdletBinding()]` und `Param()` deklarieren.
- Cmdlets statt Aliase verwenden (`Get-ChildItem` statt `ls`).

## Sicherheit
- Keine Klartext-Secrets oder Zugangsdaten. Variablen als Platzhalter (`$Env:MEXC_API_KEY`).
- Bei Remote-Befehlen Authentifizierung/Scopes dokumentieren.

## Logging & Output
- Verwende `Write-Verbose`/`Write-Information` mit strukturierter Nachricht (`key=value`).
- Erfolgs-/Fehlerstatus klar mit `Write-Host "✅ ..."` bzw. `Write-Error` kennzeichnen.
- Skript-Ende mit Exitcode (`0` Erfolg, `1` Fehler).

## Tests
- Beispielaufrufe in Kommentarblock dokumentieren.
- Empfohlene Checks: `pwsh -NoLogo -File <script> -WhatIf` (falls unterstützt).
