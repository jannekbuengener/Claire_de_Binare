# Secrets Management Policy

**Issue:** #316
**Status:** Implemented
**Last Updated:** 2026-03-31 (reconciled to BLUE+RED canon, Issue #1411)

> Kanonische Version: [`knowledge/governance/SECRETS_POLICY.md`](../knowledge/governance/SECRETS_POLICY.md)

---

## Overview

Claire de Binare stores secrets **outside the repository** to prevent accidental exposure.

## Kanonischer Secrets-Pfad

```
~/Documents/.secrets/.cdb/
├── REDIS_PASSWORD
├── POSTGRES_PASSWORD
├── GRAFANA_PASSWORD
└── MEXC_API_KEY (optional)
```

Windows-Vollpfad: `C:\Users\<username>\Documents\.secrets\.cdb\`

Docker Compose greift via `SECRETS_PATH`-Umgebungsvariable auf diesen Pfad zu:
```yaml
secrets:
  redis_password:
    file: ${SECRETS_PATH}/REDIS_PASSWORD
```

## Setup-Anleitung

### 1. Secrets-Verzeichnis anlegen und Secrets erzeugen

```powershell
# Option A (empfohlen): Rotate-Secrets.ps1
.\tools\secrets\Rotate-Secrets.ps1 apply

# Option B (manuell)
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\Documents\.secrets\.cdb"
[System.IO.File]::WriteAllText("$env:USERPROFILE\Documents\.secrets\.cdb\REDIS_PASSWORD",    [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(24)))
[System.IO.File]::WriteAllText("$env:USERPROFILE\Documents\.secrets\.cdb\POSTGRES_PASSWORD", [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(24)))
[System.IO.File]::WriteAllText("$env:USERPROFILE\Documents\.secrets\.cdb\GRAFANA_PASSWORD",  [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(24)))
```

### 2. Stack starten (kanonischer BLUE+RED Pfad)

```powershell
docker network create cdb_network 2>$null
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```

## Was in Git erlaubt ist

| Datei | Status | Zweck |
|-------|--------|-------|
| `.env.example` | ✅ Tracked | Template mit Platzhaltern |
| `tools/secrets/secrets.manifest.json` | ✅ Tracked | Secret-Definition (keine Werte) |
| `~/Documents/.secrets/.cdb/*` | ❌ Niemals | Tatsächliche Secrets (außerhalb Repo) |
| `tools/secrets/.env.runtime` | ❌ Gitignored | Generiertes Runtime-Export (temporär) |

## Verbotene Pfade (Legacy)

| Pfad | Grund |
|------|-------|
| `.cdb_local/.secrets/` | Legacy-Pfad (vor Issue #316). Nicht verwenden. |
| Repo-`.secrets/` | Legacy-Pfad (vor Issue #316). Nicht verwenden. |

## Git History Warning

⚠️ Ältere Versionen enthielten Secrets in der Git-History.
Diese wurden aus dem Tracking entfernt, sind aber noch in der History.

**Empfehlung:** Alle Secrets nach einem Clone rotieren:
```powershell
.\tools\secrets\Rotate-Secrets.ps1 apply
```

## CI/CD Secrets

GitHub Actions Secrets: Repository Settings → Secrets and variables → Actions

Erforderliche Secrets:
- `GEMINI_API_KEY` — Für Gemini AI Agent
- `CLAUDE_API_KEY` — Für Claude AI Agent

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
