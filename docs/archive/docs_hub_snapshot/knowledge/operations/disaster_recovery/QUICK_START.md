# 🚀 QUICK START - Nach Docker Neuinstallation

**Backup Location:** `D:\Dev\Backups\docker_reinstall_20251231_075507`

---

## ⚡ 3-Schritte Restore (Automatisch)

### 1. Docker verifizieren
```powershell
docker --version
docker compose version
```
✅ Sollte funktionieren nach Neuinstallation

### 2. Volumes + Config automatisch wiederherstellen
```powershell
cd D:\Dev\Backups\docker_reinstall_20251231_075507
.\restore_volumes.ps1
```
⏱️ Dauer: ~2-3 Minuten

### 3. Stack starten
```powershell
cd D:\Dev\Workspaces\Repos\Claire_de_Binare
make docker-up
```
⏱️ Dauer: ~30-60 Sekunden

### 4. Verifizieren
```powershell
cd D:\Dev\Backups\docker_reinstall_20251231_075507
.\verify_restore.ps1
```

---

## ✅ Erfolgs-Checks

1. **Docker läuft:**
   ```powershell
   docker ps
   ```
   Sollte zeigen: grafana, redis, signal, ws, risk, execution, db_writer, paper_runner

2. **Grafana Dashboards:**
   - http://localhost:3000
   - Login: admin / (siehe Secrets)
   - Sollte 8 Dashboards zeigen

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

## 🚨 Wenn Probleme auftreten

### Problem: Container crashen
**Check Logs:**
```powershell
docker compose logs cdb_postgres
docker compose logs cdb_execution
```

**Häufige Ursache:** Alte Pfade in Compose Files
- Suche nach: `C:\Users\janne\Documents\GitHub\Workspaces\`
- Ersetze mit: `D:\Dev\Workspaces\Repos\`

### Problem: Postgres startet nicht
**Container ID prüfen:**
```powershell
docker ps -a | grep postgres
```

**Mount-Fehler?**
- Prüfe: `infrastructure/compose/base.yml`
- Entferne alte absolute Pfade
- Volume-Namen sollten ausreichen (keine Host-Mounts für schema.sql nötig)

### Problem: Grafana zeigt keine Dashboards
**Restore nochmal:**
```powershell
docker volume rm claire_de_binare_grafana_data
docker volume create claire_de_binare_grafana_data
docker run --rm -v claire_de_binare_grafana_data:/var/lib/grafana -v D:\Dev\Backups\docker_reinstall_20251231_075507\grafana_data:/backup alpine cp -r /backup/. /var/lib/grafana/
docker compose restart cdb_grafana
```

---

## 📊 Was wurde wiederhergestellt

| Component | Size | Status |
|-----------|------|--------|
| Grafana Dashboards (8) | 109MB | ✅ Gesichert |
| Redis Daten | 85KB | ✅ Gesichert |
| Prometheus Metriken | 2.0MB | ✅ Gesichert |
| Claude Memory | 2.9KB | ✅ Gesichert |
| Loki Logs | 671B | ✅ Gesichert |
| PostgreSQL | - | ⚠️ Volume bleibt erhalten |
| .env Config | 1.1KB | ✅ Gesichert |
| Secrets | - | ✅ Bleiben außerhalb Docker |

---

## 🔧 Manuelle Restore-Commands (falls Scripts fehlschlagen)

**Redis:**
```powershell
docker volume create claire_de_binare_redis_data
docker run --rm -v claire_de_binare_redis_data:/data -v D:\Dev\Backups\docker_reinstall_20251231_075507\redis_data:/backup alpine cp -r /backup/. /data/
```

**Grafana:**
```powershell
docker volume create claire_de_binare_grafana_data
docker run --rm -v claire_de_binare_grafana_data:/var/lib/grafana -v D:\Dev\Backups\docker_reinstall_20251231_075507\grafana_data:/backup alpine cp -r /backup/. /var/lib/grafana/
```

**Prometheus:**
```powershell
docker volume create claire_de_binare_prom_data
docker run --rm -v claire_de_binare_prom_data:/data -v D:\Dev\Backups\docker_reinstall_20251231_075507:/backup alpine sh -c "cd /data && tar xzf /backup/prometheus_data.tar.gz"
```

**Loki:**
```powershell
docker volume create claire_de_binare_loki_data
docker run --rm -v claire_de_binare_loki_data:/data -v D:\Dev\Backups\docker_reinstall_20251231_075507:/backup alpine sh -c "cd /data && tar xzf /backup/loki_data.tar.gz"
```

**Claude Memory:**
```powershell
docker volume create claude-memory
docker run --rm -v claude-memory:/data -v D:\Dev\Backups\docker_reinstall_20251231_075507:/backup alpine sh -c "cd /data && tar xzf /backup/claude_memory.tar.gz"
```

**PostgreSQL (falls Volume weg ist):**
```powershell
docker volume create claire_de_binare_postgres_data
# Fresh init beim ersten Start - Datenbank wird neu initialisiert
```

**Config:**
```powershell
Copy-Item D:\Dev\Backups\docker_reinstall_20251231_075507\.env_backup D:\Dev\Workspaces\Repos\Claire_de_Binare\.env -Force
```

---

## 🎯 Erwartete Endstate

**Laufende Container (docker ps):**
```
cdb_grafana      - healthy
cdb_redis        - healthy  
cdb_postgres     - healthy
cdb_prometheus   - healthy
cdb_loki         - healthy
cdb_promtail     - running
cdb_signal       - healthy
cdb_ws           - healthy
cdb_risk         - healthy
cdb_execution    - running/healthy
cdb_db_writer    - running/healthy
cdb_paper_runner - running/healthy
```

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
