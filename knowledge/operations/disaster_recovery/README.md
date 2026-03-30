# Disaster Recovery - Docker Volume Backup & Restore

**Location:** `knowledge/operations/disaster_recovery/`
**Status:** Active guidance — adapt paths to your environment

---

## Dokumentation

| File | Beschreibung | Verwendung |
|------|--------------|------------|
| **QUICK_START.md** | 3-Schritte Schnellanleitung | Nach Docker Neuinstallation |
| **RESTORE_GUIDE.md** | Ausführliche Schritt-für-Schritt Anleitung | Detaillierte Restore-Prozedur |
| **restore_volumes.ps1** | Automatisches Restore-Script | PowerShell ausführen |
| **verify_restore.ps1** | Verifications-Script | Nach Restore zur Validierung |

---

## Verwendungszweck

Diese Dokumentation beschreibt den **Docker Volume Backup und Restore Prozess** für CDB (Claire de Binare).

**Anwendungsfälle:**
- Docker Desktop Neuinstallation
- Migration auf neuen Rechner
- Disaster Recovery nach System-Crash
- Entwicklungsumgebung Reset

---

## Was wird gesichert

### Kritische Daten:
- **Grafana Dashboards** (Dashboards, Settings, Users)
- **Redis Datenbank** (Session State, Cache)
- **Prometheus Metriken** (Zeitreihen-Daten)
- **Loki Logs** (Aggregierte Log-Daten)

### Konfiguration:
- `.env` File
- Container/Volume/Network Listen

### PostgreSQL:
- Volume bleibt normalerweise erhalten bei Docker Neuinstallation
- Bei Migration: Manueller Export/Import empfohlen
- Bei Datenverlust: Fresh Init mit Schema

### Secrets (außerhalb Docker):
- Bleiben erhalten unter dem konfigurierten `SECRETS_PATH`
- Default: `~/Documents/.secrets/.cdb/`
- Enthalten: MEXC API Keys, Grafana/Postgres/Redis Passwords

---

## Quick Start (TL;DR)

**Nach Docker Neuinstallation:**

```powershell
# 1. Restore (2-3 Min)
cd <BACKUP_DIR>
.\restore_volumes.ps1

# 2. Stack starten (30-60 Sek)
cd <REPO_ROOT>
make docker-up

# 3. Verifizieren
.\verify_restore.ps1
```

**Details:** Siehe [QUICK_START.md](./QUICK_START.md)

---

## Backup-Prozess

### Kanonischer Weg (empfohlen):

```powershell
.\tools\cdb.ps1 backup
```

Sichert Postgres + Redis nach `F:\Claire_Backups` (konfigurierbar).

### Manuelles Volume-Backup:

```powershell
# 1. Backup-Verzeichnis erstellen
$BACKUP_DIR = "<BACKUP_LOCATION>\docker_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
mkdir $BACKUP_DIR

# 2. Volumes sichern
docker run --rm -v claire_de_binare_redis_data:/data -v ${BACKUP_DIR}:/backup alpine tar czf /backup/redis_data.tar.gz -C /data .
docker run --rm -v claire_de_binare_grafana_data:/data -v ${BACKUP_DIR}:/backup alpine tar czf /backup/grafana_data.tar.gz -C /data .
docker run --rm -v claire_de_binare_prom_data:/data -v ${BACKUP_DIR}:/backup alpine tar czf /backup/prometheus_data.tar.gz -C /data .
docker run --rm -v claire_de_binare_loki_data:/data -v ${BACKUP_DIR}:/backup alpine tar czf /backup/loki_data.tar.gz -C /data .

# 3. Config sichern
Copy-Item <REPO_ROOT>\.env ${BACKUP_DIR}\.env_backup

# 4. Dokumentieren
docker ps -a --format "{{.Names}}\t{{.Image}}\t{{.Status}}" > ${BACKUP_DIR}\container_list.txt
docker volume ls > ${BACKUP_DIR}\volume_list.txt
docker network ls > ${BACKUP_DIR}\network_list.txt
```

---

## Restore-Prozess

### Automatisch (empfohlen):
```powershell
cd <BACKUP_DIR>
.\restore_volumes.ps1
```

### Manuell:
Siehe [RESTORE_GUIDE.md](./RESTORE_GUIDE.md) für alle Commands.

---

## Verifikation

### Nach Restore ausführen:
```powershell
.\verify_restore.ps1
```

### Manuelle Checks:
```powershell
# Docker Version
docker --version
docker compose version

# Volumes existieren
docker volume ls

# Container laufen
docker ps

# Grafana Dashboards
# -> http://localhost:3000

# Redis Daten
docker exec cdb_redis redis-cli DBSIZE
```

---

## Bekannte Probleme & Lösungen

### Problem: PostgreSQL Mount-Fehler
**Symptom:**
```
error mounting "...schema.sql": not a directory
```

**Lösung:**
1. Prüfe `infrastructure/compose/compose.blue.yml`
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
docker run --rm -v claire_de_binare_grafana_data:/var/lib/grafana -v <BACKUP_DIR>\grafana_data:/backup alpine cp -r /backup/. /var/lib/grafana/
docker compose restart cdb_grafana
```

---

## Backup-Historie

> **Hinweis:** Die DR-Guidance in diesem Verzeichnis wurde ursprünglich anlässlich
> der Docker-Neuinstallation vom 2025-12-31 erstellt. Snapshot-spezifische Pfade
> (z.B. `D:\Dev\Backups\docker_reinstall_20251231_075507`) sind nicht mehr als
> aktiver Standard zu verstehen — die generischen Platzhalter oben gelten.

---

## Related Documentation

- [Stack Lifecycle](../../systems/STACK_LIFECYCLE.md) - Docker Stack Management

---

## Maintenance

**Empfohlene Backup-Frequenz:**
- **Täglich:** `make backup` (Postgres + Redis nach F:\Claire_Backups)
- **Vor Major Updates:** Manuelles Volume-Backup (alle Volumes)
- **Vor Docker Neuinstallation:** Manuelles Volume-Backup (wie oben dokumentiert)

**Retention:**
- Lokale Backups: 7 Tage
- Kritische Backups: 30 Tage
- Vor Major Releases: Permanent archivieren
