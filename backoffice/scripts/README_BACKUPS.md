# Backup-System - Claire de Binare

**Version**: 1.0.0
**Status**: ✅ Production-Ready
**Speicherort**: `F:\Claire_Backups\`
**Retention**: 14 Tage
**Automatisierung**: Pre-Session Hook

---

## 📋 Übersicht

Das Backup-System sichert automatisch vor jeder Claude Code Session:

1. **PostgreSQL-Datenbank** - Alle Trading-Daten (signals, orders, trades, positions, portfolio_snapshots)
2. **Git-Repository** - Vollständiger Code-Stand mit Metadaten

**Backup-Speicherorte**:
```
F:\Claire_Backups\
├── PostgreSQL\
│   ├── cdb_backup_2025-11-25_2227.sql
│   ├── cdb_backup_2025-11-25_1430.sql
│   └── backup_log.txt
└── Repository\
    ├── claire_repo_2025-11-25_2230_0e4fbd3.zip
    ├── claire_repo_2025-11-25_1430_6903fdf.zip
    └── backup_log.txt
```

---

## 🚀 Quick Start

### Automatische Backups (Standard)

Backups werden **automatisch vor jeder Session** erstellt via Pre-Session Hook:

```
backoffice/hooks/pre_session_backup.ps1
```

**Ausgabe beim Session-Start**:
```
=== Pre-Session: Automatische Backups ===

[1/2] PostgreSQL Backup...
      [✓] PostgreSQL: 245.67 KB

[2/2] Repository Backup...
      [✓] Repository: 0.68 MB | 0e4fbd3

=== Backups Complete ===
Gespeichert: F:\Claire_Backups\
```

### Manuelle Backups

**PostgreSQL-Backup**:
```powershell
# Einfaches Backup
pwsh -File backoffice/scripts/backup_postgres.ps1

# Mit Details
pwsh -File backoffice/scripts/backup_postgres.ps1 -Verbose

# Eigener Speicherort
pwsh -File backoffice/scripts/backup_postgres.ps1 -BackupRoot "D:\Backups\PostgreSQL"
```

**Repository-Backup**:
```powershell
# Einfaches Backup
pwsh -File backoffice/scripts/backup_repository.ps1

# Mit .env (ACHTUNG: Enthält Secrets!)
pwsh -File backoffice/scripts/backup_repository.ps1 -IncludeEnv

# Mit Docker Volumes
pwsh -File backoffice/scripts/backup_repository.ps1 -IncludeDockerVolumes

# Mit allen Optionen
pwsh -File backoffice/scripts/backup_repository.ps1 -IncludeEnv -IncludeDockerVolumes -Verbose
```

---

## 📊 PostgreSQL Backup

### Was wird gesichert?

**5 kritische Tabellen**:
- `signals` - Trading-Signale
- `orders` - Order-Historie
- `trades` - Ausgeführte Trades
- `positions` - Offene Positionen
- `portfolio_snapshots` - Portfolio-Historie

**Format**: SQL-Dump (Plain Text, UTF-8)

### Dateiname-Schema

```
cdb_backup_YYYY-MM-DD_HHMM.sql
```

**Beispiel**:
```
cdb_backup_2025-11-25_2227.sql
→ Backup vom 25. Nov 2025 um 22:27 Uhr
```

### Restore (PostgreSQL Backup wiederherstellen)

```powershell
# 1. Container stoppen
docker compose stop cdb_postgres

# 2. Backup-Datei auswählen
$backupFile = "F:\Claire_Backups\PostgreSQL\cdb_backup_2025-11-25_2227.sql"

# 3. Restore via Docker
docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare < $backupFile

# 4. Container neu starten
docker compose start cdb_postgres

