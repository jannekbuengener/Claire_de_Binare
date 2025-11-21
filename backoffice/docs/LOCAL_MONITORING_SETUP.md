# Lokales Monitoring-Setup – Claire de Binaire

**Projekt:** Claire de Binaire – Autonomer Krypto-Trading-Bot
**Phase:** N1 – Paper-Test Implementation
**Version:** 1.0
**Datum:** 2025-11-21
**Status:** ✅ Ready for Local Execution

---

## 📋 Inhaltsverzeichnis

1. [Executive Summary](#1-executive-summary)
2. [Voraussetzungen](#2-voraussetzungen)
3. [Setup-Schritte (komplett)](#3-setup-schritte-komplett)
4. [Service-Integration (manuell)](#4-service-integration-manuell)
5. [Dashboard-Setup (Grafana UI)](#5-dashboard-setup-grafana-ui)
6. [Validierung & Testing](#6-validierung--testing)
7. [Troubleshooting](#7-troubleshooting)
8. [Wartung](#8-wartung)

---

## 1. Executive Summary

### 1.1 Was wurde automatisiert?

✅ **Bereits konfiguriert** (durch Code-Generation):
- Docker-Compose mit 4 neuen Services (Redis-Exporter, PostgreSQL-Exporter, Alertmanager, aktualisierte Prometheus/Grafana)
- Prometheus-Konfiguration (`monitoring/prometheus/prometheus.yml` + `alerts.yml`)
- Alertmanager-Konfiguration (`monitoring/alertmanager/alertmanager.yml`)
- Grafana-Provisioning (Datasources + Dashboard-Provider)
- Gemeinsames Metrics-Modul (`services_common/metrics.py`)

### 1.2 Was muss lokal getan werden?

⚠️ **Manuelle Schritte erforderlich**:
1. **Services integrieren:** Metrics-Modul in cdb_core, cdb_risk, cdb_execution einbinden
2. **Dashboards erstellen:** 3 Grafana-Dashboards via UI konfigurieren (Templates verfügbar)
3. **Docker-Stack neu starten:** `docker compose up -d --build`
4. **Validieren:** Prometheus-Targets, Grafana-Dashboards, Alert-Regeln testen
5. **E2E-Tests:** Metriken während Tests überprüfen

**Geschätzte Dauer:** 2-3 Stunden

---

## 2. Voraussetzungen

### 2.1 System-Requirements

- Docker & Docker Compose installiert
- Mindestens 4 GB RAM verfügbar (für alle Container)
- Ports frei: 19090 (Prometheus), 3000 (Grafana), 9121 (Redis-Exporter), 9187 (PostgreSQL-Exporter), 9093 (Alertmanager)

### 2.2 ENV-Variablen prüfen

Sicherstellen, dass `.env` Folgendes enthält:

```bash
# PostgreSQL
POSTGRES_USER=claire
POSTGRES_PASSWORD=<your-password>
POSTGRES_DB=claire_de_binaire

# Redis
REDIS_PASSWORD=<your-password>

# Grafana
GRAFANA_PASSWORD=<your-password>

# MEXC API (für Services)
MEXC_API_KEY=<your-api-key>
MEXC_API_SECRET=<your-api-secret>

# Risk Parameters
MAX_DAILY_DRAWDOWN_PCT=0.05
MAX_POSITION_PCT=0.10
MAX_EXPOSURE_PCT=0.50
```

---

## 3. Setup-Schritte (komplett)

### 3.1 Schritt 1: Docker-Compose validieren

```bash
# Validiere docker-compose.yml
docker compose config --quiet

# Erwartung: Kein Output = Config ist valide
```

**Bei Fehler:**
- Prüfe, ob alle Volume-Mounts existieren: `monitoring/prometheus`, `monitoring/alertmanager`, `monitoring/grafana`

### 3.2 Schritt 2: Docker-Stack neu starten

```bash
# Stoppe alle Container
docker compose down

# Baue Images neu (falls Service-Code geändert wurde)
docker compose build

# Starte alle Services
docker compose up -d

# Warte 30 Sekunden, bis alle Services hochgefahren sind
sleep 30

# Prüfe Status
docker compose ps
```

**Erwartung:**
```
NAME                        STATUS
cdb_alertmanager            Up (healthy)
cdb_core                    Up (healthy)
cdb_execution               Up (healthy)
cdb_grafana                 Up (healthy)
cdb_postgres                Up (healthy)
cdb_postgres_exporter       Up
cdb_prometheus              Up (healthy)
cdb_redis                   Up (healthy)
cdb_redis_exporter          Up
cdb_risk                    Up (healthy)
cdb_ws                      Up (healthy)
```

**Falls Services "unhealthy" sind:**
- Logs prüfen: `docker compose logs <service-name>`
- Siehe [Abschnitt 7: Troubleshooting](#7-troubleshooting)

### 3.3 Schritt 3: Prometheus-Targets validieren

```bash
# Öffne Prometheus UI
open http://localhost:19090/targets
# oder: curl -s http://localhost:19090/api/v1/targets | jq .
```

**Erwartung:**
- **cdb_services (4 Targets):** cdb_ws:8000, cdb_core:8001, cdb_risk:8002, cdb_execution:8003 → **State: UP**
- **redis (1 Target):** cdb_redis_exporter:9121 → **State: UP**
- **postgres (1 Target):** cdb_postgres_exporter:9187 → **State: UP**
- **prometheus (1 Target):** localhost:9090 → **State: UP**

**Falls Targets "DOWN" sind:**
1. **Service nicht erreichbar:** Prüfe mit `curl http://localhost:<port>/metrics`
2. **Kein /metrics-Endpoint:** Service muss Metrics-Modul integrieren (siehe Abschnitt 4)
3. **DNS-Problem:** Prüfe Docker-Netzwerk: `docker network inspect cdb_network`

### 3.4 Schritt 4: Grafana-Login

```bash
# Öffne Grafana UI
open http://localhost:3000
```

**Login:**
- Username: `admin`
- Password: `${GRAFANA_PASSWORD}` (aus `.env`)

**Nach Login:**
1. Gehe zu **Configuration → Data Sources**
2. Prüfe, dass "Prometheus" vorhanden und als "Default" markiert ist
3. Klicke auf "Prometheus" → "Test" → **Erwartung: "Data source is working"**

---

## 4. Service-Integration (manuell)

### 4.1 Übersicht

Jeder Python-Service (`cdb_core`, `cdb_risk`, `cdb_execution`) muss:
1. `services_common.metrics` importieren
2. `/metrics`-Endpoint hinzufügen
3. Metriken an kritischen Code-Stellen aufrufen

### 4.2 cdb_core (Signal Engine)

**Datei:** `backoffice/services/signal_engine/service.py` (oder Haupt-Entry-Point)

#### 4.2.1 Import hinzufügen

```python
# Am Anfang der Datei
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from services_common import metrics
from flask import Flask, Response
```

#### 4.2.2 /metrics-Endpoint hinzufügen

```python
app = Flask(__name__)

@app.route('/metrics')
def prometheus_metrics():
    return Response(metrics.get_metrics(), mimetype='text/plain')

@app.route('/health')
def health():
    # ... existing health check logic
    is_healthy = check_health()  # Deine Health-Check-Logik
    metrics.set_health_status('cdb_core', is_healthy)
    return {'status': 'ok' if is_healthy else 'error'}
```

#### 4.2.3 Metriken in Code integrieren

**Beispiel 1: Signal generieren**
```python
def generate_signal(market_data):
    with metrics.measure_signal_processing('momentum_v1'):
        # ... Signalgenerierungs-Logik
        signal = {
            'symbol': 'BTCUSDT',
            'direction': 'BUY',
            'strength': 0.82
        }

        # Metrik aufzeichnen
        metrics.record_signal(
            symbol=signal['symbol'],
            direction=signal['direction'],
            strategy='momentum_v1',
            strength=signal['strength']
        )

        return signal
```

**Beispiel 2: Market-Data verarbeiten**
```python
def on_market_data(event):
    metrics.market_data_events_received.labels(
        symbol=event['symbol'],
        source='mexc_ws'
    ).inc()

    # ... Verarbeitung
```

#### 4.2.4 Test

```bash
# Service ist laufend, teste Metrics-Endpoint
curl -s http://localhost:8001/metrics | grep cdb_signals_generated_total

# Erwartung: Metrik ist vorhanden (auch wenn Wert 0)
# cdb_signals_generated_total{symbol="BTCUSDT",direction="BUY",strategy="momentum_v1"} 0
```

---

### 4.3 cdb_risk (Risk Manager)

**Datei:** `backoffice/services/risk_manager/service.py`

#### 4.3.1 Import & Endpoint (wie cdb_core)

```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from services_common import metrics
from flask import Flask, Response

app = Flask(__name__)

@app.route('/metrics')
def prometheus_metrics():
    return Response(metrics.get_metrics(), mimetype='text/plain')

@app.route('/health')
def health():
    is_healthy = check_health()
    metrics.set_health_status('cdb_risk', is_healthy)
    return {'status': 'ok' if is_healthy else 'error'}
```

#### 4.3.2 Metriken in Risk-Logic integrieren

**Beispiel 1: Risk-Decision**
```python
def validate_signal(signal, risk_state, config):
    with metrics.measure_risk_decision():
        # ... Risk-Validation-Logik
        approved = True  # oder False
        reason_code = "OK"  # oder "DRAWDOWN_LIMIT", etc.
        size = 0.05

        # Metrik aufzeichnen
        metrics.record_risk_decision(
            symbol=signal['symbol'],
            approved=approved,
            reason_code=reason_code if not approved else None,
            size=size if approved else None
        )

        return {'approved': approved, 'size': size, 'reason': reason_code}
```

**Beispiel 2: Drawdown & Exposure updaten**
```python
def update_risk_state(portfolio_state):
    # Berechne Drawdown
    daily_drawdown_pct = calculate_drawdown()
    metrics.update_drawdown(daily_drawdown_pct)

    # Berechne Exposure
    total_exposure_pct = calculate_total_exposure()
    position_exposures = {
        'BTCUSDT': 8.5,
        'ETHUSDT': 6.2
    }
    metrics.update_exposure(total_exposure_pct, position_exposures)

    # Circuit-Breaker-Status
    if daily_drawdown_pct > 5.0:
        metrics.set_circuit_breaker(True)
```

**Beispiel 3: Risk-Violation**
```python
def check_position_limit(symbol, size, config):
    max_size = config['MAX_POSITION_PCT']
    if size > max_size:
        metrics.record_violation('POSITION_SIZE_EXCEEDED', layer=5)
        return False
    return True
```

#### 4.3.3 Test

```bash
curl -s http://localhost:8002/metrics | grep cdb_daily_drawdown_pct
# Erwartung: cdb_daily_drawdown_pct 0.0
```

---

### 4.4 cdb_execution (Execution Service)

**Datei:** `backoffice/services/execution_service/service.py`

#### 4.4.1 Import & Endpoint (wie vorher)

```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from services_common import metrics
from flask import Flask, Response

app = Flask(__name__)

@app.route('/metrics')
def prometheus_metrics():
    return Response(metrics.get_metrics(), mimetype='text/plain')

@app.route('/health')
def health():
    is_healthy = check_health()
    metrics.set_health_status('cdb_execution', is_healthy)
    return {'status': 'ok' if is_healthy else 'error'}
```

#### 4.4.2 Metriken in Execution-Logic integrieren

**Beispiel 1: Trade ausführen**
```python
def execute_order(order):
    metrics.orders_received.labels(symbol=order['symbol']).inc()

    with metrics.measure_order_execution('MEXC'):
        # ... Order-Execution-Logik
        trade = {
            'symbol': order['symbol'],
            'side': 'BUY',
            'quantity': 0.05,
            'price': 50000.0,
            'pnl': 120.50,
            'slippage': 5.2  # Basispunkte
        }

        # Metrik aufzeichnen
        metrics.record_trade(
            symbol=trade['symbol'],
            side=trade['side'],
            pnl=trade['pnl'],
            slippage=trade['slippage']
        )

        return trade
```

**Beispiel 2: Portfolio-State updaten**
```python
def update_portfolio(trades):
    # Berechne kumulativen PnL
    total_pnl = sum(t['pnl'] for t in trades)
    metrics.update_pnl(total_pnl)

    # Offene Positionen
    positions = {
        'BTCUSDT': 0.05,
        'ETHUSDT': 0.12
    }
    metrics.update_positions(positions)
```

#### 4.4.3 Test

```bash
curl -s http://localhost:8003/metrics | grep cdb_cumulative_pnl_usd
# Erwartung: cdb_cumulative_pnl_usd 0.0
```

---

### 4.5 Alle Services neu starten

```bash
# Nach Code-Änderungen: Services neu bauen
docker compose build cdb_core cdb_risk cdb_execution

# Neu starten
docker compose up -d cdb_core cdb_risk cdb_execution

# Health prüfen
curl -fsS http://localhost:8001/health
curl -fsS http://localhost:8002/health
curl -fsS http://localhost:8003/health

# Metrics prüfen
curl -s http://localhost:8001/metrics | grep -E "^cdb_" | wc -l
curl -s http://localhost:8002/metrics | grep -E "^cdb_" | wc -l
curl -s http://localhost:8003/metrics | grep -E "^cdb_" | wc -l

# Erwartung: Jeweils > 10 Metriken sichtbar
```

---

## 5. Dashboard-Setup (Grafana UI)

### 5.1 Option 1: Manuell über UI erstellen

Da die kompletten Dashboard-JSONs sehr groß sind (>1000 Zeilen), hier die **vereinfachte Anleitung**:

#### 5.1.1 Dashboard 1: Trading Overview

1. **Grafana öffnen:** http://localhost:3000
2. **Dashboards → New Dashboard**
3. **Add Visualization → Prometheus**
4. **Panel 1: Total Signals (Stat)**
   - Query: `sum(cdb_signals_generated_total)`
   - Visualization: Stat
   - Title: "Total Signals"
5. **Panel 2: Signals per Minute (Time Series)**
   - Query: `sum by (symbol) (rate(cdb_signals_generated_total[1m]))`
   - Visualization: Time series
   - Title: "Signals per Minute"
6. **Panel 3: Order Approval Rate (Time Series)**
   - Query: `sum(rate(cdb_orders_approved_total[5m])) / sum(rate(cdb_signals_evaluated_total[5m])) * 100`
   - Visualization: Time series
   - Unit: Percent (0-100)
   - Title: "Order Approval Rate (%)"
7. **Panel 4: Cumulative PnL (Time Series - Area)**
   - Query: `cdb_cumulative_pnl_usd`
   - Visualization: Time series (Area fill)
   - Title: "Cumulative PnL"
8. **Speichern als:** "Trading Overview"

**Vollständige Panel-Definitionen:** Siehe `backoffice/docs/MONITORING_SPEC.md` Abschnitt 4.1

---

#### 5.1.2 Dashboard 2: Risk & Alerts

1. **Dashboards → New Dashboard**
2. **Panel 1: Daily Drawdown (Gauge)**
   - Query: `cdb_daily_drawdown_pct`
   - Visualization: Gauge
   - Unit: Percent
   - Max: 5.0
   - Thresholds: Green (0-3%), Yellow (3-4.5%), Red (>4.5%)
3. **Panel 2: Total Exposure (Gauge)**
   - Query: `cdb_total_exposure_pct`
   - Visualization: Gauge
   - Unit: Percent
   - Max: 50.0
   - Thresholds: Green (0-30%), Yellow (30-45%), Red (>45%)
4. **Panel 3: Circuit Breaker Status (Stat)**
   - Query: `cdb_circuit_breaker_active`
   - Visualization: Stat
   - Value Mappings:
     - 0 → "✅ INACTIVE" (Green)
     - 1 → "🔴 ACTIVE" (Red)
5. **Panel 4: Daily Drawdown History (Time Series)**
   - Query: `cdb_daily_drawdown_pct`
   - Visualization: Time series
   - Threshold line bei 5.0 (red dashed)
6. **Speichern als:** "Risk & Alerts"

**Vollständige Panel-Definitionen:** Siehe `backoffice/docs/MONITORING_SPEC.md` Abschnitt 4.2

---

#### 5.1.3 Dashboard 3: System Health

1. **Dashboards → New Dashboard**
2. **Panel-Reihe: Service Health (9x Stat Panels)**
   - Query (pro Service): `cdb_health_status{service="cdb_core"}`
   - Value Mappings:
     - 1 → "✅ HEALTHY" (Green)
     - 0 → "🔴 DOWN" (Red)
   - Für alle Services: cdb_ws, cdb_core, cdb_risk, cdb_execution, redis (via `redis_up`), postgres (via `pg_up`)
3. **Panel: Event Processing P95 Latency (Time Series)**
   - Query: `histogram_quantile(0.95, sum by (service, le) (rate(cdb_event_processing_duration_seconds_bucket[5m])))`
   - Visualization: Time series
   - Title: "P95 Event Processing Duration"
4. **Panel: Redis Memory Usage (Gauge)**
   - Query: `redis_used_memory_bytes / 1024 / 1024`
   - Unit: MB
5. **Panel: PostgreSQL Connections (Time Series)**
   - Query: `pg_stat_database_numbackends{datname="claire_de_binaire"}`
   - Visualization: Time series
6. **Speichern als:** "System Health"

**Vollständige Panel-Definitionen:** Siehe `backoffice/docs/MONITORING_SPEC.md` Abschnitt 4.3

---

### 5.2 Option 2: JSON-Import (schneller, aber erfordert volle JSONs)

**Vollständige Dashboard-JSONs** sind verfügbar in `backoffice/docs/MONITORING_SPEC.md` Abschnitt 6.

**Import-Schritte:**
1. Öffne Grafana UI: http://localhost:3000
2. **Dashboards → Import**
3. JSON aus `MONITORING_SPEC.md` kopieren (z.B. Abschnitt 6.1 für Trading Overview)
4. **Load** → **Import**
5. Wiederhole für alle 3 Dashboards

---

## 6. Validierung & Testing

### 6.1 Schritt 1: Prometheus-Metriken prüfen

```bash
# Alle cdb_*-Metriken auflisten
curl -s http://localhost:19090/api/v1/label/__name__/values | jq -r '.data[]' | grep ^cdb_

# Erwartung: Mindestens 30 Metriken sichtbar
```

**Beispiel-Output:**
```
cdb_circuit_breaker_active
cdb_cumulative_pnl_usd
cdb_daily_drawdown_pct
cdb_health_status
cdb_orders_approved_total
cdb_orders_rejected_total
cdb_signals_evaluated_total
cdb_signals_generated_total
cdb_total_exposure_pct
cdb_trades_executed_total
...
```

### 6.2 Schritt 2: Alert-Regeln prüfen

```bash
# Öffne Prometheus UI: Alerts
open http://localhost:19090/alerts

# Oder via API:
curl -s http://localhost:19090/api/v1/rules | jq '.data.groups[].rules[] | {alert: .name, state: .state}'
```

**Erwartung:**
- 10 Alerts definiert (DailyDrawdownLimitExceeded, CircuitBreakerActivated, etc.)
- State: "inactive" (solange keine Grenzwerte überschritten)

### 6.3 Schritt 3: Grafana-Dashboards prüfen

```bash
# Öffne Grafana
open http://localhost:3000/dashboards

# Prüfe, ob 3 Dashboards existieren:
# - Trading Overview
# - Risk & Alerts
# - System Health
```

**In jedem Dashboard:**
- Mindestens 1 Panel zeigt Daten (nicht "No Data")
- Time-Range anpassen (z.B. "Last 1 hour")

### 6.4 Schritt 4: E2E-Tests mit Metriken

```bash
# E2E-Tests ausführen
pytest -v -m e2e

# Während Tests laufen: Prometheus-Queries testen
# Terminal 2:
watch -n 2 'curl -s http://localhost:19090/api/v1/query?query=cdb_signals_generated_total | jq .data.result[0].value[1]'

# Terminal 3: Grafana-Dashboard beobachten
open http://localhost:3000/d/cdb-trading-overview
```

**Erwartung:**
- Metriken steigen während E2E-Tests:
  - `cdb_signals_generated_total` > 0
  - `cdb_orders_approved_total` > 0
  - `cdb_trades_executed_total` > 0
- Grafana-Panels zeigen Live-Updates

### 6.5 Schritt 5: Alert manuell triggern (optional)

```bash
# Simuliere hohen Drawdown (falls möglich in Service-Code):
curl -X POST http://localhost:8002/test/trigger-drawdown

# Prüfe Alert-Status in Prometheus:
open http://localhost:19090/alerts

# Erwartung: Alert "DailyDrawdownLimitExceeded" = "Firing" (rot)
```

---

## 7. Troubleshooting

### 7.1 Prometheus kann Services nicht scrapen

**Problem:**
```bash
curl -s http://localhost:19090/api/v1/targets | jq '.data.activeTargets[] | select(.health == "down")'
```

**Output zeigt "Connection refused" für cdb_core/cdb_risk/cdb_execution**

**Lösung:**
1. **Prüfe, ob /metrics-Endpoint existiert:**
   ```bash
   docker compose exec cdb_core curl -s http://localhost:8001/metrics
   ```
   - **Falls 404:** Service hat noch kein `/metrics`-Endpoint → Siehe Abschnitt 4
   - **Falls Fehler:** Service-Code hat Bug → Logs prüfen:
     ```bash
     docker compose logs cdb_core --tail=50
     ```

2. **Prüfe Docker-Netzwerk:**
   ```bash
   docker network inspect cdb_network | jq '.[0].Containers | to_entries[] | {name: .value.Name, ip: .value.IPv4Address}'
   ```
   - Alle Services sollten im selben Netzwerk sein

3. **Prometheus-Config prüfen:**
   ```bash
   docker compose exec cdb_prometheus cat /etc/prometheus/prometheus.yml
   ```
   - Target-URLs müssen korrekt sein: `cdb_core:8001`, nicht `cdb_core:8002`

---

### 7.2 Grafana zeigt "No Data"

**Problem:** Dashboard-Panels zeigen "No Data", obwohl Prometheus Metriken hat.

**Lösung:**
1. **Time-Range anpassen:**
   - Grafana UI → Time Picker (oben rechts) → "Last 1 hour"
   - Falls System gerade erst gestartet: "Last 5 minutes"

2. **Query testen in Prometheus:**
   ```bash
   curl -s 'http://localhost:19090/api/v1/query?query=cdb_signals_generated_total' | jq .data.result
   ```
   - Falls leer: Metriken wurden noch nicht generiert → Service ausführen/testen

3. **Datasource testen:**
   - Grafana UI → Configuration → Data Sources → Prometheus → **Test**
   - Falls "Error": Prometheus-URL falsch oder Container down

---

### 7.3 Alerts werden nicht gefeuert

**Problem:** Drawdown > 5%, aber Alert "DailyDrawdownLimitExceeded" bleibt "inactive".

**Lösung:**
1. **Metrik prüfen:**
   ```bash
   curl -s 'http://localhost:19090/api/v1/query?query=cdb_daily_drawdown_pct' | jq .data.result[0].value[1]
   ```
   - Falls Wert = "0": Service aktualisiert Metrik nicht → Siehe Abschnitt 4.3

2. **Alert-Rule-Syntax prüfen:**
   ```bash
   docker compose exec cdb_prometheus promtool check rules /etc/prometheus/alerts.yml
   ```
   - Falls Fehler: alerts.yml korrigieren und Container neustarten

3. **Alert-Evaluation-Intervall:**
   - Alerts werden alle 15s evaluiert (siehe `prometheus.yml`)
   - `for: 1m` bedeutet: Bedingung muss 1 Minute lang erfüllt sein
   - → Warte mindestens 1 Minute, nachdem Drawdown > 5%

---

### 7.4 Redis-Exporter zeigt keine Daten

**Problem:** `redis_up` = 0 oder Metriken fehlen.

**Lösung:**
1. **Redis-Exporter-Logs:**
   ```bash
   docker compose logs cdb_redis_exporter
   ```
   - Falls "ERR invalid password": `REDIS_PASSWORD` in `.env` falsch

2. **Redis-Verbindung testen:**
   ```bash
   docker compose exec cdb_redis redis-cli -a $REDIS_PASSWORD ping
   ```
   - Erwartung: "PONG"

3. **Exporter manuell testen:**
   ```bash
   curl -s http://localhost:9121/metrics | grep redis_up
   ```
   - Erwartung: `redis_up 1`

---

### 7.5 PostgreSQL-Exporter zeigt keine Daten

**Problem:** `pg_up` = 0 oder Metriken fehlen.

**Lösung:**
1. **PostgreSQL-Exporter-Logs:**
   ```bash
   docker compose logs cdb_postgres_exporter
   ```
   - Falls "connection refused": PostgreSQL noch nicht ready → Warte 30s

2. **PostgreSQL-Verbindung testen:**
   ```bash
   docker compose exec cdb_postgres psql -U $POSTGRES_USER -d claire_de_binaire -c "SELECT 1;"
   ```
   - Erwartung: "1"

3. **DATA_SOURCE_NAME prüfen:**
   ```bash
   docker compose exec cdb_postgres_exporter env | grep DATA_SOURCE_NAME
   ```
   - Format: `postgresql://user:pass@host:5432/db?sslmode=disable`

---

## 8. Wartung

### 8.1 Metrics-Coverage erhöhen

**Aktuell:** Basis-Metriken vorhanden (Signals, Orders, Trades, PnL, Health).

**Nächste Schritte:**
1. **Zusätzliche Business-Metriken:**
   - Win-Rate pro Strategy
   - Average Trade Duration
   - Symbol-Performance (PnL by symbol)

2. **Erweiterte Risk-Metriken:**
   - Value-at-Risk (VaR)
   - Sharpe Ratio (rolling 30d)
   - Max Drawdown (historical)

3. **Custom Alerts:**
   - "Low Win-Rate" (< 40%)
   - "High Volatility Detected"
   - "Unusual Trading Volume"

**Implementierung:**
- Neue Metriken in `services_common/metrics.py` definieren
- In Services aufrufen
- Prometheus/Grafana zeigen sie automatisch

---

### 8.2 Dashboard-Erweiterung

**Vorgehen:**
1. Grafana UI → Dashboard öffnen → "Add Panel"
2. Query schreiben (Prometheus-Syntax)
3. Visualization wählen (Time Series, Gauge, Table, etc.)
4. Panel konfigurieren (Thresholds, Colors, Units)
5. Dashboard speichern

**Best Practices:**
- **Konsistente Namensgebung:** Panel-Titel immer mit Metrik-Typ (z.B. "Total Signals (Counter)")
- **Thresholds nutzen:** Rot/Gelb/Grün für schnelle visuelle Orientierung
- **Legends klar:** `{{symbol}}` statt `{{__name__}}`

---

### 8.3 Retention & Performance

**Aktuell:** Prometheus speichert 14 Tage Daten (`--storage.tsdb.retention.time=14d`).

**Bei Performance-Problemen:**
1. **Retention reduzieren:**
   - `monitoring/prometheus/prometheus.yml` → command → `--storage.tsdb.retention.time=7d`
   - `docker compose restart cdb_prometheus`

2. **Scrape-Intervall erhöhen:**
   - `monitoring/prometheus/prometheus.yml` → `scrape_interval: 30s` (statt 15s)

3. **High-Cardinality-Labels reduzieren:**
   - **Falsch:** `order_id` als Label (zu viele unique values)
   - **Richtig:** `symbol` als Label (wenige unique values)

---

### 8.4 Backup & Restore

**Prometheus-Daten sichern:**
```bash
# Stoppe Prometheus
docker compose stop cdb_prometheus

# Backup erstellen
docker run --rm -v cdb_prom_data:/data -v $(pwd):/backup alpine tar czf /backup/prom_backup_$(date +%Y%m%d).tar.gz /data

# Prometheus wieder starten
docker compose start cdb_prometheus
```

**Grafana-Dashboards sichern:**
```bash
# Dashboard-JSON exportieren via UI:
# Grafana → Dashboard → Settings → JSON Model → Copy to Clipboard
# → In Datei speichern: monitoring/grafana/dashboards/trading-overview.json
```

**Restore:**
```bash
# Prometheus-Daten wiederherstellen
docker compose stop cdb_prometheus
docker run --rm -v cdb_prom_data:/data -v $(pwd):/backup alpine tar xzf /backup/prom_backup_20251121.tar.gz -C /
docker compose start cdb_prometheus
```

---

## Anhang A: Vollständige Command-Liste

```bash
# === SETUP ===
# 1. Docker-Compose validieren
docker compose config --quiet

# 2. Stack starten
docker compose up -d

# 3. Status prüfen
docker compose ps

# === VALIDIERUNG ===
# 4. Prometheus-Targets
curl -s http://localhost:19090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# 5. Metrics-Endpoints testen
curl -s http://localhost:8001/metrics | grep -E "^cdb_" | head -5
curl -s http://localhost:8002/metrics | grep -E "^cdb_" | head -5
curl -s http://localhost:8003/metrics | grep -E "^cdb_" | head -5

# 6. Grafana-Login testen
curl -s http://localhost:3000/api/health | jq .

# === MONITORING ===
# 7. Live-Metriken beobachten
watch -n 2 'curl -s http://localhost:19090/api/v1/query?query=cdb_signals_generated_total | jq .data.result[0].value[1]'

# 8. Alert-Status prüfen
curl -s http://localhost:19090/api/v1/alerts | jq '.data.alerts[] | {alert: .labels.alertname, state: .state}'

# 9. E2E-Tests mit Metriken
pytest -v -m e2e

# === TROUBLESHOOTING ===
# 10. Logs anzeigen
docker compose logs cdb_core --tail=50
docker compose logs cdb_prometheus --tail=50
docker compose logs cdb_grafana --tail=50

# 11. Container neu starten
docker compose restart cdb_prometheus cdb_grafana

# 12. Vollständiger Neustart
docker compose down && docker compose up -d --build
```

---

## Anhang B: Checkliste für Go-Live

- [ ] Alle 11 Services "healthy" (`docker compose ps`)
- [ ] Prometheus scraped alle 7 Targets (`/targets` zeigt UP)
- [ ] Grafana Datasource "Prometheus" funktioniert (Test erfolgreich)
- [ ] 3 Dashboards erstellt (Trading Overview, Risk & Alerts, System Health)
- [ ] `/metrics`-Endpoints in cdb_core, cdb_risk, cdb_execution implementiert
- [ ] E2E-Tests laufen durch und Metriken steigen (`pytest -m e2e`)
- [ ] Mindestens 1 Alert getestet (z.B. ServiceDown durch `docker compose stop cdb_core`)
- [ ] Alertmanager erreichbar (`http://localhost:9093`)
- [ ] Dokumentation gelesen und verstanden

---

## Changelog

| Version | Datum | Änderungen |
|---------|-------|------------|
| 1.0 | 2025-11-21 | Initial Release – Vollständiges Setup-Handbuch |

---

**Dokument-Status:** ✅ Ready for Execution
**Nächste Review:** Nach Durchführung und Feedback

---

**Ende des Handbuchs**
