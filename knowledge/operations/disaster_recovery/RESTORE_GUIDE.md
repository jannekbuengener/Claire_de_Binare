# Docker Reinstall - Restore Guide

> **Hinweis:** Diese Anleitung beschreibt den generischen Restore-Prozess.
> Die ursprüngliche Version basierte auf dem Backup vom 2025-12-31 mit
> host-spezifischen Pfaden — diese wurden durch Platzhalter ersetzt.
> Passe `<BACKUP_DIR>` und `<REPO_ROOT>` an deine Umgebung an.

---

## Was wird wiederhergestellt

### Daten (Volumes):
- Redis: `redis_data/` (dump.rdb + appendonlydir)
- Grafana: `grafana_data/` (Dashboards, Settings, Users)
- Prometheus: `prometheus_data.tar.gz` (Zeitreihen-Daten)
- Loki: `loki_data.tar.gz` (Aggregierte Logs)

### Konfiguration:
- `.env` File: `.env_backup`
- Secrets Template: `.secrets_example_backup/`
- Container/Volume/Network Listen

### PostgreSQL:
- **Volume bleibt normalerweise bei Docker-Neuinstallation erhalten**
- Falls leer: Fresh Init beim ersten Start (Schema wird automatisch angelegt)

### Secrets (außerhalb Docker):
- Konfigurierbar via `SECRETS_PATH` (Default: `~/Documents/.secrets/.cdb/`)
- Enthalten: MEXC API Keys, Grafana/Postgres/Redis Passwords
- **Bleiben bei Neuinstallation erhalten**

---

## Restore nach Docker Neuinstallation

### 1. Docker neu installieren
```bash
# Nach Installation verifizieren:
docker --version
docker compose version
```

### 2. Repository Setup
```bash
cd <REPO_ROOT>
cp <BACKUP_DIR>/.env_backup .env
```

### 3. Volumes wiederherstellen

#### Redis:
```bash
docker volume create claire_de_binare_redis_data
docker run --rm -v claire_de_binare_redis_data:/data -v <BACKUP_DIR>/redis_data:/backup alpine cp -r /backup/. /data/
```

#### Grafana:
```bash
docker volume create claire_de_binare_grafana_data
docker run --rm -v claire_de_binare_grafana_data:/var/lib/grafana -v <BACKUP_DIR>/grafana_data:/backup alpine cp -r /backup/. /var/lib/grafana/
```

#### Prometheus:
```bash
docker volume create claire_de_binare_prom_data
docker run --rm -v claire_de_binare_prom_data:/data -v <BACKUP_DIR>:/backup alpine sh -c "cd /data && tar xzf /backup/prometheus_data.tar.gz"
```

#### Loki:
```bash
docker volume create claire_de_binare_loki_data
docker run --rm -v claire_de_binare_loki_data:/data -v <BACKUP_DIR>:/backup alpine sh -c "cd /data && tar xzf /backup/loki_data.tar.gz"
```

### 4. PostgreSQL Volume (sollte automatisch erhalten bleiben)
```bash
# Volume sollte noch existieren, sonst:
docker volume create claire_de_binare_postgres_data
# Falls leer: Fresh Init beim ersten Start
```

### 5. Stack starten (BLUE+RED)
```bash
cd <REPO_ROOT>
# Netzwerk sicherstellen
docker network create cdb_network 2>/dev/null
make docker-up
# ODER explizit:
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
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

## Known Issues

### PostgreSQL Mount-Fehler:
```
error mounting "...schema.sql": not a directory
```
**Fix:** Prüfe Mount-Pfade in `infrastructure/compose/compose.blue.yml` — absolute Host-Pfade durch Volume-Namen ersetzen.

### Container Status nach Restore prüfen:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```
Erwartung: alle BLUE-Services `healthy` oder `running`.

---

## Compose File Locations

```
infrastructure/compose/compose.blue.yml   # BLUE stack (core, always-on)
infrastructure/compose/compose.red.yml    # RED stack (signal + monitoring)
```

**WICHTIG:** Prüfe Mount-Pfade in Compose Files nach Neuinstallation!

---

**Hinweis:** Die Helper-Scripts `restore_volumes.ps1` und `verify_restore.ps1`
enthalten möglicherweise noch hartcodierte Pfade — siehe Issue #1387 für deren
Bereinigung.