# 5. Validieren
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "\dt"
# → Sollte 5 Tabellen anzeigen: signals, orders, trades, positions, portfolio_snapshots
```

### Validierung

Script validiert automatisch:
- ✅ PostgreSQL-Header vorhanden (`PostgreSQL database dump`)
- ✅ Alle 5 Tabellen im Backup (`CREATE TABLE signals`, etc.)
- ✅ Backup-Größe > 0 KB

**Warnungen**:
- Fehlende Tabellen im Backup
- Backup-Datei könnte korrupt sein

---

## 📦 Repository Backup

### Was wird gesichert?

**1. Git Repository (git archive)**
- Alle versionierten Dateien (HEAD)
- **OHNE** .env (Secrets!)
- **OHNE** untracked files
- Format: ZIP

**2. Git-Metadaten**
- Branch, Commit-Hash, Commit-Message
- Autor, Datum
- Remote-URLs
- Anzahl Commits
- Uncommitted Changes Count

**Optional**:
- `.env` Datei (mit `-IncludeEnv`)
- Docker Volumes (mit `-IncludeDockerVolumes`)

### Dateiname-Schema

```
claire_repo_YYYY-MM-DD_HHMM_COMMITHASH.zip
```

**Beispiel**:
```
claire_repo_2025-11-25_2230_0e4fbd3.zip
→ Backup vom 25. Nov 2025 um 22:30 Uhr
→ Commit: 0e4fbd3
```

### Restore (Repository wiederherstellen)

```powershell
# 1. Backup-Datei auswählen
$backupFile = "F:\Claire_Backups\Repository\claire_repo_2025-11-25_2230_0e4fbd3.zip"

# 2. Zielverzeichnis erstellen
$restoreDir = "C:\Temp\Claire_Restore"
New-Item -ItemType Directory -Path $restoreDir -Force

# 3. ZIP entpacken
Expand-Archive -Path $backupFile -DestinationPath $restoreDir

# 4. Git-Metadata lesen
Get-Content "$restoreDir\git_metadata.txt"

# 5. Repository.zip extrahieren
Expand-Archive -Path "$restoreDir\repository.zip" -DestinationPath "$restoreDir\repo"

# 6. Optional: .env wiederherstellen (falls im Backup enthalten)
if (Test-Path "$restoreDir\.env.backup") {
    Copy-Item "$restoreDir\.env.backup" "$restoreDir\repo\.env"
}
```

---

## 🔧 Konfiguration

### Backup-Retention ändern

**Standard**: 14 Tage

**Ändern**:
```powershell
# In backup_postgres.ps1 oder backup_repository.ps1
param(
    [int]$RetentionDays = 30  # Auf 30 Tage ändern
)
```

### Speicherort ändern

**Standard**: `F:\Claire_Backups\`

**Ändern**:
```powershell
# Option 1: Über Parameter
pwsh -File backup_postgres.ps1 -BackupRoot "D:\Backups"

# Option 2: Script editieren
param(
    [string]$BackupRoot = "D:\My_Backups\PostgreSQL"
)
```

### Pre-Session Hook deaktivieren

```powershell
# Pre-Session Hook umbenennen (damit er nicht mehr ausgeführt wird)
Rename-Item backoffice/hooks/pre_session_backup.ps1 `
    backoffice/hooks/pre_session_backup.ps1.disabled
```

---

## 📊 Backup-Logs

Beide Scripts schreiben Logs:

**PostgreSQL Log**: `F:\Claire_Backups\PostgreSQL\backup_log.txt`
```
[2025-11-25 22:27:38] Backup erfolgreich
  Datei: F:\Claire_Backups\PostgreSQL\cdb_backup_2025-11-25_2227.sql
  Größe: 245.67 KB
  Tabellen: 5 / 5
  Retention: Gelöscht 0 alte Backups
```

**Repository Log**: `F:\Claire_Backups\Repository\backup_log.txt`
```
[2025-11-25 22:30:15] Repository Backup erfolgreich
  Datei: F:\Claire_Backups\Repository\claire_repo_2025-11-25_2230_0e4fbd3.zip
  Größe: 0.68 MB
  Branch: festive-shamir
  Commit: 0e4fbd3
  .env included: No
  Volumes included: No
  Retention: Gelöscht 0 alte Backups
```

---

## 🚨 Troubleshooting

### PostgreSQL Backup schlägt fehl

**Problem 1**: Container nicht running
```
[ERROR] PostgreSQL Container konnte nicht gestartet werden!
```

**Lösung**:
```powershell
# Container manuell starten
docker compose up -d cdb_postgres

# Warten bis healthy
Start-Sleep -Seconds 5

# Backup erneut ausführen
pwsh -File backoffice/scripts/backup_postgres.ps1
```

**Problem 2**: Fehlende Credentials in .env
```
[ERROR] Fehlende PostgreSQL Credentials in .env!
```

**Lösung**:
```powershell
# .env Datei prüfen
Get-Content .env | Select-String "POSTGRES"

# Erwartete Variablen:
# POSTGRES_USER=claire_user
# POSTGRES_PASSWORD=claire_db_secret_2024
# POSTGRES_DB=claire_de_binare
```

---

### Repository Backup schlägt fehl

