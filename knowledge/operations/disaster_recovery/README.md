# Disaster Recovery - Docker Reinstallation

**Location:** `Claire_de_Binare/knowledge/operations/disaster_recovery/`  
**Last Updated:** 2025-12-31  
**Status:** Production-Ready

---

## 📚 Dokumentation

| File | Beschreibung | Verwendung |
|------|--------------|------------|
| **QUICK_START.md** | 🚀 3-Schritte Schnellanleitung | Nach Docker Neuinstallation |
| **RESTORE_GUIDE.md** | 📖 Historischer Event-Snapshot (2025-12-31) | Hintergrund-Referenz |
| **restore_volumes.ps1** | ⚡ Historisches Restore-Script (2025-12-31-Snapshot) | Nicht aktive Kanonik — siehe `make restore` |
| **verify_restore.ps1** | ✅ Historisches Verifikations-Script (2025-12-31-Snapshot) | Nicht aktive Kanonik |
| **create_backup.ps1** | 💾 Historisches Backup-Script (2025-12-31-Snapshot) | Nicht aktive Kanonik — siehe `make backup` |

---

## 🎯 Verwendungszweck

Diese Dokumentation beschreibt den **Docker Volume Backup und Restore Prozess** für CDB (Claire de Binare).

**Anwendungsfälle:**
- Docker Desktop Neuinstallation
- Migration auf neuen Rechner
- Disaster Recovery nach System-Crash
- Entwicklungsumgebung Reset

---

## 💾 Was wird gesichert

### Aktueller Canon (`make backup`):

- ✅ **PostgreSQL** (SQL dump via `pg_dumpall`)
- ✅ **Redis** (`dump.rdb`)
- ◻️ **SurrealDB** (optional, wenn aktiv)

Backup-Root: `F:\Claire_Backups` — Retention: 14 Tage (automatisch via Windows Task `Claire_Hourly_Backup`, siehe `docs/runbooks/BACKUP_AUTOMATION.md`)

### Historischer Scope (2025-12-31 — nicht aktiver Canon):

Der Snapshot-Backup-Satz vom 2025-12-31 enthielt: Grafana-Volumes (~109MB), Prometheus-Metriken (~2MB), Loki-Logs (~671B), Claude Memory (~3KB). Diese Volumes sind kein Teil des aktuellen `make backup`-Scopes.

### Secrets (außerhalb Docker):
- ✅ Bleiben erhalten: lokales Secrets-Verzeichnis (host-spezifisch, außerhalb Docker)
- Pfad: konfigurierbar über `SECRETS_PATH` — Standard: `~/Documents/.secrets/.cdb/`

---

## 🚀 Quick Start (TL;DR)

**Nach Docker Neuinstallation:**

```powershell
# 1. Verfügbare Backups anzeigen
make restore
# → listet Archive in F:\Claire_Backups

# 2. Restore mit konkretem Backup-Namen ausführen (2-3 Min)
powershell.exe -ExecutionPolicy Bypass -File infrastructure/scripts/restore_all.ps1 -BackupName cdb_backup_YYYYMMDD_HHMMSS
# → Backup-Name aus Schritt 1 einsetzen

# 3. Stack starten (30-60 Sek)
make docker-up

# 4. Restore verifizieren — Redis + Postgres
docker exec cdb_redis redis-cli DBSIZE
docker exec cdb_postgres psql -U postgres -c "\dt" 2>&1 | Select-String "public"
```

**Details:** Siehe [QUICK_START.md](./QUICK_START.md)

---

## 📋 Backup-Prozess

### Kanonischer Einstieg:

```powershell
# Backup erstellen (Postgres + Redis → F:\Claire_Backups)
make backup
# → infrastructure/scripts/backup_all.ps1

# Backup-Aktualität prüfen
make backup-health
# → infrastructure/scripts/backup_health_check.ps1
```

### Automatisches Backup (aktiv):
- Windows Task `Claire_Hourly_Backup` via `infrastructure/scripts/setup_backup_task.ps1` — stündlich nach `F:\Claire_Backups`, Retention 14 Tage
- Details: `docs/runbooks/BACKUP_AUTOMATION.md`

### Manuelle Volume-Befehle (historische Referenz, 2025-12-31-Snapshot):

