# Grafana Dashboard Audit - 2026-01-08

**Session:** Claude Sonnet 4.5
**Datum:** 2026-01-08 18:35 CET
**Ziel:** Vollständige Prüfung aller 9 Grafana Dashboards zur Identifikation fehlender Metriken

---

## Executive Summary

**Status:** ⚠️ **TEILWEISE FUNKTIONSFÄHIG**

- **3/9 Dashboards** vollständig funktionsfähig (Paper Trading, Dark Trading, Execution Engine)
- **3/9 Dashboards** teilweise funktionsfähig (System Performance, Risk Manager, HITL Control Center)
- **3/9 Dashboards** komplett ohne Daten (Database Metrics, Signal Engine, 72h Soak Test)

**Root Cause:** Prometheus scraped **nur Container-Metriken** (cAdvisor), aber **keine Application-Metriken** von Services.

---

## Dashboard-Status (Detailliert)

### ✅ VOLL FUNKTIONSFÄHIG (3/9)

#### 1. Claire de Binare - Paper Trading (N1)
**URL:** `/d/claire_paper_trading_n1`
**Status:** ✅ **100% FUNKTIONSFÄHIG**

**Funktioniert:**
- Total Signals: 1.78K ✓
- Orders Approved: 0 ✓
- Orders Blocked: 1.78K ✓
- Approval Rate: 0% ✓
- Signal Engine Status: RUNNING ✓
- Circuit Breaker: INACTIVE ✓
- Signal Generation Rate Graph ✓
- Activity Rates (1min avg) ✓
- System Status Indicators ✓
- Signal & Order Flow Graph ✓

**Befund:** Dashboard zeigt alle erwarteten Daten korrekt an.

---

#### 2. Claire de Binare - Dark Trading
**URL:** `/d/claire_dark_v1`
**Status:** ✅ **100% FUNKTIONSFÄHIG**

**Funktioniert:**
- Circuit Breaker: INACTIVE ✓
- Orders Filled: 0 ✓
- Orders Rejected: 0 ✓
- Uptime: 3.35 hours ✓
- Order Flow Graph ✓
- Risk Metrics Panel ✓
- Performance Score Panel ✓

**Befund:** Dashboard zeigt alle erwarteten Daten korrekt an.

---

#### 3. Claire - Execution Engine
**URL:** `/d/claire_execution_v1`
**Status:** ✅ **100% FUNKTIONSFÄHIG**

**Funktioniert:**
- Orders Rate (Received/s, Filled/s, Rejected/s): Alle 0 ✓
- Order Results Timeline Graph ✓
- Total Results: 0 ✓
- Recent Trades Panel ✓

**Befund:** Werte bei 0 sind korrekt (keine Trades = keine Aktivität).

---

### ⚠️ TEILWEISE FUNKTIONSFÄHIG (3/9)

#### 4. Claire - System Performance
**URL:** `/d/claire_system_v1`
**Status:** ⚠️ **~60% FUNKTIONSFÄHIG**

**Funktioniert:**
- Services Up: 5 ✓
- Risk Manager: UP ✓
- Execution: UP ✓
- Prometheus: UP ✓
- **CPU Usage Graph (cdb_ws)** ✓
- **Memory Usage Graph (cdb_ws ~40 MB)** ✓

**Fehlt:**
- Signal Engine: No data ❌
- Goroutines (Concurrency Load): No data ❌
- HTTP Request Rate: No data ❌

**Befund:** Container-Metriken funktionieren, Application-Metriken fehlen.

---

#### 5. Claire - Risk Manager
**URL:** `/d/claire_risk_v1`
**Status:** ⚠️ **~40% FUNKTIONSFÄHIG**

**Funktioniert:**
- **Circuit Breaker: SAFE** ✓
- **Orders Blocked: 0** ✓

**Fehlt:**
- Max Exposure: No data ❌
- Exposure Timeline: No data ❌
- Risk Thresholds: Panel leer ❌
- Performance Score: Panel leer ❌

**Befund:** Grundlegende Status-Metriken funktionieren, Detail-Metriken fehlen.

---

#### 6. Claire - HITL Control Center
**URL:** `/d/claire_hitl_v1`
**Status:** ⚠️ **~30% FUNKTIONSFÄHIG**

**Funktioniert:**
- **Circuit Breaker: SAFE** ✓
- **Daily P&L Trend Graph** (zeigt Circuit Breaker Limit) ✓

**Fehlt:**
- Kill-Switch Status: No data ❌
- Trading Mode: No data ❌
- Daily P&L (%): No data ❌
- Portfolio Value (USDT): No data ❌
- Active Risk Limits: No data ❌
- Recent Manual Interventions: No data ❌

**Befund:** Nur grundlegende Status-Anzeigen funktionieren.

---

### ❌ OHNE DATEN (3/9)

#### 7. Claire - Database Metrics
**URL:** `/d/claire_database_v1`
**Status:** ❌ **0% FUNKTIONSFÄHIG**

