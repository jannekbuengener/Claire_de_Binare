# GitHub Repository Secrets Setup

**Datum:** 2025-12-29 03:53 CET
**Session Lead:** Claude Opus 4.5
**Repository:** jannekbuengener/Claire_de_Binare

---

## Zweck

GitHub Repository Secrets ermöglichen sichere Secret-Handhabung in GitHub Actions Workflows. Diese Secrets werden für E2E-Tests und CI/CD-Pipelines benötigt.

---

## Gesetzte Secrets

| Secret Name | Gesetzt am | Zweck |
|-------------|------------|-------|
| `REDIS_PASSWORD` | 2025-12-29T02:53:18Z | Redis-Authentifizierung für CI/CD |
| `POSTGRES_PASSWORD` | 2025-12-29T02:53:22Z | PostgreSQL-Authentifizierung für CI/CD |
| `GRAFANA_PASSWORD` | 2025-12-29T02:53:26Z | Grafana Admin-Passwort für CI/CD |

**Bereits vorhandene Secrets:**
- `CDB_GITHUB_TOKEN` (seit 2025-12-15)
- `CLAUDE_CODE_OAUTH_TOKEN` (seit 2025-12-27)

---

## Architektur

### Lokale Entwicklung
```
~/Documents/.secrets/.cdb/
├── REDIS_PASSWORD
├── POSTGRES_PASSWORD
├── GRAFANA_PASSWORD
├── GRAFANA_API_KEY
├── MEXC_API_KEY.txt
├── MEXC_API_SECRET.txt
├── MEXC_TRADE_API_KEY.txt
└── MEXC_TRADE_API_SECRET.txt
```

Docker Compose lädt Secrets via `${SECRETS_PATH}` Interpolation.

### GitHub Actions
```yaml
env:
  SECRETS_PATH: ${{ github.workspace }}/.ci-secrets

steps:
  - name: Create CI Secrets Directory
    run: |
      mkdir -p $SECRETS_PATH
      echo "${{ secrets.REDIS_PASSWORD }}" > $SECRETS_PATH/REDIS_PASSWORD
      echo "${{ secrets.POSTGRES_PASSWORD }}" > $SECRETS_PATH/POSTGRES_PASSWORD
      echo "${{ secrets.GRAFANA_PASSWORD }}" > $SECRETS_PATH/GRAFANA_PASSWORD
      chmod 600 $SECRETS_PATH/*
```

---

## Validierung

### Lokal (PowerShell)
```powershell
# Alle GitHub Secrets auflisten
gh secret list --repo jannekbuengener/Claire_de_Binare
```

### Erwartete Ausgabe
```
CDB_GITHUB_TOKEN        2025-12-15T02:32:35Z
CLAUDE_CODE_OAUTH_TOKEN 2025-12-27T02:33:09Z
GRAFANA_PASSWORD        2025-12-29T02:53:26Z
POSTGRES_PASSWORD       2025-12-29T02:53:22Z
REDIS_PASSWORD          2025-12-29T02:53:18Z
```

---

## Wartung

### Secret-Rotation
```powershell
# Neues Passwort generieren
$newPassword = [Convert]::ToBase64String((1..24 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])

# Lokal speichern (CRLF-safe!)
[System.IO.File]::WriteAllBytes("$env:SECRETS_PATH\REDIS_PASSWORD", [System.Text.Encoding]::ASCII.GetBytes($newPassword))

# GitHub Secret aktualisieren
$newPassword | gh secret set REDIS_PASSWORD --repo jannekbuengener/Claire_de_Binare

# Stack mit neuen Volumes neu starten
docker compose down -v
docker compose up -d
```

### Secret löschen
```powershell
gh secret delete SECRET_NAME --repo jannekbuengener/Claire_de_Binare
```

---

## Sicherheitshinweise

1. **Secrets NIEMALS in Logs ausgeben** - GitHub maskiert sie automatisch, aber `echo ${{ secrets.X }}` ist trotzdem riskant
2. **CRLF-Problematik** - Windows schreibt `\r\n`, Docker erwartet `\n`. Immer `WriteAllBytes` oder `-NoNewline` verwenden
3. **Keine Fallback-Passwörter** - Workflow soll fehlschlagen wenn Secrets fehlen
4. **Workflow-Validierung** - Immer prüfen ob Secret-Dateien existieren und non-empty sind

---

## Referenzen

- [Docker Secrets Blueprint Session](../logs/sessions/2025-12-29-docker-secrets-blueprint.md)
- [E2E Workflow](.github/workflows/e2e-tests.yml)
- [Secrets Policy](governance/SECRETS_POLICY.md)
