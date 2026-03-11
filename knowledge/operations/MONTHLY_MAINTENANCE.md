# Monthly Maintenance Runbook (Issue #291)

Standard-Wartungsprozess für Claire de Binare Infrastruktur.

## Cadence

- **Wann**: Erster Samstag jeden Monats
- **Wer**: DevOps / Platform Engineer
- **Dauer**: ~30 Minuten
- **Notification**: #alerts Slack-Channel vorab informieren

## Pre-Checks

### 1. Stack Health prüfen

```powershell
# Alle Container running?
docker compose -f infrastructure/compose/base.yml ps

# Health-Status
docker ps --format "table {{.Names}}\t{{.Status}}"
```

**Erwartetes Ergebnis**: Alle Services "healthy"

### 2. Disk Usage dokumentieren

```powershell
# Vor Maintenance dokumentieren
docker system df > maintenance_$(Get-Date -Format "yyyy-MM-dd")_before.txt
```

### 3. Volume Snapshot (KRITISCH)

```powershell
# Backup kritischer Volumes
docker run --rm -v claire_postgres_data:/data -v ${PWD}:/backup alpine tar czf /backup/postgres_backup_$(Get-Date -Format "yyyy-MM-dd").tar.gz /data
```

## Maintenance Tasks

### Safe Commands ✅

```powershell
# 1. Stopped containers entfernen
docker container prune -f

# 2. Dangling images entfernen
docker image prune -f

# 3. Build cache entfernen (optional)
docker builder prune -f

# 4. Dangling volumes (nur unnamed!)
docker volume prune -f

# ODER: Cleanup-Script verwenden
.\tools\cleanup\cleanup.ps1 -Execute -BuildCache
```

### NO-GO Commands ❌

| Command | Grund | Konsequenz |
|---------|-------|------------|
| `docker volume rm claire_postgres_data` | Löscht Datenbank | Datenverlust! |
| `docker system prune -a` | Löscht ALLES | Stack kaputt |
| `docker volume prune` ohne Check | Kann Named Volumes treffen | Datenverlust |
| `docker-compose down -v` | Löscht Volumes | Datenverlust! |

## Post-Checks

### 1. Stack Health verifizieren

```powershell
# Services neustarten falls nötig
docker compose -f infrastructure/compose/base.yml up -d

# Health prüfen
docker compose -f infrastructure/compose/base.yml ps
```

### 2. Disk Usage dokumentieren

```powershell
docker system df > maintenance_$(Get-Date -Format "yyyy-MM-dd")_after.txt
```

### 3. Cleanup-Dokumentation

- Diskspace freigegeben: X GB
- Images entfernt: X
- Container entfernt: X

## Artifact Storage

| Artifact | Location | Retention |
|----------|----------|-----------|
| Volume Backups | `./backups/` | 3 Monate |
| Maintenance Logs | `./logs/maintenance/` | 12 Monate |
| Disk Usage Reports | `./reports/` | 12 Monate |

## Checkliste

```markdown
### Pre-Maintenance
- [ ] Stack healthy (alle Container grün)
- [ ] Disk Usage dokumentiert
- [ ] Volume Backup erstellt
- [ ] Team informiert

### Maintenance
- [ ] Stopped containers entfernt
- [ ] Dangling images entfernt
- [ ] Build cache geleert (optional)
- [ ] Unnamed volumes entfernt

### Post-Maintenance
- [ ] Stack healthy
- [ ] Disk Usage dokumentiert
- [ ] Report erstellt
- [ ] Backup archiviert
```

## Rollback

Falls Stack nach Maintenance nicht startet:

```powershell
# 1. Logs prüfen
docker compose -f infrastructure/compose/base.yml logs

# 2. Falls Volume-Problem: Restore
docker run --rm -v claire_postgres_data:/data -v ${PWD}:/backup alpine tar xzf /backup/postgres_backup_DATUM.tar.gz -C /

# 3. Stack neu starten
docker compose -f infrastructure/compose/base.yml up -d
```

## Kalender-Reminder

```
Titel: Claire de Binare - Monthly Maintenance
Wann: Erster Samstag, 10:00 Uhr
Wiederholen: Monatlich
Notizen: Runbook: docs/ops/MONTHLY_MAINTENANCE.md
```