**Alles "No data":**
- Postgres Status ❌
- Redis Status ❌
- PG Connections ❌
- Redis Memory ❌
- Redis Keys ❌
- PostgreSQL Query Performance ❌
- Redis Operations/sec ❌
- PostgreSQL Connections Over Time ❌
- Redis Memory Usage ❌
- Slow Queries ❌

**Befund:** Keine Daten von PostgreSQL/Redis Exporters.

---

#### 8. Claire - Signal Engine
**URL:** `/d/claire_signal_engine_v1`
**Status:** ❌ **0% FUNKTIONSFÄHIG**

**Alles "No data":**
- Signals Generated ❌
- Buy Signals ❌
- Sell Signals ❌
- Avg Confidence ❌
- Signal Generation Rate ❌
- Top Symbols (Last Hour) ❌
- Signal Type Distribution ❌

**Befund:** Signal-Service exportiert keine Metriken an Prometheus.

---

#### 9. Claire - 72h Soak Test Monitor
**URL:** `/d/claire_soak_test_v1`
**Status:** ❌ **0% FUNKTIONSFÄHIG**

**Alles "No data" oder "Error":**
- Container Restarts: No data ❌
- Disk Space Remaining: No data ❌
- Test Duration: No data ❌
- Service Health (8 Services): "An unexpected error happened" ❌
- Container Restarts Over Time: No data ❌

**Befund:** System-Metriken für Soak Testing fehlen komplett.

---

## Root Cause Analysis

### Was funktioniert:
1. ✅ **Grafana** läuft (Port 3000)
2. ✅ **Prometheus** läuft (Port 19090)
3. ✅ **Container-Metriken** (cAdvisor): CPU, Memory von `cdb_ws`
4. ✅ **Einige Application-Metriken**: Circuit Breaker Status, Service Health

### Was NICHT funktioniert:
1. ❌ **PostgreSQL Exporter**: Keine DB-Metriken
2. ❌ **Redis Exporter**: Keine Redis-Metriken
3. ❌ **Service Application Metrics**: Signal Engine, Goroutines, HTTP Requests
4. ❌ **System Metrics**: Disk Space, Container Restarts

### Mögliche Ursachen:

**Option 1: Exporters fehlen/laufen nicht**
- PostgreSQL Exporter nicht deployed
- Redis Exporter nicht deployed
- Fehlende Sidecar-Container in compose

**Option 2: Prometheus Scrape Config unvollständig**
- `prometheus.yml` fehlen Scrape-Targets
- Exporters laufen, aber Prometheus scraped sie nicht
- Service Discovery konfiguriert aber fehlerhaft

**Option 3: Services exportieren keine Metriken**
- Services haben `/metrics` Endpoint nicht implementiert
- Metrics-Libraries nicht eingebunden (z.B. prometheus_client)
- Metriken werden generiert aber nicht exposed

---

## Empfohlene Maßnahmen

### Sofort (P0):
1. **Prometheus Scrape Config prüfen**
   ```bash
   # Prometheus Targets UI öffnen
   http://127.0.0.1:19090/targets
   ```
   - Erwartung: Alle Services/Exporters als Targets sichtbar

2. **Service `/metrics` Endpoints testen**
   ```bash
   curl http://cdb_postgres:9187/metrics  # PostgreSQL Exporter
   curl http://cdb_redis:9121/metrics      # Redis Exporter
   curl http://cdb_signal:8005/metrics     # Signal Service
   ```

### Kurzfristig (P1):
3. **Fehlende Exporters deployen**
   - PostgreSQL Exporter: `wrouesnel/postgres_exporter`
   - Redis Exporter: `oliver006/redis_exporter`
   - Zu `dev.yml` oder `base.yml` hinzufügen

4. **Services instrumentieren**
   - `/metrics` Endpoint zu allen Python Services hinzufügen
   - `prometheus_client` Library verwenden
   - Standard-Metriken: HTTP requests, Goroutines, Custom Business Metrics

### Mittelfristig (P2):
5. **Prometheus Alerts konfigurieren**
   - Alert bei fehlenden Metriken
   - Alert bei "No data" Dashboards

6. **Dashboard-Dokumentation**
   - Welche Metriken woher kommen
   - Dependencies zwischen Services/Exporters/Dashboards

---

## Dateien für Issue

**Zu prüfen:**
- `infrastructure/compose/base.yml` - Exporters fehlen?
- `infrastructure/compose/dev.yml` - Exporter-Konfiguration?
- `infrastructure/monitoring/prometheus.yml` - Scrape Config vollständig?
- `services/*/service.py` - `/metrics` Endpoint implementiert?

**Screenshots:**
- Database Metrics "No data" (alle rot/orange)
- System Performance (teilweise funktionierend)
- Paper Trading (voll funktionierend)

---

## Nächste Schritte

1. ✅ Dokumentation erstellt
2. ⏳ GitHub Issue aufmachen: "Grafana Dashboards: Fehlende Metriken von PostgreSQL/Redis/Services"
3. ⏳ Prometheus Targets prüfen
4. ⏳ Exporters deployen
5. ⏳ Services instrumentieren

---

**Ende der Audit-Dokumentation**
