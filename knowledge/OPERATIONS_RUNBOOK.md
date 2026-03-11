# OPERATIONS_RUNBOOK - Ops Start/Stop/Debug

**Version:** 1.0
**Erstellt:** 2025-12-28
**Status:** Kanonisch
**Pruefintervall:** Bei jedem Session-Start

---

## 1. Stack Management

### Stack starten (Development)

```powershell
# Standard Dev Stack
.\infrastructure\scripts\stack_up.ps1 -Profile dev

# Mit Logging (Loki + Promtail)
.\infrastructure\scripts\stack_up.ps1 -Profile dev -Logging

# Mit TLS
.\infrastructure\scripts\stack_up.ps1 -Profile dev -TLS

# Vollstaendig (Dev + Logging + TLS)
.\infrastructure\scripts\stack_up.ps1 -Profile dev -Logging -TLS
```

### Stack stoppen

```powershell
# Alle Container stoppen
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml down

# Mit Volume-Cleanup (ACHTUNG: loescht Daten!)
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml down -v
```

### Stack verifizieren

```powershell
# Automatische Vollstaendigkeitspruefung
.\infrastructure\scripts\stack_verify.ps1

# Manueller Schnellcheck
docker ps --filter "name=cdb_" --format "table {{.Names}}\t{{.Status}}"
```

---

## 2. Erwarteter Stack-Status (healthy)

```
NAMES               STATUS
cdb_redis           Up X minutes (healthy)
cdb_postgres        Up X minutes (healthy)
cdb_prometheus      Up X minutes (healthy)
cdb_grafana         Up X minutes (healthy)
cdb_ws              Up X minutes (healthy)
cdb_signal          Up X minutes (healthy)
cdb_risk            Up X minutes
cdb_execution       Up X minutes
cdb_db_writer       Up X minutes (healthy)
cdb_paper_runner    Up X minutes (healthy)
```

**Hinweis:** cdb_risk und cdb_execution haben keine expliziten Healthchecks in dev.yml.

---

## 3. Service Health Checks

### Manuelle Health-Pruefung

```powershell
# WebSocket Service
curl http://127.0.0.1:8000/health

# Signal Service
curl http://127.0.0.1:8005/health

# Risk Service
curl http://127.0.0.1:8002/health

# Execution Service
curl http://127.0.0.1:8003/health

# Paper Runner
curl http://127.0.0.1:8004/health

# Grafana
curl http://127.0.0.1:3000/api/health

# Prometheus
curl http://127.0.0.1:19090/-/healthy
```

### Redis Health

```powershell
docker exec cdb_redis redis-cli ping
# Erwartete Antwort: PONG
```

### PostgreSQL Health

```powershell
docker exec cdb_postgres pg_isready -U postgres
# Erwartete Antwort: accepting connections
```

---

## 4. Logs einsehen

### Container Logs

```powershell
# Einzelner Service
docker logs cdb_signal --tail 100 -f

# Alle Services
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml logs -f

# Nur Fehler
docker logs cdb_risk 2>&1 | Select-String -Pattern "ERROR|CRITICAL"
```

### Loki Logs (wenn aktiviert)

Zugriff ueber Grafana: http://127.0.0.1:3000
- Data Source: Loki
- Label Filter: {container_name="cdb_signal"}

---

## 5. Debugging

### Service Restart

```powershell
# Einzelnen Service neu starten
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml restart cdb_signal
```

### Service Rebuild

```powershell
# Mit Rebuild
.\infrastructure\scripts\stack_up.ps1 -Profile dev -Rebuild

# Oder manuell
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml up -d --build cdb_signal
```

### Container Shell

```powershell
# In Container einloggen
docker exec -it cdb_signal /bin/sh

# Python REPL im Container
docker exec -it cdb_signal python3
```

---

## 6. Redis Debugging

### Channel Monitor

```powershell
# Alle Pub/Sub Messages mitlesen
docker exec -it cdb_redis redis-cli PSUBSCRIBE "*"
```

### Queue Status

```powershell
# Keys anzeigen
docker exec cdb_redis redis-cli KEYS "*"

# Bestimmten Key lesen
docker exec cdb_redis redis-cli GET <key>
```

---

## 7. PostgreSQL Debugging

### SQL Shell

```powershell
docker exec -it cdb_postgres psql -U postgres -d claire
```

### Tabellen pruefen

```sql
-- Letzte 10 Events
SELECT * FROM events ORDER BY created_at DESC LIMIT 10;

-- Signals zaehlen
SELECT COUNT(*) FROM signals;

-- Orders Status
SELECT status, COUNT(*) FROM orders GROUP BY status;
```

---

## 8. Paper Trading

### Paper Runner starten

```powershell
# Via Makefile
make paper-trading-start

# Oder direkt
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml up -d cdb_paper_runner
```

### Paper Runner Logs

```powershell
make paper-trading-logs

# Oder
docker logs cdb_paper_runner -f --tail 100
```

### Paper Runner stoppen

```powershell
make paper-trading-stop
```

---

## 9. Metrics (Prometheus/Grafana)

### Prometheus Queries

```
# Risk Service Metriken
risk_orders_blocked_total
circuit_breaker_active

# Execution Service Metriken
order_results_received_total
orders_executed_total
```

### Grafana Dashboards

URL: http://127.0.0.1:3000
- Default Credentials: admin/admin (bei erstem Login aendern!)
- Trading Dashboard: Suche nach "Claire de Binare"

---

## 10. Notfall-Prozeduren

### Kill Switch aktivieren

```powershell
# Emergency Stop - stoppt alle Services
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml stop
```

### Vollstaendiger Reset

```powershell
# Alles stoppen und aufraeuumen
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml down -v
docker system prune -f

# Neu starten
.\infrastructure\scripts\stack_up.ps1 -Profile dev
```

---

## 11. Bekannte Probleme

### Problem: Service bleibt "starting"
**Ursache:** Abhaengigkeit (Redis/Postgres) nicht ready.
**Loesung:** Warten oder `docker compose restart <service>`.

### Problem: Port bereits belegt
**Ursache:** Alter Container oder anderer Prozess.
**Loesung:**
```powershell
# Prozess auf Port finden
netstat -ano | findstr :8005
# Prozess beenden oder Port in .env aendern
```

### Problem: Container Crash Loop
**Ursache:** Fehlende Env-Vars oder Code-Fehler.
**Loesung:**
```powershell
docker logs cdb_<service> --tail 200
# Fehler analysieren, Env-Vars pruefen
```

---

## Changelog

| Datum | Aenderung | Durch |
|-------|-----------|-------|
| 2025-12-28 | Initiale Erstellung via Context Core Build Sprint | Claude (Orchestrator) |
