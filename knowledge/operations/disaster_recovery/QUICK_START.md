# QUICK START - Nach Docker Neuinstallation

> **Hinweis:** Ersetze `<BACKUP_DIR>` durch den Pfad deines aktuellsten Backups
> und `<REPO_ROOT>` durch den Pfad zum Claire_de_Binare Repository.

---

## 3-Schritte Restore (Automatisch)

### 1. Docker verifizieren
```powershell
docker --version
docker compose version
```

### 2. Volumes + Config automatisch wiederherstellen
```powershell
cd <BACKUP_DIR>
.\restore_volumes.ps1
```
Dauer: ~2-3 Minuten

### 3. Stack starten
```powershell
cd <REPO_ROOT>
make docker-up
```
Dauer: ~30-60 Sekunden

### 4. Verifizieren
```powershell
cd <BACKUP_DIR>
.\verify_restore.ps1
```

---

## Erfolgs-Checks

1. **Docker läuft:**
   ```powershell
   docker ps
   ```
   Sollte zeigen: alle BLUE- und RED-Services (grafana, redis, postgres, signal, ws, risk, ...)

2. **Grafana Dashboards:**
   - http://localhost:3000
   - Login: admin / (siehe Secrets)

3. **Redis Daten:**
   ```powershell
   docker exec cdb_redis redis-cli DBSIZE
   ```
   Sollte > 0 sein

4. **Container Health:**
   ```powershell
   docker ps --format "table {{.Names}}\t{{.Status}}"
   ```
   Gesunde Container sollten "healthy" zeigen

---

## Wenn Probleme auftreten

### Problem: Container crashen
**Check Logs:**
```powershell
docker compose logs cdb_postgres
docker compose logs cdb_execution
```

**Häufige Ursache:** Alte absolute Host-Pfade in Compose Files.
Prüfe `infrastructure/compose/compose.blue.yml` auf hartcodierte Pfade.

### Problem: Postgres startet nicht
```powershell
docker ps -a | grep postgres
```
- Prüfe: `infrastructure/compose/compose.blue.yml`
- Entferne alte absolute Pfade
- Volume-Namen sollten ausreichen (keine Host-Mounts für schema.sql nötig)

### Problem: Grafana zeigt keine Dashboards
**Restore nochmal:**
```powershell
docker volume rm claire_de_binare_grafana_data
docker volume create claire_de_binare_grafana_data
docker run --rm -v claire_de_binare_grafana_data:/var/lib/grafana -v <BACKUP_DIR>\grafana_data:/backup alpine cp -r /backup/. /var/lib/grafana/
docker compose restart cdb_grafana
```

---

## Was wird wiederhergestellt

| Component | Status |
|-----------|--------|
| Grafana Dashboards | Gesichert |
| Redis Daten | Gesichert |
| Prometheus Metriken | Gesichert |
| Loki Logs | Gesichert |
| PostgreSQL | Volume bleibt erhalten |
| .env Config | Gesichert |
| Secrets | Bleiben außerhalb Docker |

---

## Manuelle Restore-Commands (falls Scripts fehlschlagen)

**Redis:**
```powershell
docker volume create claire_de_binare_redis_data
docker run --rm -v claire_de_binare_redis_data:/data -v <BACKUP_DIR>\redis_data:/backup alpine cp -r /backup/. /data/
```

**Grafana:**
```powershell
docker volume create claire_de_binare_grafana_data
docker run --rm -v claire_de_binare_grafana_data:/var/lib/grafana -v <BACKUP_DIR>\grafana_data:/backup alpine cp -r /backup/. /var/lib/grafana/
```

**Prometheus:**
```powershell
docker volume create claire_de_binare_prom_data
docker run --rm -v claire_de_binare_prom_data:/data -v <BACKUP_DIR>:/backup alpine sh -c "cd /data && tar xzf /backup/prometheus_data.tar.gz"
```

**Loki:**
```powershell
docker volume create claire_de_binare_loki_data
docker run --rm -v claire_de_binare_loki_data:/data -v <BACKUP_DIR>:/backup alpine sh -c "cd /data && tar xzf /backup/loki_data.tar.gz"
```

**PostgreSQL (falls Volume weg ist):**
```powershell
docker volume create claire_de_binare_postgres_data
# Fresh init beim ersten Start - Datenbank wird neu initialisiert
```

**Config:**
```powershell
Copy-Item <BACKUP_DIR>\.env_backup <REPO_ROOT>\.env -Force
```

---

## Erwarteter Endstate

**Laufende Container (docker ps):**
Alle BLUE- und RED-Services healthy/running.

**Services erreichbar:**
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Signal: http://localhost:8005/health
- WS: http://localhost:8000/health
- Risk: http://localhost:8002/health

---

**Gesamt-Dauer für komplettes Restore:** ~5 Minuten
**Scripts:** `restore_volumes.ps1`, `verify_restore.ps1`
**Manuelle Anleitung:** `RESTORE_GUIDE.md`

**Hinweis:** Die Helper-Scripts enthalten möglicherweise noch hartcodierte Pfade —
siehe Issue #1387 für deren Bereinigung.
