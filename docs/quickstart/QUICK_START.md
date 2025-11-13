# Archiviert: QUICK_START.md (Stand 2025-01-11)

> Hinweis: Dieses Dokument wurde am 2025-11-01 durch `README.md` und
> `../ops/RUNBOOK_DOCKER_OPERATIONS.md` ersetzt. Inhalte werden
> unverändert für historische Referenz aufbewahrt.

## 🚀 QUICK START - Claire de Binaire MVP-Core

**Letztes Update:** 2025-01-11
**Status:** ✅ OPERATIONAL

---

## ⚡ SYSTEM STARTEN (3 Befehle)

```powershell
## 1. Container prüfen
docker ps

## 2. Health-Checks
curl http://localhost:8001/health
curl http://localhost:8002/health

## 3. Database prüfen
docker exec cdb_postgres psql -U claire -d claire_de_binare -c "\dt"
```

**Erwartung:** 4 Container running, 2 Health-Checks OK, 10 Tabellen

---

## 🔄 NEUSTART (bei Problemen)

```powershell
## Services neu starten (Postgres bleibt)
docker restart cdb_signal cdb_risk

## Alles neu starten
docker restart cdb_postgres redis cdb_signal cdb_risk

## Health-Check
docker ps
```

---

## 🧪 QUICK TEST

```powershell
## Test-Signal senden
docker exec redis redis-cli PUBLISH market_data '{"symbol":"BTC_USDT","price":50000,"volume":1000000,"timestamp":1736600000,"pct_change":5.0}'

## Prüfe DB
docker exec cdb_postgres psql -U claire -d claire_de_binare -c "SELECT * FROM signals ORDER BY timestamp DESC LIMIT 3;"

## Prüfe Logs
docker logs cdb_signal --tail 10
docker logs cdb_risk --tail 10
```

---

## 📊 WICHTIGE PORTS

```
5432 - PostgreSQL
6379 - Redis
8001 - Signal-Engine
8002 - Risk-Manager
```

---

## 🔍 TROUBLESHOOTING

### Container läuft nicht?
```powershell
docker logs cdb_signal --tail 50
docker logs cdb_risk --tail 50
```

### Database-Probleme?
```powershell
docker exec cdb_postgres pg_isready -U claire
docker exec cdb_postgres psql -U claire -d claire_de_binare -c "SELECT version();"
```

### Schema neu laden?
```powershell
docker cp C:/Users/janne/Documents/claire_de_binare/backoffice/docs/DATABASE_SCHEMA.sql cdb_postgres:/tmp/schema.sql
docker exec cdb_postgres psql -U claire -d claire_de_binare -f /tmp/schema.sql
```

---

## 📁 WICHTIGE DATEIEN

```
PROJECT_STATUS.md                           - Aktueller Stand
backoffice/docs/DATABASE_SCHEMA.sql        - Database-Schema
backoffice/docs/reports/MVP_CORE_DEPLOYMENT.md - Deployment-Report
backoffice/services/signal_engine/         - Signal-Engine Code
backoffice/services/risk_manager/          - Risk-Manager Code
```

---

## 🎯 NÄCHSTE SCHRITTE

1. **End-to-End Test** (30 Min)
2. **Execution-Service** (3-4h)
3. **Monitoring** (2h)

---

**Für Details siehe:** `PROJECT_STATUS.md` oder `MVP_CORE_DEPLOYMENT.md`