**Problem 1**: Nicht in Git-Repository
```
[ERROR] Nicht in einem Git-Repository!
```

**Lösung**:
```powershell
# In Repository-Root wechseln
cd C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Cleanroom

# Erneut ausführen
pwsh -File backoffice/scripts/backup_repository.ps1
```

**Problem 2**: Uncommitted Changes Warning
```
[WARN] WARNUNG: Uncommitted changes gefunden!
[WARN]   Anzahl geänderter Dateien: 4
```

**Lösung**:
```powershell
# Option 1: Changes committen
git add .
git commit -m "save work"

# Option 2: Backup trotzdem erstellen (wartet 3 Sekunden)
# → Einfach warten, Script fährt automatisch fort

# Option 3: Mit -Force Flag (keine Warnung)
pwsh -File backoffice/scripts/backup_repository.ps1 -Force
```

---

### Backup-Speicherplatz prüfen

```powershell
# PostgreSQL Backups
Get-ChildItem F:\Claire_Backups\PostgreSQL -Filter "*.sql" |
    Measure-Object -Property Length -Sum |
    Select-Object @{N="Total Size (MB)";E={[math]::Round($_.Sum / 1MB, 2)}}, Count

# Repository Backups
Get-ChildItem F:\Claire_Backups\Repository -Filter "*.zip" |
    Measure-Object -Property Length -Sum |
    Select-Object @{N="Total Size (MB)";E={[math]::Round($_.Sum / 1MB, 2)}}, Count
```

**Erwartete Größen**:
- PostgreSQL: ~200-500 KB pro Backup
- Repository: ~0.5-1 MB pro Backup
- **14 Tage**: ~20 MB gesamt

---

## ✅ Best Practices

### Empfohlene Backup-Strategie

**Automatisch (Pre-Session Hook)**:
- ✅ PostgreSQL: Ja
- ✅ Repository: Ja (ohne .env)
- ⏰ Frequenz: Vor jeder Session

**Manuell (bei wichtigen Meilensteinen)**:
```powershell
# Full Backup mit allem
pwsh -File backoffice/scripts/backup_repository.ps1 -IncludeEnv -IncludeDockerVolumes

# PostgreSQL explizit
pwsh -File backoffice/scripts/backup_postgres.ps1 -Verbose
```

**Beispiele für manuelle Backups**:
- Vor Production-Deployment
- Nach erfolgreichen Paper-Tests
- Vor größeren Refactorings
- Nach wichtigen Konfigurationsänderungen

### Sicherheit

**⚠️ WICHTIG - .env Backups**:

```powershell
# .env enthält Secrets - NUR wenn nötig sichern!
pwsh -File backoffice/scripts/backup_repository.ps1 -IncludeEnv

# Gesichert wird:
# - MEXC_API_KEY / MEXC_API_SECRET
# - POSTGRES_PASSWORD
# - REDIS_PASSWORD
# - GRAFANA_PASSWORD

# Speicherort F:\ sollte verschlüsselt sein (BitLocker)
```

**Backup-Zugriffskontrolle**:
- F:\ Drive: Nur lokaler Admin-Zugriff
- Keine Cloud-Sync (Dropbox, OneDrive, etc.)
- Regelmäßige externe Kopie auf verschlüsseltem USB-Stick

---

## 📚 Weiterführende Dokumentation

| Dokument | Zweck |
|----------|-------|
| [PROJECT_STATUS.md](../PROJECT_STATUS.md) | Backup-Strategie-Konzept |
| [DECISION_LOG.md](../docs/DECISION_LOG.md) | ADR-003: Backup & Recovery |
| [docker-compose.yml](../../docker-compose.yml) | Volume-Definitionen |

---

## 🎯 Erfolgskriterien

**N1 Paper-Test Phase**:
- ✅ Täglich vor Session: Auto-Backup via Hook
- ✅ 14-Tage-Retention: Automatische Bereinigung
- ✅ Backup-Größe: <1 MB pro Tag
- ✅ Restore-Zeit: <5 Minuten
- ✅ Validation: Automatisch bei jedem Backup

**Production**:
- [ ] Externe Backup-Kopie (verschlüsselter USB-Stick)
- [ ] Wöchentliche Restore-Tests
- [ ] Off-Site Backup (Cloud-Storage verschlüsselt)

---

**Version**: 1.0.0
**Letzte Aktualisierung**: 2025-11-25
**Autor**: Claude (AI) + Jannek
**Status**: ✅ Production-Ready
