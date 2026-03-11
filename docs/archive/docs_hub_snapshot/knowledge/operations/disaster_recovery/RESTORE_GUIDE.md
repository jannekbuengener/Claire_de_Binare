# Docker Reinstall - Restore Guide

**Backup erstellt:** 2025-12-31 07:55:07
**Backup Location:** D:\Dev\Backups\docker_reinstall_20251231_075507

## ✅ Was wurde gesichert

### Daten (Volumes):
- ✅ Redis: `redis_data/` (85KB dump.rdb + appendonlydir)
- ✅ Grafana: `grafana_data/` (109MB - Dashboards, Settings, Users)
- ✅ Claude Memory: `claude_memory.tar.gz` (2.9KB)
- ✅ Prometheus: `prometheus_data.tar.gz` (2.0MB)
- ✅ Loki: `loki_data.tar.gz` (671 bytes)

### Konfiguration:
- ✅ .env File: `.env_backup`
- ✅ Secrets Template: `.secrets_example_backup/`
- ✅ Container List: `container_list.txt`
- ✅ Volume List: `volume_list.txt`
- ✅ Network List: `network_list.txt`

### PostgreSQL:
- ⚠️ **NICHT GESICHERT** - Container konnte nicht starten (Mount-Fehler)
- Volume existiert: `claire_de_binare_postgres_data`
- Status: Daten sollten im Volume erhalten bleiben

### Secrets (außerhalb Docker):
- ✅ Location dokumentiert: `/c/Users/janne/Documents/.secrets/.cdb/`
- Enthält: MEXC API Keys, Grafana/Postgres/Redis Passwords
- **Diese bleiben erhalten!**

---

## 🔧 Restore nach Docker Neuinstallation

### 1. Docker neu installieren
```bash
# Nach Installation verifizieren:
docker --version
docker compose version
```

### 2. Repository Setup
```bash
cd D:\Dev\Workspaces\Repos\Claire_de_Binare
cp D:\Dev\Backups\docker_reinstall_20251231_075507\.env_backup .env
```

### 3. Volumes wiederherstellen

#### Redis:
```bash
docker volume create claire_de_binare_redis_data
docker run --rm -v claire_de_binare_redis_data:/data -v D:\Dev\Backups\docker_reinstall_20251231_075507\redis_data:/backup alpine cp -r /backup/. /data/
```

#### Grafana:
```bash
docker volume create claire_de_binare_grafana_data
docker run --rm -v claire_de_binare_grafana_data:/var/lib/grafana -v D:\Dev\Backups\docker_reinstall_20251231_075507\grafana_data:/backup alpine cp -r /backup/. /var/lib/grafana/
```

#### Claude Memory:
```bash
docker volume create claude-memory
docker run --rm -v claude-memory:/data -v D:\Dev\Backups\docker_reinstall_20251231_075507:/backup alpine sh -c "cd /data && tar xzf /backup/claude_memory.tar.gz"
```

#### Prometheus:
```bash
docker volume create claire_de_binare_prom_data
docker run --rm -v claire_de_binare_prom_data:/data -v D:\Dev\Backups\docker_reinstall_20251231_075507:/backup alpine sh -c "cd /data && tar xzf /backup/prometheus_data.tar.gz"
```

#### Loki:
```bash
docker volume create claire_de_binare_loki_data
docker run --rm -v claire_de_binare_loki_data:/data -v D:\Dev\Backups\docker_reinstall_20251231_075507:/backup alpine sh -c "cd /data && tar xzf /backup/loki_data.tar.gz"
```

### 4. PostgreSQL Volume (sollte automatisch erhalten bleiben)
```bash
# Volume sollte noch existieren, sonst:
docker volume create claire_de_binare_postgres_data
# Falls leer: Fresh Init beim ersten Start
```

### 5. Stack starten
```bash
cd D:\Dev\Workspaces\Repos\Claire_de_Binare
# Fix Postgres Mount-Problem falls nötig (alter Pfad C:\Users\janne\Documents\...)
make docker-up
# ODER
docker compose up -d
```

### 6. Verifizierung
```bash
docker ps
docker logs cdb_grafana
docker logs cdb_redis
docker logs cdb_postgres

# Grafana: http://localhost:3000
# Dashboards sollten wiederhergestellt sein
```

---

## 🚨 Known Issues

### PostgreSQL Mount-Fehler:
```
error mounting "/run/desktop/mnt/host/c/Users/janne/Documents/GitHub/Workspaces/..."
```
**Fix:** Update compose file paths von altem `C:\Users\janne\Documents\GitHub\Workspaces\` zu `D:\Dev\Workspaces\Repos\`

### Container Status vor Backup:
- ✅ Healthy: signal, ws, risk, grafana, redis
- 🔄 Restarting: paper_runner, execution, db_writer
- ❌ Exited: postgres, prometheus, loki, promtail

---

## 📝 Compose File Locations

```
infrastructure/compose/base.yml
infrastructure/compose/dev.yml
infrastructure/compose/prod.yml
infrastructure/compose/logging.yml
infrastructure/compose/memory.yml
infrastructure/compose/test.yml
```

**WICHTIG:** Prüfe Mount-Pfade in compose files nach Neuinstallation!

---

**Backup Duration:** ~3 Minuten
**Total Size:** ~111MB (hauptsächlich Grafana)