```powershell
# Direktes Volume-Backup (Hintergrund-Referenz, nicht kanonischer Einstieg)
$BACKUP_DIR = "D:\Dev\Backups\docker_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
mkdir $BACKUP_DIR

docker run --rm -v claire_de_binare_redis_data:/data -v ${BACKUP_DIR}:/backup alpine tar czf /backup/redis_data.tar.gz -C /data .
docker run --rm -v claire_de_binare_grafana_data:/data -v ${BACKUP_DIR}:/backup alpine tar czf /backup/grafana_data.tar.gz -C /data .
docker run --rm -v claire_de_binare_prom_data:/data -v ${BACKUP_DIR}:/backup alpine tar czf /backup/prometheus_data.tar.gz -C /data .
docker run --rm -v claire_de_binare_loki_data:/data -v ${BACKUP_DIR}:/backup alpine tar czf /backup/loki_data.tar.gz -C /data .
docker run --rm -v claude-memory:/data -v ${BACKUP_DIR}:/backup alpine tar czf /backup/claude_memory.tar.gz -C /data .
Copy-Item D:\Dev\Workspaces\Repos\Claire_de_Binare\.env ${BACKUP_DIR}\.env_backup
docker ps -a --format "{{.Names}}\t{{.Image}}\t{{.Status}}" > ${BACKUP_DIR}\container_list.txt
docker volume ls > ${BACKUP_DIR}\volume_list.txt
docker network ls > ${BACKUP_DIR}\network_list.txt
```

---

## 🔧 Restore-Prozess

### Kanonischer Einstieg (empfohlen):
```powershell
# Schritt 1: verfügbare Backups anzeigen
make restore
# → listet Archive in F:\Claire_Backups

# Schritt 2: Restore mit konkretem Namen ausführen
powershell.exe -ExecutionPolicy Bypass -File infrastructure/scripts/restore_all.ps1 -BackupName cdb_backup_YYYYMMDD_HHMMSS
```

### Hintergrund-Referenz:
Siehe [RESTORE_GUIDE.md](./RESTORE_GUIDE.md) — historischer Event-Snapshot vom 2025-12-31-Docker-Reinstall

---

## ✅ Verifikation nach Restore

### Restore-Erfolg prüfen (manuelle DB-Checks):

```powershell
# Redis — Schlüsselanzahl (> 0 erwartet)
docker exec cdb_redis redis-cli DBSIZE

# Postgres — Tabellen prüfen
docker exec cdb_postgres psql -U postgres -c "\dt" 2>&1 | Select-String "public"
```

### Stack-Health:

```powershell
# Container laufen
docker ps

# Stack-Health (BLUE+RED)
make docker-health
```

### Backup-Frischecheck (separat — prüft Backup-Aktualität, nicht Restore-Erfolg):

```powershell
make backup-health
# → infrastructure/scripts/backup_health_check.ps1
# → Prüft ob aktuelles Backup vorhanden und aktuell ist; NICHT ob Restore erfolgreich war
```

---

## 🚨 Bekannte Probleme & Lösungen

### Problem: PostgreSQL Mount-Fehler
**Symptom:**
```
error mounting "...schema.sql": not a directory
```

**Ursache:** Alte absolute Pfade in Compose Files (C:\Users\... statt D:\Dev\...)

**Lösung:**
1. Prüfe `infrastructure/compose/base.yml`
2. Entferne oder update absolute Pfade
3. Volume-Namen sollten ausreichen

### Problem: Container crashen nach Restore
**Check:**
```powershell
docker compose logs <container_name>
```

**Häufige Ursachen:**
- Falsche Pfade in .env
- Fehlende Secrets
- Inkompatible Volume-Daten

### Problem: Grafana zeigt keine Dashboards
**Lösung:**
```powershell
docker volume rm claire_de_binare_grafana_data
docker volume create claire_de_binare_grafana_data
docker run --rm -v claire_de_binare_grafana_data:/var/lib/grafana -v D:\Dev\Backups\...\grafana_data:/backup alpine cp -r /backup/. /var/lib/grafana/
docker compose restart cdb_grafana
```

---

## 📊 Backup-Historie

| Datum | Event | Backup Location | Size | Status |
|-------|-------|----------------|------|--------|
| 2025-12-31 | Docker Neuinstallation | `docker_reinstall_20251231_075507` | 112MB | ✅ Erfolgreich |

---

## 🔗 Related Documentation

- [WORKSPACE_LAYOUT.md](../WORKSPACE_LAYOUT.md) - Workspace-Struktur
- [Stack Lifecycle](../../systems/STACK_LIFECYCLE.md) - Docker Stack Management
- [Setup Guide](../../archive/docs_legacy/SETUP_GUIDE.md) - Initial Setup

---

## 📝 Maintenance

**Empfohlene Backup-Frequenz:**
- **Täglich:** Automatisches Backup aktiv — Windows Task `Claire_Hourly_Backup` (siehe `docs/runbooks/BACKUP_AUTOMATION.md`)
- **Vor Major Updates:** Manuelles Backup
- **Vor Docker Neuinstallation:** Manuelles Backup (wie hier dokumentiert)

**Retention:**
- Lokale Backups: 7 Tage
- Kritische Backups: 30 Tage
- Vor Major Releases: Permanent archivieren

---

**Erstellt:** 2025-12-31  
**Autor:** Claude (Disaster Recovery Documentation)  
**Basierend auf:** Docker Reinstall 2025-12-31 07:55
