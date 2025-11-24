# RUNBOOK: 7-Tage Paper-Trading Run

**Version**: 1.0
**Datum**: 2025-11-23
**Status**: Production-Ready
**Gültigkeit**: N1 Paper-Test Phase

---

## 📋 Inhaltsverzeichnis

1. [Executive Summary](#1-executive-summary)
2. [Pre-Flight Checklist](#2-pre-flight-checklist)
3. [Start Procedures](#3-start-procedures)
4. [Monitoring Checklists](#4-monitoring-checklists)
5. [Incident Response](#5-incident-response)
6. [Daily Review Process](#6-daily-review-process)
7. [Stop Procedures](#7-stop-procedures)
8. [Post-Run Analysis](#8-post-run-analysis)
9. [Emergency Contacts](#9-emergency-contacts)

---

## 1. Executive Summary

### 1.1 Zielsetzung

**7-Tage Paper-Trading Run** zum Validieren der Claire de Binare Trading-Engine unter realistischen Marktbedingungen ohne echtes Kapitalrisiko.

**Erfolgs-Kriterien**:
- ✅ System läuft durchgängig 7 Tage ohne Crash
- ✅ Alle Risk-Checks funktionieren korrekt
- ✅ Event-Flow vollständig (market_data → signals → orders → trades → analytics)
- ✅ Kein Verstoß gegen Risk-Limits (Daily Drawdown, Total Exposure, Position Limits)
- ✅ Alle Trades korrekt in PostgreSQL persistiert

### 1.2 System-Übersicht

**Container-Stack** (9 Services):
```
cdb_redis       → Message Bus (Port 6379)
cdb_postgres    → Database (Port 5432)
cdb_db_writer   → Persistence Layer
cdb_ws          → Market Data Screener (Port 8000)
cdb_core        → Signal Engine (Port 8001)
cdb_risk        → Risk Manager (Port 8002)
cdb_execution   → Execution Service (Port 8003)
cdb_prometheus  → Metrics (Port 19090)
cdb_grafana     → Dashboards (Port 3000)
```

**Daten-Flow**:
```
MEXC API → WebSocket → market_data (Redis) → Signal Engine → signals (Redis)
→ Risk Manager → orders (Redis) → Execution → order_results (Redis)
→ DB Writer → PostgreSQL (5 Tabellen)
```

---

## 2. Pre-Flight Checklist

### 2.1 Infrastruktur (T-24h vor Start)

**Docker Desktop**:
- [ ] Docker Desktop gestartet und stabil
- [ ] Mindestens 4 GB RAM für Container verfügbar
- [ ] Mindestens 10 GB Disk Space frei

**ENV-Variablen**:
```bash
# ENV-Validation ausführen
cd C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Cleanroom
.\backoffice\automation\check_env.ps1

# Erwartung: Alle Required Vars gesetzt
```

**Kritische ENV-Variablen prüfen**:
```bash
# .env öffnen und validieren:
POSTGRES_PASSWORD=<set>          # ✅ Gesetzt
REDIS_HOST=cdb_redis             # ✅ Korrekt
POSTGRES_HOST=cdb_postgres       # ✅ Korrekt
MAX_POSITION_PCT=0.10            # ✅ 10%
MAX_DAILY_DRAWDOWN_PCT=0.05      # ✅ 5%
MAX_TOTAL_EXPOSURE_PCT=0.30      # ✅ 30%
CIRCUIT_BREAKER_THRESHOLD_PCT=0.10  # ✅ 10%
```

### 2.2 Code-Qualität (T-12h vor Start)

**Test-Suite ausführen**:
```bash
# Alle Tests
pytest -v

# Erwartung: 144 passed, 1 skipped, 0 errors, 0 warnings
```

**Coverage prüfen**:
```bash
pytest --cov=services --cov-report=term

# Erwartung: 100% Coverage (424/424 statements)
```

**E2E-Tests mit Docker**:
```bash
# Container starten
docker compose up -d

# E2E-Suite
pytest -v -m e2e

# Erwartung: 18 passed, 0 failed
```

### 2.3 Datenbank-Vorbereitung (T-6h vor Start)

**PostgreSQL Schema validieren**:
```bash
# Schema-Check
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare -c "\dt"

# Erwartung: 5 Tabellen
#   signals
#   orders
#   trades
#   positions
#   portfolio_snapshots
```

**Datenbank-Backup erstellen**:
```bash
# Vor Start: Letztes Backup
docker exec cdb_postgres pg_dump -U claire_user -d claire_de_binare > backup_pre_paper_run_$(date +%Y%m%d).sql

# Backup-Datei prüfen
ls -lh backup_pre_paper_run_*.sql
```

### 2.4 Monitoring-Setup (T-3h vor Start)

**Grafana Dashboard**:
- [ ] Grafana öffnen: http://localhost:3000
- [ ] Login: admin / <aus .env GRAFANA_PASSWORD>
- [ ] Dashboard "Claire Paper-Trading" vorhanden
- [ ] Panels zeigen Daten: Equity, Drawdown, Exposure, Trades

**Prometheus Metrics**:
- [ ] Prometheus öffnen: http://localhost:19090
- [ ] Targets prüfen: http://localhost:19090/targets
- [ ] Erwartung: Alle Services "UP"

**Alerts einrichten**:
```yaml
# In Grafana: Alert Rules erstellen
- Daily Drawdown > 4.5% → Warning
- Daily Drawdown > 5.0% → Critical
- Total Exposure > 28% → Warning
- Total Exposure > 30% → Critical
- Service Down > 30s → Critical
```

### 2.5 Final Go/No-Go Decision (T-1h vor Start)

**Checkliste**:
- [ ] ✅ Alle 9 Container healthy
- [ ] ✅ Tests: 144/144 passed
- [ ] ✅ Coverage: 100%
- [ ] ✅ E2E-Tests: 18/18 passed
- [ ] ✅ ENV-Vars validiert
- [ ] ✅ PostgreSQL Schema OK
- [ ] ✅ Backup erstellt
- [ ] ✅ Grafana Dashboard lädt
- [ ] ✅ Prometheus Targets UP
- [ ] ✅ Alerts konfiguriert

**Decision**:
```
GO:    Alle Checkboxen ✅
NO-GO: Mindestens 1 Critical Item nicht erfüllt
```

---

## 3. Start Procedures

### 3.1 T-0: System-Start

**Schritt 1: Container hochfahren**
```bash
# Alle Container starten
docker compose up -d

# Status prüfen (alle sollten "healthy" sein)
docker compose ps
```

**Erwartung nach 30 Sekunden**:
```
NAME            STATUS              HEALTH
cdb_redis       Up 30s              healthy
cdb_postgres    Up 30s              healthy
cdb_db_writer   Up 30s              healthy
cdb_ws          Up 30s              healthy
cdb_core        Up 30s              healthy
cdb_risk        Up 30s              healthy
cdb_execution   Up 30s              healthy
cdb_prometheus  Up 30s              healthy
cdb_grafana     Up 30s              healthy
```

**Schritt 2: Health-Endpoints prüfen**
```bash
# Alle Services
curl -fsS http://localhost:8000/health  # WebSocket
curl -fsS http://localhost:8001/health  # Signal Engine
curl -fsS http://localhost:8002/health  # Risk Manager
curl -fsS http://localhost:8003/health  # Execution

# Erwartung jeweils: {"status": "ok", "service": "...", "version": "..."}
```

**Schritt 3: Event-Flow validieren**
```bash
# Redis Pub/Sub prüfen
docker exec -it cdb_redis redis-cli

# In Redis CLI:
SUBSCRIBE market_data
SUBSCRIBE signals
SUBSCRIBE orders
SUBSCRIBE order_results

# In anderem Terminal: Test-Event publishen
docker exec -it cdb_redis redis-cli PUBLISH market_data '{"symbol":"BTCUSDT","price":50000.0}'

# Erwartung: Event erscheint im Subscribe-Terminal
```

**Schritt 4: Initial Log-Check**
```bash
# Alle Services: Keine Errors
docker compose logs --tail=50 cdb_core cdb_risk cdb_execution

# Erwartung: Nur INFO-Level, keine ERROR/CRITICAL
```

### 3.2 T+0 bis T+5min: Stabilisierungsphase

**Beobachten**:
- [ ] Keine Container-Restarts in `docker compose ps`
- [ ] Logs zeigen kontinuierliche Aktivität (market_data Events)
- [ ] Grafana zeigt erste Datenpunkte
- [ ] PostgreSQL erhält erste Einträge

**Erste Daten validieren**:
```bash
# PostgreSQL prüfen
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare

# In psql:
SELECT COUNT(*) FROM signals;
SELECT COUNT(*) FROM orders;
SELECT COUNT(*) FROM trades;

# Erwartung: > 0 bei signals, ggf. 0 bei orders/trades (je nach Marktlage)
```

### 3.3 T+5min: System operativ

**Final Checks**:
- [ ] Mindestens 5 Signals in PostgreSQL
- [ ] Grafana Dashboard aktualisiert
- [ ] Prometheus scrapes erfolgreich
- [ ] Kein Memory-Leak (Container-RAM stabil)

**Zeitstempel dokumentieren**:
```bash
echo "Paper-Run gestartet: $(date)" >> paper_run_log.txt
```

---

## 4. Monitoring Checklists

### 4.1 Kontinuierliches Monitoring (Alle 4 Stunden)

**Health-Check**:
```bash
# Container-Status
docker compose ps

# Health-Endpoints
curl -fsS http://localhost:8001/health
curl -fsS http://localhost:8002/health
curl -fsS http://localhost:8003/health
```

**Grafana Dashboard prüfen**:
- [ ] http://localhost:3000/d/claire-paper-trading
- [ ] Equity-Curve zeigt Bewegung
- [ ] Drawdown < 5%
- [ ] Total Exposure < 30%
- [ ] Keine roten Alerts

**PostgreSQL Data-Growth**:
```sql
-- In psql:
SELECT
    'signals' AS table_name, COUNT(*) AS count FROM signals
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'trades', COUNT(*) FROM trades
UNION ALL
SELECT 'positions', COUNT(*) FROM positions
UNION ALL
SELECT 'portfolio_snapshots', COUNT(*) FROM portfolio_snapshots;
```

**Erwartung**:
- signals: +100-500 pro Tag
- orders: +10-50 pro Tag (je nach Marktlage)
- trades: +5-20 pro Tag
- positions: 0-3 (aktive Positionen)
- portfolio_snapshots: +24 pro Tag (stündlich)

### 4.2 Alarm-Bedingungen (Sofort reagieren)

| Alarm | Schwere | Aktion |
|-------|---------|--------|
| Container exited | 🔴 CRITICAL | [Incident-5.1](#51-container-crash) |
| Daily Drawdown > 5% | 🔴 CRITICAL | [Incident-5.2](#52-risk-limit-überschritten) |
| Total Exposure > 30% | 🔴 CRITICAL | [Incident-5.2](#52-risk-limit-überschritten) |
| Health-Endpoint down > 1min | 🔴 CRITICAL | [Incident-5.3](#53-service-unresponsive) |
| PostgreSQL down | 🔴 CRITICAL | [Incident-5.4](#54-datenbank-ausfall) |
| Memory > 90% | 🟡 WARNING | [Incident-5.5](#55-ressourcen-knappheit) |
| No new signals > 1h | 🟡 WARNING | [Incident-5.6](#56-daten-stopp) |

---

## 5. Incident Response

### 5.1 Container Crash

**Symptome**:
- `docker compose ps` zeigt "Exited" oder "Restarting"
- Logs zeigen "Traceback" oder "FATAL"

**Sofortmaßnahmen**:
```bash
# 1. Logs sichern
docker compose logs <crashed_service> > incident_$(date +%Y%m%d_%H%M%S)_crash.log

# 2. Container neu starten
docker compose restart <crashed_service>

# 3. Health prüfen
curl -fsS http://localhost:800X/health

# 4. Erneuter Crash?
#    → STOP Paper-Run (siehe 7.2)
#    → Root-Cause-Analysis
```

**Root-Cause-Analysis**:
```bash
# Log analysieren
cat incident_*_crash.log | grep -E "ERROR|FATAL|Traceback"

# Häufige Ursachen:
# - Out of Memory → docker stats prüfen
# - Connection refused → Redis/PostgreSQL prüfen
# - KeyError → ENV-Variablen prüfen
```

### 5.2 Risk-Limit überschritten

**Symptome**:
- Grafana Alert: "Daily Drawdown > 5%"
- Oder: "Total Exposure > 30%"

**Sofortmaßnahmen**:
```bash
# 1. Trading STOPPEN (manueller Circuit-Breaker)
# Execution Service pausieren
docker compose stop cdb_execution

# 2. Aktuelle Positionen prüfen
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare -c "SELECT * FROM positions WHERE status='open';"

# 3. Grafana Dashboard öffnen
# → Equity-Curve analysieren
# → Welche Trades verursachten Loss?

# 4. Entscheidung:
#    a) Fehler in Risk-Logic → Bug-Fix nötig → STOP Run
#    b) Markt-Volatilität → Warten auf Marktberuhigung
```

**Wenn Trading fortgesetzt wird**:
```bash
# Execution Service neu starten
docker compose start cdb_execution

# Kontinuierlich Drawdown monitoren (alle 10 Min)
watch -n 600 'curl -fsS http://localhost:8002/status | jq .daily_drawdown'
```

### 5.3 Service Unresponsive

**Symptome**:
- Health-Endpoint antwortet nicht (Timeout)
- Grafana Panel zeigt "No Data"

**Sofortmaßnahmen**:
```bash
# 1. Service-Status prüfen
docker compose ps <service>

# 2. Container-Logs prüfen (letzte 100 Zeilen)
docker compose logs --tail=100 <service>

# 3. Ressourcen prüfen
docker stats <service>

# 4. Neustart
docker compose restart <service>

# 5. Wenn weiterhin unresponsive:
docker compose stop <service>
docker compose up -d <service>
```

### 5.4 Datenbank-Ausfall

**Symptome**:
- PostgreSQL Container "Exited"
- Services loggen "Connection refused" oder "PG::Error"

**Sofortmaßnahmen**:
```bash
# 1. PostgreSQL neu starten
docker compose restart cdb_postgres

# 2. Warten auf healthy (ca. 10-15s)
docker compose ps cdb_postgres

# 3. Schema-Validierung
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare -c "\dt"

# 4. Wenn Daten korrupt:
#    → Restore von Backup (siehe 8.3)
```

**Wenn PostgreSQL nicht startet**:
```bash
# Logs prüfen
docker compose logs cdb_postgres

# Volume-Problem?
docker volume ls | grep postgres
docker volume inspect claire_de_binare_cleanroom_cdb_postgres_data

# Letzter Ausweg: Volume neu erstellen (DATEN VERLUST!)
# NUR mit Backup!
docker compose down
docker volume rm claire_de_binare_cleanroom_cdb_postgres_data
docker compose up -d cdb_postgres
# Dann: Restore von Backup
```

### 5.5 Ressourcen-Knappheit

**Symptome**:
- Docker stats zeigt > 90% Memory
- Services werden langsam
- "Out of Memory" Errors in Logs

**Sofortmaßnahmen**:
```bash
# 1. Ressourcen-Verbrauch analysieren
docker stats --no-stream

# 2. Logs auf Memory-Leaks prüfen
docker compose logs cdb_core | grep -i "memory"

# 3. Nicht-kritische Services stoppen (temporär)
docker compose stop cdb_grafana  # Dashboard ist optional
docker compose stop cdb_prometheus  # Metrics sind optional

# 4. Docker Desktop RAM-Limit erhöhen
# Settings → Resources → Memory Limit → 6 GB

# 5. Wenn Problem bleibt:
#    → Paper-Run STOPPEN
#    → Memory-Profiling durchführen
```

### 5.6 Daten-Stopp

**Symptome**:
- Keine neuen Signals > 1 Stunde
- PostgreSQL: `SELECT MAX(timestamp) FROM signals;` zeigt alte Daten

**Sofortmaßnahmen**:
```bash
# 1. WebSocket-Service prüfen
curl -fsS http://localhost:8000/health

# 2. MEXC API-Status prüfen
# Browser: https://www.mexc.com/de-DE/support/sections/360002165591

# 3. WebSocket Logs prüfen
docker compose logs --tail=200 cdb_ws | grep -i "error\|disconnect"

# 4. Wenn WebSocket disconnected:
docker compose restart cdb_ws

# 5. Test-Event manuell publishen
docker exec -it cdb_redis redis-cli PUBLISH market_data '{"symbol":"BTCUSDT","price":50000.0,"timestamp":"2025-11-23T12:00:00Z"}'

# 6. Signal Engine reagiert?
docker compose logs cdb_core | grep "BTCUSDT"
```

---

## 6. Daily Review Process

### 6.1 Morning Check (09:00 UTC täglich)

**Checkliste**:
```bash
# 1. Container-Status
docker compose ps
# Erwartung: Alle "healthy"

# 2. Overnight Logs (letzte 8h)
docker compose logs --since 8h cdb_core cdb_risk cdb_execution | grep -E "ERROR|CRITICAL"
# Erwartung: Keine Errors

# 3. PostgreSQL Data-Growth
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare -c "
SELECT
    DATE(timestamp) AS day,
    COUNT(*) AS signal_count
FROM signals
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY DATE(timestamp);
"
# Erwartung: > 100 Signals pro Tag

# 4. Grafana Dashboard Review
# → http://localhost:3000/d/claire-paper-trading
# → Screenshot speichern für Report
```

**Trading-Statistik abrufen**:
```bash
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare -c "
SELECT
    COUNT(*) AS total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS winning_trades,
    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) AS losing_trades,
    SUM(pnl) AS total_pnl,
    AVG(pnl) AS avg_pnl_per_trade
FROM trades
WHERE timestamp > NOW() - INTERVAL '24 hours';
"
```

### 6.2 Evening Review (21:00 UTC täglich)

**Performance-Analyse**:
```sql
-- In psql:
-- Daily PnL
SELECT
    DATE(timestamp) AS day,
    SUM(pnl) AS daily_pnl,
    COUNT(*) AS trades_count
FROM trades
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY DATE(timestamp);

-- Position Analysis
SELECT
    symbol,
    side,
    size,
    entry_price,
    current_price,
    unrealized_pnl
FROM positions
WHERE status = 'open';

-- Risk Metrics
SELECT
    MAX(total_exposure_pct) AS max_exposure_today,
    MIN(equity_usd) AS min_equity_today,
    MAX(equity_usd) AS max_equity_today
FROM portfolio_snapshots
WHERE timestamp > NOW() - INTERVAL '24 hours';
```

**Daily Report erstellen**:
```bash
# Report-Datei
echo "=== Paper-Run Daily Report $(date +%Y-%m-%d) ===" > daily_report_$(date +%Y%m%d).txt

# Container Uptime
docker compose ps >> daily_report_$(date +%Y%m%d).txt

# Trading Stats
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare -c "
SELECT * FROM (
    SELECT COUNT(*) AS total_trades FROM trades WHERE timestamp > NOW() - INTERVAL '24 hours'
) t1,
(
    SELECT SUM(pnl) AS total_pnl FROM trades WHERE timestamp > NOW() - INTERVAL '24 hours'
) t2;
" >> daily_report_$(date +%Y%m%d).txt

# Grafana Screenshot (manuell)
# → Screenshot von Dashboard → Ablegen in: reports/day_X_dashboard.png
```

### 6.3 Wochenend-Check (Samstag/Sonntag)

**Reduziertes Monitoring** (nur kritische Checks):
```bash
# Minimal-Check alle 12h
docker compose ps
curl -fsS http://localhost:8001/health
curl -fsS http://localhost:8002/health

# PostgreSQL Data-Wachstum
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare -c "SELECT COUNT(*) FROM signals;"
```

**Hinweis**: Krypto-Märkte handeln 24/7, daher sollte System auch am Wochenende laufen.

---

## 7. Stop Procedures

### 7.1 Geplantes Ende (Tag 7)

**Schritt 1: Trading stoppen**
```bash
# Execution Service pausieren (keine neuen Trades)
docker compose stop cdb_execution

# Warten auf offene Positionen (max 1h)
watch -n 60 'docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare -c "SELECT COUNT(*) FROM positions WHERE status='\''open'\'';"'

# Wenn nach 1h noch Positionen offen:
# → Manuell schließen (Paper-Modus: einfach "closed" setzen)
```

**Schritt 2: Final Snapshot**
```bash
# PostgreSQL Backup
docker exec cdb_postgres pg_dump -U claire_user -d claire_de_binare > backup_post_paper_run_$(date +%Y%m%d).sql

# Grafana Dashboard Screenshot
# → http://localhost:3000/d/claire-paper-trading
# → Screenshot speichern: final_dashboard_day_7.png

# Logs archivieren
docker compose logs > paper_run_full_logs_$(date +%Y%m%d).txt
```

**Schritt 3: Container herunterfahren**
```bash
# Alle Services stoppen (Daten bleiben in Volumes)
docker compose down

# Volumes NICHT löschen! (Daten für Analyse)
```

### 7.2 Notfall-Stop (bei Critical Incidents)

**Sofort-Stop**:
```bash
# Trading sofort stoppen
docker compose stop cdb_execution cdb_core cdb_risk

# Logs sichern
docker compose logs > emergency_stop_$(date +%Y%m%d_%H%M%S).txt

# PostgreSQL Backup
docker exec cdb_postgres pg_dump -U claire_user -d claire_de_binare > emergency_backup_$(date +%Y%m%d_%H%M%S).sql

# Alle Container stoppen
docker compose down
```

**Incident dokumentieren**:
```bash
# Incident-Report erstellen
cat > incident_report_$(date +%Y%m%d_%H%M%S).txt <<EOF
=== EMERGENCY STOP ===
Datum: $(date)
Grund: <GRUND EINTRAGEN>

Container-Status vor Stop:
$(docker compose ps)

Letzte 200 Log-Zeilen:
$(docker compose logs --tail=200)

Nächste Schritte:
- Root-Cause-Analysis
- Bug-Fix
- Erneuter Test-Start nach Validierung
EOF
```

---

## 8. Post-Run Analysis

### 8.1 Daten-Export

**PostgreSQL → CSV**:
```bash
# Alle Signals exportieren
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare -c "\COPY signals TO '/tmp/signals_export.csv' WITH CSV HEADER;"
docker cp cdb_postgres:/tmp/signals_export.csv ./analysis/signals_export.csv

# Alle Trades exportieren
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare -c "\COPY trades TO '/tmp/trades_export.csv' WITH CSV HEADER;"
docker cp cdb_postgres:/tmp/trades_export.csv ./analysis/trades_export.csv

# Portfolio Snapshots exportieren
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare -c "\COPY portfolio_snapshots TO '/tmp/portfolio_export.csv' WITH CSV HEADER;"
docker cp cdb_postgres:/tmp/portfolio_export.csv ./analysis/portfolio_export.csv
```

### 8.2 Performance-Metriken

**Trading-Performance**:
```sql
-- In psql:
-- Gesamt-PnL
SELECT SUM(pnl) AS total_pnl FROM trades;

-- Win-Rate
SELECT
    COUNT(CASE WHEN pnl > 0 THEN 1 END) * 100.0 / COUNT(*) AS win_rate_pct
FROM trades;

-- Avg Win / Avg Loss
SELECT
    AVG(CASE WHEN pnl > 0 THEN pnl END) AS avg_win,
    AVG(CASE WHEN pnl < 0 THEN pnl END) AS avg_loss,
    AVG(CASE WHEN pnl > 0 THEN pnl END) / ABS(AVG(CASE WHEN pnl < 0 THEN pnl END)) AS profit_factor
FROM trades;

-- Max Drawdown
WITH equity_series AS (
    SELECT
        timestamp,
        equity_usd,
        MAX(equity_usd) OVER (ORDER BY timestamp) AS peak_equity
    FROM portfolio_snapshots
)
SELECT
    MIN((equity_usd - peak_equity) / peak_equity * 100) AS max_drawdown_pct
FROM equity_series;

-- Total Trades & Exposure
SELECT
    COUNT(*) AS total_trades,
    AVG(size * entry_price) AS avg_trade_size_usd,
    MAX(total_exposure_pct) AS max_exposure_reached
FROM trades t
JOIN portfolio_snapshots ps ON DATE(t.timestamp) = DATE(ps.timestamp);
```

### 8.3 System-Performance

**Container-Uptime**:
```bash
# Container-Statistik
docker compose ps --format json | jq -r '.[] | "\(.Name): \(.Status)"'

# Restarts prüfen
docker inspect $(docker compose ps -q) | jq -r '.[] | "\(.Name): \(.RestartCount) restarts"'
```

**Logs-Analyse**:
```bash
# Error-Count
docker compose logs | grep -c "ERROR"

# Warning-Count
docker compose logs | grep -c "WARNING"

# Häufigste Fehler
docker compose logs | grep "ERROR" | sort | uniq -c | sort -nr | head -20
```

### 8.4 Lessons Learned

**Template für Abschlussbericht**:
```markdown
# Paper-Run Abschlussbericht

**Zeitraum**: <START> bis <ENDE>
**Dauer**: 7 Tage
**Status**: <ERFOLG / ABGEBROCHEN>

## Executive Summary
<1-2 Sätze Zusammenfassung>

## Trading-Performance
- Total PnL: <WERT> USD
- Win-Rate: <WERT> %
- Total Trades: <ANZAHL>
- Max Drawdown: <WERT> %
- Max Exposure: <WERT> %

## System-Performance
- Container-Uptime: <WERT> %
- Container-Restarts: <ANZAHL>
- Total Errors: <ANZAHL>
- Incidents: <ANZAHL>

## Risk-Compliance
- Daily Drawdown Limit (5%) überschritten: <JA/NEIN>
- Total Exposure Limit (30%) überschritten: <JA/NEIN>
- Circuit-Breaker getriggert: <JA/NEIN>

## Lessons Learned
### Was lief gut:
- <PUNKT 1>
- <PUNKT 2>

### Was lief schlecht:
- <PUNKT 1>
- <PUNKT 2>

### Action Items für Production:
- [ ] <AKTION 1>
- [ ] <AKTION 2>

## Nächste Schritte
<Empfehlung für Production-Deployment>
```

---

## 9. Emergency Contacts

### 9.1 Eskalationskette

| Level | Name | Rolle | Erreichbarkeit |
|-------|------|-------|----------------|
| L1 | Claude (AI) | IT-Chef | Immer verfügbar |
| L2 | Jannek | Projektleiter | Work Hours |
| L3 | Gordon (AI) | Server-Admin | Docker-Probleme |

### 9.2 Externe Abhängigkeiten

**MEXC Exchange**:
- Status-Page: https://www.mexc.com/de-DE/support/sections/360002165591
- API-Docs: https://mexcdevelop.github.io/apidocs/spot_v3_en/
- Support: support@mexc.com

**Docker Desktop**:
- Docs: https://docs.docker.com/desktop/
- Community: https://forums.docker.com/

**PostgreSQL**:
- Docs: https://www.postgresql.org/docs/
- Community: https://www.postgresql.org/support/

### 9.3 Kritische Dateien & Backups

**Backup-Lokationen**:
```
C:\Backups\cdb_postgres\           # PostgreSQL Dumps
C:\Users\janne\Documents\GitHub\   # Repo-Backups
```

**Restore-Kommando**:
```bash
# PostgreSQL Restore (bei Datenverlust)
docker exec -i cdb_postgres psql -U claire_user -d claire_de_binare < backup_YYYYMMDD.sql
```

**ENV-Datei Backup**:
```bash
# .env sichern (NICHT in Git!)
cp .env .env.backup_$(date +%Y%m%d)

# Bei Verlust: .env.example → .env kopieren und Werte neu setzen
```

---

## 10. Anhang

### 10.1 Wichtige Commands (Cheat-Sheet)

```bash
# Container-Status
docker compose ps

# Logs (live)
docker compose logs -f cdb_core cdb_risk cdb_execution

# Health-Checks
curl -fsS http://localhost:8001/health
curl -fsS http://localhost:8002/health
curl -fsS http://localhost:8003/health

# PostgreSQL Connect
docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare

# Redis Connect
docker exec -it cdb_redis redis-cli

# Container neu starten
docker compose restart <service>

# Alle Container neu starten
docker compose restart

# Container-Ressourcen
docker stats

# Backup erstellen
docker exec cdb_postgres pg_dump -U claire_user -d claire_de_binare > backup_$(date +%Y%m%d).sql
```

### 10.2 SQL-Queries (Schnellzugriff)

```sql
-- Offene Positionen
SELECT * FROM positions WHERE status = 'open';

-- Heute's Trades
SELECT * FROM trades WHERE timestamp > NOW() - INTERVAL '24 hours';

-- Equity-Verlauf
SELECT timestamp, equity_usd FROM portfolio_snapshots ORDER BY timestamp DESC LIMIT 100;

-- Daily PnL
SELECT
    DATE(timestamp) AS day,
    SUM(pnl) AS daily_pnl
FROM trades
GROUP BY DATE(timestamp)
ORDER BY day DESC;

-- Risk-Metriken
SELECT
    MAX(total_exposure_pct) AS max_exposure,
    MIN(equity_usd) AS min_equity,
    MAX(equity_usd) AS max_equity
FROM portfolio_snapshots
WHERE timestamp > NOW() - INTERVAL '24 hours';
```

### 10.3 Grafana Panel IDs

| Panel | ID | Beschreibung |
|-------|----|--------------|
| Equity Curve | panel-1 | Kapitalverlauf über Zeit |
| Daily Drawdown | panel-2 | Täglicher Drawdown % |
| Total Exposure | panel-3 | Gesamt-Exposure % |
| Open Positions | panel-4 | Anzahl offene Positionen |
| Trade Count | panel-5 | Trades pro Tag |
| Win Rate | panel-6 | Gewinn-Rate % |

---

**Ende des Runbooks**

**Version History**:
- v1.0 (2025-11-23): Initial Release für N1 Paper-Test
