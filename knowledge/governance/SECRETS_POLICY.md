# Secrets Management Policy

**Issue:** #316
**Status:** Implemented
**Last Updated:** 2026-03-31 (reconciled to BLUE+RED canon, Issue #1411)

---

## Overview

Claire de Binare stores secrets **outside the repository** to prevent accidental exposure.

## Secret Locations

### Kanonischer Secrets-Pfad (Single Source of Truth)

```
~/Documents/.secrets/.cdb/
├── REDIS_PASSWORD
├── POSTGRES_PASSWORD
├── GRAFANA_PASSWORD
└── MEXC_API_KEY (optional)
```

Windows-Vollpfad: `C:\Users\<username>\Documents\.secrets\.cdb\`

Docker Compose greift via `SECRETS_PATH`-Umgebungsvariable auf diesen Pfad zu:
```
secrets:
  redis_password:
    file: ${SECRETS_PATH}/REDIS_PASSWORD
```

## Setup-Anleitung

### 1. Secrets-Verzeichnis anlegen

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\Documents\.secrets\.cdb"
```

### 2. Secrets erzeugen (PowerShell)

```powershell
# Option A: Automatisch via Rotate-Secrets.ps1 (empfohlen)
.\tools\secrets\Rotate-Secrets.ps1 apply

# Option B: Manuell
$secretsPath = "$env:USERPROFILE\Documents\.secrets\.cdb"
[System.IO.File]::WriteAllText("$secretsPath\REDIS_PASSWORD",    [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(24)))
[System.IO.File]::WriteAllText("$secretsPath\POSTGRES_PASSWORD", [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(24)))
[System.IO.File]::WriteAllText("$secretsPath\GRAFANA_PASSWORD",  [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(24)))
```

### 3. Stack starten (kanonischer BLUE+RED Pfad)

```powershell
docker network create cdb_network 2>$null
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```

### 4. Secrets verifizieren

```powershell
# Dateien vorhanden?
ls "$env:USERPROFILE\Documents\.secrets\.cdb"

# Nicht im Repo-Index?
git ls-files | Select-String "Documents|\.secrets"
# Erwartet: kein Output
```

## Was in Git erlaubt ist

| Datei | Status | Zweck |
|-------|--------|-------|
| `.env.example` | ✅ Tracked | Template mit Platzhaltern |
| `tools/secrets/secrets.manifest.json` | ✅ Tracked | Secret-Definition (keine Werte) |
| `~/Documents/.secrets/.cdb/*` | ❌ Niemals | Tatsächliche Secrets (außerhalb Repo) |
| `tools/secrets/.env.runtime` | ❌ Gitignored | Generiertes Runtime-Export (temporär) |
| `core/secrets.py` | ✅ Tracked | Secret-Ladelogik (keine Werte) |

## Verbotene Pfade (nicht mehr kanonisch)

| Pfad | Grund |
|------|-------|
| `.cdb_local/.secrets/` | Legacy-Pfad (vor Issue #316). Nicht verwenden. |
| Repo-`.secrets/` | Legacy-Pfad (vor Issue #316). Nicht verwenden. |
| `.env.runtime` als regulärer Operator-Standardfluss | Nur temporäres Export-Artefakt nach `Rotate-Secrets.ps1 export` |

## Git History Warning

⚠️ Ältere Versionen dieses Repos enthielten Secrets im Git-Verlauf.
Diese wurden aus dem Tracking entfernt, sind aber noch in der History.

**Empfehlung:** Alle Secrets nach einem Clone rotieren:
```powershell
.\tools\secrets\Rotate-Secrets.ps1 apply
```

## CI/CD Secrets

GitHub Actions Secrets werden gespeichert unter:
- Repository Settings → Secrets and variables → Actions

Erforderliche Secrets:
- `GEMINI_API_KEY` — Für Gemini AI Agent
- `CLAUDE_API_KEY` — Für Claude AI Agent

## Weiterführende Dokumentation

- **Rotation:** `tools/secrets/README.md` + `knowledge/governance/SECRET_ROTATION_POLICY.md`
- **Grafana-Incident (manuelles Passwort):** `knowledge/runbooks/GRAFANA_ADMIN_INCIDENT.md`
- **Rotation-Tool:** `tools/secrets/Rotate-Secrets.ps1`

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
