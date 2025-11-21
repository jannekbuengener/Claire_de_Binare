# Monitoring & Alerting Specification – Claire de Binaire

**Projekt:** Claire de Binaire – Autonomer Krypto-Trading-Bot
**Phase:** N1 – Paper-Test Implementation
**Version:** 1.0
**Datum:** 2025-11-21
**Status:** ✅ Final Specification

---

## 📋 Inhaltsverzeichnis

1. [Executive Summary](#1-executive-summary)
2. [Monitoring-Architektur](#2-monitoring-architektur)
3. [Prometheus-Metriken](#3-prometheus-metriken)
4. [Grafana-Dashboards](#4-grafana-dashboards)
5. [Alert-Regeln](#5-alert-regeln)
6. [Grafana-Panel-JSON-Vorlagen](#6-grafana-panel-json-vorlagen)
7. [Implementierungs-Leitfaden](#7-implementierungs-leitfaden)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Executive Summary

### 1.1 Zweck

Dieses Dokument spezifiziert das vollständige Monitoring- und Alerting-System für Claire de Binaire, umfassend:

- **Prometheus-Metriken** für alle Services (Business-, Risk-, System-, Infrastructure-Ebene)
- **3 Grafana-Dashboards** (Trading Overview, Risk & Alerts, System Health)
- **10 Prometheus-Alert-Regeln** für kritische System- und Risk-Events
- **JSON-Vorlagen** für Grafana-Panel-Konfigurationen

### 1.2 Scope

**Überwachte Services:**
- **cdb_core** (Signal Engine) – Port 8001
- **cdb_risk** (Risk Manager) – Port 8002
- **cdb_execution** (Execution Service) – Port 8003
- **cdb_ws** (WebSocket Screener) – Port 8000
- **cdb_rest** (REST Screener) – Port 8080
- **cdb_redis** (Message Bus) – Port 6379
- **cdb_postgres** (Database) – Port 5432

**Monitoring-Stack:**
- **Prometheus** (Port 19090 Host → 9090 Container)
- **Grafana** (Port 3000)
- **Alertmanager** (optional, für Notification Routing)

### 1.3 Key Metrics

| Kategorie | Anzahl Metriken | Beispiele |
|-----------|----------------|-----------|
| **Business** | 15 | Signale generiert, Orders approved, Trades executed, PnL |
| **Risk** | 12 | Daily Drawdown, Exposure, Violations, Circuit-Breaker |
| **System** | 18 | Latency, Throughput, Errors, Event-Queue-Länge |
| **Infrastructure** | 10 | CPU, Memory, Disk, DB Connections, Redis Keys |
| **GESAMT** | **55** | — |

---

## 2. Monitoring-Architektur

### 2.1 Komponenten-Übersicht

```mermaid
flowchart TB
    subgraph Services["🐳 Claire Services"]
        WS[cdb_ws<br/>WebSocket Screener<br/>:8000]
        REST[cdb_rest<br/>REST Screener<br/>:8080]
        CORE[cdb_core<br/>Signal Engine<br/>:8001]
        RISK[cdb_risk<br/>Risk Manager<br/>:8002]
        EXEC[cdb_execution<br/>Execution Service<br/>:8003]
    end

    subgraph Infra["🔧 Infrastructure"]
        REDIS[(cdb_redis<br/>:6379)]
        PG[(cdb_postgres<br/>:5432)]
    end

    subgraph Monitoring["📊 Monitoring Stack"]
        PROM[Prometheus<br/>:9090<br/>Metrics Collection]
        GRAF[Grafana<br/>:3000<br/>Visualization]
        AM[Alertmanager<br/>:9093<br/>Notifications]
    end

    WS -->|/metrics| PROM
    REST -->|/metrics| PROM
    CORE -->|/metrics| PROM
    RISK -->|/metrics| PROM
    EXEC -->|/metrics| PROM
    REDIS -->|redis_exporter| PROM
    PG -->|postgres_exporter| PROM

    PROM -->|Datasource| GRAF
    PROM -->|Alert Rules| AM
    AM -->|Email/Slack| NOTIF[📧 Notifications]
```

### 2.2 Metriken-Export-Pattern

Alle Python-Services (cdb_*) exportieren Metriken via **Prometheus Client Library**:

```python
# services/<service>/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Business Metrics
signals_generated = Counter('cdb_signals_generated_total', 'Total signals generated', ['symbol', 'direction'])
orders_approved = Counter('cdb_orders_approved_total', 'Orders approved by risk', ['symbol'])
trades_executed = Counter('cdb_trades_executed_total', 'Trades executed', ['symbol', 'side'])

# System Metrics
event_processing_duration = Histogram('cdb_event_processing_duration_seconds',
                                      'Event processing duration',
                                      ['service', 'event_type'])

# Endpoint: GET /metrics
@app.route('/metrics')
def metrics():
    return generate_latest()
```

**Scrape-Konfiguration (prometheus.yml):**
```yaml
scrape_configs:
  - job_name: 'cdb_services'
    scrape_interval: 15s
    static_configs:
      - targets:
          - 'cdb_ws:8000'
          - 'cdb_rest:8080'
          - 'cdb_core:8001'
          - 'cdb_risk:8002'
          - 'cdb_execution:8003'
    metrics_path: '/metrics'

  - job_name: 'redis'
    static_configs:
      - targets: ['cdb_redis:6379']

  - job_name: 'postgres'
    static_configs:
      - targets: ['cdb_postgres:5432']
```

---

## 3. Prometheus-Metriken

### 3.1 Service: cdb_core (Signal Engine)

#### Business-Metriken

| Metrik | Typ | Labels | Beschreibung |
|--------|-----|--------|--------------|
| `cdb_signals_generated_total` | Counter | `symbol`, `direction`, `strategy` | Anzahl generierter Signale |
| `cdb_signal_strength` | Histogram | `symbol`, `strategy` | Signal-Stärke (0.0-1.0) |
| `cdb_market_data_events_received_total` | Counter | `symbol`, `source` | Empfangene Market-Data-Events |
| `cdb_indicators_calculated_total` | Counter | `indicator_type`, `symbol` | Berechnete technische Indikatoren |

#### System-Metriken

| Metrik | Typ | Labels | Beschreibung |
|--------|-----|--------|--------------|
| `cdb_signal_processing_duration_seconds` | Histogram | `strategy` | Signalverarbeitungs-Dauer |
| `cdb_signal_errors_total` | Counter | `error_type` | Fehler bei Signalgenerierung |
| `cdb_redis_publish_duration_seconds` | Histogram | `topic` | Redis-Publish-Latenz |
| `cdb_health_status` | Gauge | `service=cdb_core` | Health-Status (1=healthy, 0=unhealthy) |

**Beispiel-Queries:**
```promql
# Signale pro Minute
rate(cdb_signals_generated_total[1m])

# P95 Signal-Processing-Zeit
histogram_quantile(0.95, cdb_signal_processing_duration_seconds_bucket)

# Fehlerrate
rate(cdb_signal_errors_total[5m]) / rate(cdb_signals_generated_total[5m])
```

---

### 3.2 Service: cdb_risk (Risk Manager)

#### Business-Metriken

| Metrik | Typ | Labels | Beschreibung |
|--------|-----|--------|--------------|
| `cdb_signals_evaluated_total` | Counter | `symbol` | Anzahl evaluierter Signale |
| `cdb_orders_approved_total` | Counter | `symbol` | Genehmigte Orders |
| `cdb_orders_rejected_total` | Counter | `symbol`, `reason_code` | Abgelehnte Orders (mit Reason) |
| `cdb_approved_order_size` | Histogram | `symbol` | Größe genehmigter Orders |

#### Risk-Metriken

| Metrik | Typ | Labels | Beschreibung |
|--------|-----|--------|--------------|
| `cdb_daily_drawdown_pct` | Gauge | — | Aktueller Daily Drawdown (%) |
| `cdb_total_exposure_pct` | Gauge | — | Gesamtes Portfolio-Exposure (%) |
| `cdb_position_exposure_pct` | Gauge | `symbol` | Exposure pro Symbol (%) |
| `cdb_risk_violations_total` | Counter | `violation_type`, `layer` | Risk-Limit-Verletzungen |
| `cdb_circuit_breaker_active` | Gauge | — | Circuit-Breaker-Status (1=aktiv, 0=inaktiv) |
| `cdb_stop_loss_triggered_total` | Counter | `symbol` | Ausgelöste Stop-Loss-Orders |
| `cdb_data_staleness_seconds` | Gauge | `source` | Alter der letzten Marktdaten |
| `cdb_risk_layer_checks_total` | Counter | `layer`, `result` | Checks pro Risk-Layer (passed/failed) |

#### System-Metriken

| Metrik | Typ | Labels | Beschreibung |
|--------|-----|--------|--------------|
| `cdb_risk_decision_duration_seconds` | Histogram | — | Risk-Decision-Latenz |
| `cdb_risk_state_update_duration_seconds` | Histogram | — | RiskState-Update-Dauer |
| `cdb_health_status` | Gauge | `service=cdb_risk` | Health-Status |

**Beispiel-Queries:**
```promql
# Approval-Rate
sum(rate(cdb_orders_approved_total[5m])) /
sum(rate(cdb_signals_evaluated_total[5m]))

# Rejection-Gründe (Top 5)
topk(5, sum by (reason_code) (rate(cdb_orders_rejected_total[1h])))

# Circuit-Breaker-Historie
changes(cdb_circuit_breaker_active[1h])
```

---

### 3.3 Service: cdb_execution (Execution Service)

#### Business-Metriken

| Metrik | Typ | Labels | Beschreibung |
|--------|-----|--------|--------------|
| `cdb_orders_received_total` | Counter | `symbol` | Empfangene Orders |
| `cdb_trades_executed_total` | Counter | `symbol`, `side` | Ausgeführte Trades |
| `cdb_trade_pnl_usd` | Histogram | `symbol` | Trade-PnL in USD |
| `cdb_cumulative_pnl_usd` | Gauge | — | Kumulativer PnL |
| `cdb_open_positions` | Gauge | `symbol` | Anzahl offener Positionen |
| `cdb_position_size` | Gauge | `symbol` | Größe offener Positionen |

#### System-Metriken

| Metrik | Typ | Labels | Beschreibung |
|--------|-----|--------|--------------|
| `cdb_order_execution_duration_seconds` | Histogram | `exchange` | Order-Execution-Latenz |
| `cdb_execution_errors_total` | Counter | `error_type` | Execution-Fehler |
| `cdb_slippage_bps` | Histogram | `symbol` | Slippage in Basispunkten |
| `cdb_health_status` | Gauge | `service=cdb_execution` | Health-Status |

**Beispiel-Queries:**
```promql
# Durchschnittlicher PnL pro Trade
avg(cdb_trade_pnl_usd)

# Win-Rate (Trades mit PnL > 0)
sum(cdb_trade_pnl_usd > 0) / sum(cdb_trades_executed_total)

# P99 Execution-Latenz
histogram_quantile(0.99, cdb_order_execution_duration_seconds_bucket)
```

---

### 3.4 Service: cdb_ws / cdb_rest (Market Data Screener)

#### Business-Metriken

| Metrik | Typ | Labels | Beschreibung |
|--------|-----|--------|--------------|
| `cdb_market_data_received_total` | Counter | `symbol`, `source` | Empfangene Market-Data-Events |
| `cdb_websocket_connections_active` | Gauge | — | Aktive WebSocket-Verbindungen |
| `cdb_rest_requests_total` | Counter | `endpoint`, `status_code` | REST-API-Requests |

#### System-Metriken

| Metrik | Typ | Labels | Beschreibung |
|--------|-----|--------|--------------|
| `cdb_data_ingestion_latency_seconds` | Histogram | `source` | Data-Ingestion-Latenz |
| `cdb_websocket_reconnects_total` | Counter | — | WebSocket-Reconnects |
| `cdb_health_status` | Gauge | `service` | Health-Status |

---

### 3.5 Infrastructure: cdb_redis

**Exportiert via redis_exporter (https://github.com/oliver006/redis_exporter)**

| Metrik | Typ | Beschreibung |
|--------|-----|--------------|
| `redis_connected_clients` | Gauge | Anzahl verbundener Clients |
| `redis_used_memory_bytes` | Gauge | Belegter Speicher |
| `redis_commands_processed_total` | Counter | Verarbeitete Commands |
| `redis_keyspace_hits_total` | Counter | Cache-Hits |
| `redis_keyspace_misses_total` | Counter | Cache-Misses |
| `redis_pubsub_channels` | Gauge | Anzahl Pub/Sub-Channels |
| `redis_pubsub_patterns` | Gauge | Anzahl Pub/Sub-Patterns |

**Beispiel-Query:**
```promql
# Cache-Hit-Rate
rate(redis_keyspace_hits_total[5m]) /
(rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))
```

---

### 3.6 Infrastructure: cdb_postgres

**Exportiert via postgres_exporter (https://github.com/prometheus-community/postgres_exporter)**

| Metrik | Typ | Beschreibung |
|--------|-----|--------------|
| `pg_up` | Gauge | PostgreSQL erreichbar (1=up, 0=down) |
| `pg_stat_database_numbackends` | Gauge | Anzahl Verbindungen |
| `pg_stat_database_xact_commit` | Counter | Committed Transactions |
| `pg_stat_database_xact_rollback` | Counter | Rolled-back Transactions |
| `pg_stat_database_blks_read` | Counter | Disk-Blocks gelesen |
| `pg_stat_database_tup_inserted` | Counter | Eingefügte Rows |
| `pg_database_size_bytes` | Gauge | Datenbankgröße |

**Beispiel-Query:**
```promql
# Rollback-Rate
rate(pg_stat_database_xact_rollback{datname="claire_de_binaire"}[5m])
```

---

## 4. Grafana-Dashboards

### 4.1 Dashboard 1: Trading Overview

**UID:** `cdb-trading-overview`
**Refresh:** 10s
**Zweck:** Hauptübersicht aller Trading-Aktivitäten, Signale, Orders, Trades, PnL.

#### Panel-Struktur

```
┌─────────────────────────────────────────────────────────────────┐
│ 📊 TRADING OVERVIEW                                             │
├─────────────────────────────────────────────────────────────────┤
│ Row 1: Key Performance Indicators (KPIs)                        │
├──────────────────┬──────────────────┬──────────────────┬────────┤
│ 📈 Total Signals │ ✅ Orders Approved│ 💼 Trades Executed│ 💰 PnL│
│   (Counter)      │   (Counter)      │   (Counter)      │ (Gauge)│
├──────────────────┴──────────────────┴──────────────────┴────────┤
│ Row 2: Time-Series Charts                                       │
├─────────────────────────────────────────────────────────────────┤
│ 📉 Signals per Minute (Line Chart)                              │
│    - BY symbol (multi-line)                                     │
├─────────────────────────────────────────────────────────────────┤
│ 📊 Order Approval Rate (Line Chart)                             │
│    - approved / evaluated (%)                                   │
├─────────────────────────────────────────────────────────────────┤
│ 💸 Cumulative PnL (Area Chart)                                  │
│    - Gesamt-PnL über Zeit                                       │
├──────────────────┬──────────────────────────────────────────────┤
│ Row 3: Distribution & Analysis                                  │
├──────────────────┼──────────────────────────────────────────────┤
│ 🎯 Signal Strength│ 📋 Top Traded Symbols (Bar Chart)           │
│   (Histogram)    │    - BY trade_count                          │
├──────────────────┴──────────────────────────────────────────────┤
│ Row 4: Rejection Analysis                                       │
├─────────────────────────────────────────────────────────────────┤
│ ❌ Order Rejection Reasons (Pie Chart)                          │
│    - BY reason_code                                             │
└─────────────────────────────────────────────────────────────────┘
```

#### Panel-Definitionen

**Panel 1.1: Total Signals (Stat Panel)**
```promql
sum(cdb_signals_generated_total)
```

**Panel 1.2: Orders Approved (Stat Panel)**
```promql
sum(cdb_orders_approved_total)
```

**Panel 1.3: Trades Executed (Stat Panel)**
```promql
sum(cdb_trades_executed_total)
```

**Panel 1.4: Current PnL (Stat Panel)**
```promql
cdb_cumulative_pnl_usd
```
- **Thresholds:**
  - Green: > 0
  - Red: < 0

**Panel 2.1: Signals per Minute (Time Series)**
```promql
sum by (symbol) (rate(cdb_signals_generated_total[1m]))
```
- **Legend:** `{{symbol}}`
- **Y-Axis:** Signals/min

**Panel 2.2: Order Approval Rate (Time Series)**
```promql
sum(rate(cdb_orders_approved_total[5m])) /
sum(rate(cdb_signals_evaluated_total[5m])) * 100
```
- **Y-Axis:** Percentage (%)
- **Unit:** Percent (0-100)
- **Thresholds:**
  - Green: > 70%
  - Yellow: 50-70%
  - Red: < 50%

**Panel 2.3: Cumulative PnL (Time Series - Area)**
```promql
cdb_cumulative_pnl_usd
```
- **Fill:** Gradient (green if positive, red if negative)
- **Y-Axis:** USD

**Panel 3.1: Signal Strength Distribution (Histogram)**
```promql
histogram_quantile(0.5, cdb_signal_strength_bucket)
histogram_quantile(0.75, cdb_signal_strength_bucket)
histogram_quantile(0.95, cdb_signal_strength_bucket)
```
- **Legend:** P50, P75, P95

**Panel 3.2: Top Traded Symbols (Bar Gauge)**
```promql
topk(10, sum by (symbol) (cdb_trades_executed_total))
```
- **Orientation:** Horizontal
- **Sort:** Descending

**Panel 4.1: Order Rejection Reasons (Pie Chart)**
```promql
sum by (reason_code) (cdb_orders_rejected_total)
```
- **Legend:** `{{reason_code}}`
- **Display:** Percentage

---

### 4.2 Dashboard 2: Risk & Alerts

**UID:** `cdb-risk-alerts`
**Refresh:** 5s
**Zweck:** Überwachung aller Risk-Metriken, Circuit-Breaker, Drawdown, Exposure.

#### Panel-Struktur

```
┌─────────────────────────────────────────────────────────────────┐
│ 🛡️ RISK & ALERTS                                                │
├─────────────────────────────────────────────────────────────────┤
│ Row 1: Critical Risk Indicators                                 │
├──────────────────┬──────────────────┬──────────────────┬────────┤
│ 📉 Daily Drawdown│ 📊 Total Exposure│ ⚠️ Circuit Breaker│🔴 Active│
│   (Gauge)        │   (Gauge)        │   (Stat)         │ Alerts │
├──────────────────┴──────────────────┴──────────────────┴────────┤
│ Row 2: Risk Limits Over Time                                    │
├─────────────────────────────────────────────────────────────────┤
│ 📈 Daily Drawdown History (Line Chart)                          │
│    - Threshold: 5% (MAX_DAILY_DRAWDOWN_PCT)                     │
├─────────────────────────────────────────────────────────────────┤
│ 📊 Total Exposure History (Line Chart)                          │
│    - Threshold: 50% (MAX_EXPOSURE_PCT)                          │
├──────────────────┬──────────────────────────────────────────────┤
│ Row 3: Risk Violations                                          │
├──────────────────┼──────────────────────────────────────────────┤
│ 🚨 Violations by │ 📋 Violations by Risk Layer (Bar Chart)      │
│   Type (Pie)     │    - Layer 1-6                               │
├──────────────────┴──────────────────────────────────────────────┤
│ Row 4: Position-Level Risk                                      │
├─────────────────────────────────────────────────────────────────┤
│ 📊 Position Exposure by Symbol (Table)                          │
│    - Columns: symbol, exposure_pct, size, pnl                   │
├─────────────────────────────────────────────────────────────────┤
│ Row 5: Alert Log                                                │
├─────────────────────────────────────────────────────────────────┤
│ 📜 Recent Alerts (Logs Panel)                                   │
│    - Last 100 alerts (RISK_LIMIT, CIRCUIT_BREAKER, DATA_STALE) │
└─────────────────────────────────────────────────────────────────┘
```

#### Panel-Definitionen

**Panel 1.1: Daily Drawdown (Gauge)**
```promql
cdb_daily_drawdown_pct
```
- **Unit:** Percent (%)
- **Thresholds:**
  - Green: 0-3%
  - Yellow: 3-4.5%
  - Red: > 4.5% (nahe 5% Limit)
- **Max:** 5.0 (MAX_DAILY_DRAWDOWN_PCT)

**Panel 1.2: Total Exposure (Gauge)**
```promql
cdb_total_exposure_pct
```
- **Unit:** Percent (%)
- **Thresholds:**
  - Green: 0-30%
  - Yellow: 30-45%
  - Red: > 45% (nahe 50% Limit)
- **Max:** 50.0 (MAX_EXPOSURE_PCT)

**Panel 1.3: Circuit Breaker Status (Stat)**
```promql
cdb_circuit_breaker_active
```
- **Value Mappings:**
  - 0 → "✅ INACTIVE"
  - 1 → "🔴 ACTIVE"
- **Color:**
  - 0 → Green
  - 1 → Red

**Panel 1.4: Active Alerts (Stat)**
```promql
count(ALERTS{alertstate="firing"})
```
- **Color:** Red if > 0

**Panel 2.1: Daily Drawdown History (Time Series)**
```promql
cdb_daily_drawdown_pct
```
- **Threshold Line:** 5.0 (red dashed line)
- **Alert Regions:** Shade area > 4.5% red

**Panel 2.2: Total Exposure History (Time Series)**
```promql
cdb_total_exposure_pct
```
- **Threshold Line:** 50.0 (red dashed line)

**Panel 3.1: Violations by Type (Pie Chart)**
```promql
sum by (violation_type) (rate(cdb_risk_violations_total[1h]))
```

**Panel 3.2: Violations by Risk Layer (Bar Chart)**
```promql
sum by (layer) (rate(cdb_risk_violations_total[1h]))
```
- **X-Axis:** Layer (1-6)
- **Y-Axis:** Violations/hour

**Panel 4.1: Position Exposure by Symbol (Table)**
```promql
cdb_position_exposure_pct
cdb_position_size
# PnL wird aus Execution-Metrics geholt
```
- **Columns:**
  - Symbol
  - Exposure (%)
  - Size (BTC/ETH/etc.)
  - PnL (USD)
- **Sort:** BY Exposure DESC

**Panel 5.1: Recent Alerts (Logs Panel)**
- **Data Source:** Loki (wenn vorhanden) oder Prometheus Alerts
- **Query:**
```promql
ALERTS{alertname=~"DailyDrawdown|CircuitBreaker|DataStale"}
```
- **Time Range:** Last 1 hour
- **Limit:** 100 entries

---

### 4.3 Dashboard 3: System Health

**UID:** `cdb-system-health`
**Refresh:** 15s
**Zweck:** Infrastruktur-Monitoring, Service-Health, Latenz, Fehlerquoten.

#### Panel-Struktur

```
┌─────────────────────────────────────────────────────────────────┐
│ 🏥 SYSTEM HEALTH                                                │
├─────────────────────────────────────────────────────────────────┤
│ Row 1: Service Health Status                                    │
├──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬────────┤
│ WS   │ REST │ CORE │ RISK │ EXEC │ Redis│ PG   │ Prom │ Grafana│
│ (Stat│ (Stat│ (Stat│ (Stat│ (Stat│ (Stat│ (Stat│ (Stat│ (Stat) │
├──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴────────┤
│ Row 2: Latency Metrics                                          │
├─────────────────────────────────────────────────────────────────┤
│ ⏱️ Event Processing Duration P95 (Time Series)                  │
│    - BY service (cdb_core, cdb_risk, cdb_execution)            │
├─────────────────────────────────────────────────────────────────┤
│ Row 3: Throughput & Error Rates                                 │
├──────────────────────────┬──────────────────────────────────────┤
│ 📊 Events/sec by Service │ ❌ Error Rate by Service             │
│   (Time Series)          │   (Time Series)                      │
├──────────────────────────┴──────────────────────────────────────┤
│ Row 4: Infrastructure Metrics                                   │
├──────────────────────────┬──────────────────────────────────────┤
│ 💾 Redis Memory Usage    │ 🗄️ PostgreSQL Connections           │
│   (Gauge)                │   (Time Series)                      │
├──────────────────────────┼──────────────────────────────────────┤
│ 📈 Redis Commands/sec    │ 📊 PostgreSQL Transaction Rate       │
│   (Time Series)          │   (Time Series)                      │
├──────────────────────────┴──────────────────────────────────────┤
│ Row 5: Container Resource Usage                                 │
├─────────────────────────────────────────────────────────────────┤
│ 💻 CPU Usage by Service (Time Series)                           │
├─────────────────────────────────────────────────────────────────┤
│ 🧠 Memory Usage by Service (Time Series)                        │
└─────────────────────────────────────────────────────────────────┘
```

#### Panel-Definitionen

**Panel 1.1-1.9: Service Health Status (Stat Panels)**
```promql
# Für jeden Service (cdb_ws, cdb_rest, cdb_core, cdb_risk, cdb_execution)
cdb_health_status{service="<service_name>"}

# Für Redis
redis_up

# Für PostgreSQL
pg_up
```
- **Value Mappings:**
  - 1 → "✅ HEALTHY"
  - 0 → "🔴 DOWN"
- **Color:**
  - 1 → Green
  - 0 → Red

**Panel 2.1: Event Processing Duration P95 (Time Series)**
```promql
histogram_quantile(0.95,
  sum by (service, le) (rate(cdb_event_processing_duration_seconds_bucket[5m]))
)
```
- **Legend:** `{{service}}`
- **Y-Axis:** Seconds
- **Alert Threshold:** 1.0s (red line)

**Panel 3.1: Events/sec by Service (Time Series)**
```promql
# cdb_core
sum(rate(cdb_signals_generated_total[1m]))

# cdb_risk
sum(rate(cdb_signals_evaluated_total[1m]))

# cdb_execution
sum(rate(cdb_orders_received_total[1m]))
```

**Panel 3.2: Error Rate by Service (Time Series)**
```promql
# cdb_core
rate(cdb_signal_errors_total[5m])

# cdb_execution
rate(cdb_execution_errors_total[5m])
```
- **Y-Axis:** Errors/sec
- **Alert Threshold:** 0.1 errors/sec

**Panel 4.1: Redis Memory Usage (Gauge)**
```promql
redis_used_memory_bytes / 1024 / 1024  # MB
```
- **Unit:** MB
- **Max:** (basierend auf Redis-Container-Limit, z.B. 512 MB)

**Panel 4.2: PostgreSQL Connections (Time Series)**
```promql
pg_stat_database_numbackends{datname="claire_de_binaire"}
```
- **Alert Threshold:** 80% von max_connections

**Panel 4.3: Redis Commands/sec (Time Series)**
```promql
rate(redis_commands_processed_total[1m])
```

**Panel 4.4: PostgreSQL Transaction Rate (Time Series)**
```promql
rate(pg_stat_database_xact_commit{datname="claire_de_binaire"}[1m])
```

**Panel 5.1: CPU Usage by Service (Time Series)**
```promql
rate(container_cpu_usage_seconds_total{container=~"cdb_.*"}[1m]) * 100
```
- **Y-Axis:** Percentage (%)
- **Legend:** `{{container}}`

**Panel 5.2: Memory Usage by Service (Time Series)**
```promql
container_memory_usage_bytes{container=~"cdb_.*"} / 1024 / 1024  # MB
```
- **Y-Axis:** MB
- **Legend:** `{{container}}`

---

## 5. Alert-Regeln

### 5.1 Prometheus Alerting-Konfiguration

**Datei:** `prometheus/alerts.yml`

```yaml
groups:
  - name: claire_de_binaire_critical
    interval: 15s
    rules:

      # ALERT 1: Daily Drawdown Limit Exceeded
      - alert: DailyDrawdownLimitExceeded
        expr: cdb_daily_drawdown_pct > 5.0
        for: 1m
        labels:
          severity: critical
          component: risk_engine
        annotations:
          summary: "Daily Drawdown Limit Exceeded"
          description: "Daily drawdown is {{ $value | humanizePercentage }}, exceeding 5% limit. Trading stopped."
          runbook_url: "https://docs.claire/runbooks/daily-drawdown"

      # ALERT 2: Circuit Breaker Activated
      - alert: CircuitBreakerActivated
        expr: cdb_circuit_breaker_active == 1
        for: 30s
        labels:
          severity: critical
          component: risk_engine
        annotations:
          summary: "Circuit Breaker Activated"
          description: "Market anomalies detected (high slippage or spread). Trading paused."
          runbook_url: "https://docs.claire/runbooks/circuit-breaker"

      # ALERT 3: Service Down
      - alert: ServiceDown
        expr: cdb_health_status == 0
        for: 1m
        labels:
          severity: critical
          component: "{{ $labels.service }}"
        annotations:
          summary: "Service {{ $labels.service }} is DOWN"
          description: "Health check failed for service {{ $labels.service }}."
          runbook_url: "https://docs.claire/runbooks/service-restart"

      # ALERT 4: High Error Rate
      - alert: HighErrorRate
        expr: |
          (
            rate(cdb_signal_errors_total[5m]) +
            rate(cdb_execution_errors_total[5m])
          ) > 0.1
        for: 5m
        labels:
          severity: warning
          component: system
        annotations:
          summary: "High Error Rate Detected"
          description: "Error rate is {{ $value | humanize }} errors/sec over last 5 minutes."
          runbook_url: "https://docs.claire/runbooks/error-rate"

      # ALERT 5: Stale Market Data
      - alert: StaleMarketData
        expr: cdb_data_staleness_seconds > 30
        for: 1m
        labels:
          severity: warning
          component: market_data
        annotations:
          summary: "Stale Market Data Detected"
          description: "No market data received for {{ $value }} seconds from {{ $labels.source }}."
          runbook_url: "https://docs.claire/runbooks/data-stale"

      # ALERT 6: Exposure Limit Approaching
      - alert: ExposureLimitApproaching
        expr: cdb_total_exposure_pct > 45.0
        for: 5m
        labels:
          severity: warning
          component: risk_engine
        annotations:
          summary: "Portfolio Exposure Approaching Limit"
          description: "Total exposure is {{ $value | humanizePercentage }}, approaching 50% limit."
          runbook_url: "https://docs.claire/runbooks/exposure-limit"

      # ALERT 7: Position Size Violation
      - alert: PositionSizeViolation
        expr: cdb_position_exposure_pct > 10.0
        for: 2m
        labels:
          severity: warning
          component: risk_engine
        annotations:
          summary: "Position Size Exceeds Limit for {{ $labels.symbol }}"
          description: "Position {{ $labels.symbol }} has {{ $value | humanizePercentage }} exposure, exceeding 10% limit."
          runbook_url: "https://docs.claire/runbooks/position-size"

      # ALERT 8: High Event Processing Latency
      - alert: HighEventProcessingLatency
        expr: |
          histogram_quantile(0.95,
            sum by (service, le) (rate(cdb_event_processing_duration_seconds_bucket[5m]))
          ) > 1.0
        for: 5m
        labels:
          severity: warning
          component: "{{ $labels.service }}"
        annotations:
          summary: "High Event Processing Latency in {{ $labels.service }}"
          description: "P95 latency is {{ $value | humanizeDuration }} in {{ $labels.service }}."
          runbook_url: "https://docs.claire/runbooks/latency"

      # ALERT 9: Database Connection Failures
      - alert: DatabaseConnectionFailures
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
          component: database
        annotations:
          summary: "PostgreSQL Database Unreachable"
          description: "Cannot connect to PostgreSQL database claire_de_binaire."
          runbook_url: "https://docs.claire/runbooks/database-down"

      # ALERT 10: Redis Unavailable
      - alert: RedisUnavailable
        expr: redis_up == 0
        for: 1m
        labels:
          severity: critical
          component: message_bus
        annotations:
          summary: "Redis Message Bus Unavailable"
          description: "Cannot connect to Redis. Event routing stopped."
          runbook_url: "https://docs.claire/runbooks/redis-down"

  - name: claire_de_binaire_info
    interval: 1m
    rules:

      # INFO: Positive PnL Milestone
      - alert: PositivePnLMilestone
        expr: cdb_cumulative_pnl_usd > 1000
        labels:
          severity: info
          component: trading
        annotations:
          summary: "Positive PnL Milestone Reached"
          description: "Cumulative PnL is ${{ $value | humanize }}. 🎉"
```

### 5.2 Alert-Routing (Alertmanager)

**Datei:** `alertmanager/alertmanager.yml`

```yaml
global:
  resolve_timeout: 5m
  slack_api_url: '<SLACK_WEBHOOK_URL>'

route:
  receiver: 'default'
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 3h

  routes:
    # Critical Alerts → Slack + Email
    - match:
        severity: critical
      receiver: 'critical-alerts'
      continue: false

    # Warning Alerts → Slack only
    - match:
        severity: warning
      receiver: 'warning-alerts'
      continue: false

    # Info Alerts → Log only
    - match:
        severity: info
      receiver: 'info-alerts'
      continue: false

receivers:
  - name: 'default'
    slack_configs:
      - channel: '#claire-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'critical-alerts'
    slack_configs:
      - channel: '#claire-critical'
        title: '🚨 CRITICAL: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
        send_resolved: true
    email_configs:
      - to: 'ops@claire.trading'
        from: 'alertmanager@claire.trading'
        smarthost: 'smtp.gmail.com:587'
        auth_username: '<USERNAME>'
        auth_password: '<PASSWORD>'

  - name: 'warning-alerts'
    slack_configs:
      - channel: '#claire-alerts'
        title: '⚠️ WARNING: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
        send_resolved: true

  - name: 'info-alerts'
    webhook_configs:
      - url: 'http://cdb_logger:8080/alerts'
```

---

## 6. Grafana-Panel-JSON-Vorlagen

### 6.1 Stat Panel: Total Signals

```json
{
  "type": "stat",
  "title": "Total Signals",
  "targets": [
    {
      "expr": "sum(cdb_signals_generated_total)",
      "refId": "A"
    }
  ],
  "options": {
    "reduceOptions": {
      "values": false,
      "calcs": ["lastNotNull"]
    },
    "orientation": "auto",
    "textMode": "value_and_name",
    "colorMode": "value",
    "graphMode": "area",
    "justifyMode": "auto"
  },
  "fieldConfig": {
    "defaults": {
      "mappings": [],
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {
            "value": null,
            "color": "green"
          },
          {
            "value": 100,
            "color": "yellow"
          },
          {
            "value": 1000,
            "color": "red"
          }
        ]
      },
      "unit": "short",
      "decimals": 0
    }
  },
  "gridPos": {
    "h": 4,
    "w": 6,
    "x": 0,
    "y": 0
  }
}
```

### 6.2 Time Series Panel: Signals per Minute

```json
{
  "type": "timeseries",
  "title": "Signals per Minute",
  "targets": [
    {
      "expr": "sum by (symbol) (rate(cdb_signals_generated_total[1m]))",
      "legendFormat": "{{symbol}}",
      "refId": "A"
    }
  ],
  "options": {
    "tooltip": {
      "mode": "multi",
      "sort": "desc"
    },
    "legend": {
      "displayMode": "table",
      "placement": "right",
      "calcs": ["last", "mean", "max"]
    }
  },
  "fieldConfig": {
    "defaults": {
      "custom": {
        "drawStyle": "line",
        "lineInterpolation": "smooth",
        "lineWidth": 2,
        "fillOpacity": 10,
        "gradientMode": "opacity",
        "spanNulls": false,
        "showPoints": "never",
        "pointSize": 5,
        "stacking": {
          "mode": "none",
          "group": "A"
        },
        "axisPlacement": "auto",
        "axisLabel": "Signals/min",
        "scaleDistribution": {
          "type": "linear"
        }
      },
      "unit": "short",
      "decimals": 2,
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {
            "value": null,
            "color": "green"
          }
        ]
      }
    }
  },
  "gridPos": {
    "h": 8,
    "w": 24,
    "x": 0,
    "y": 4
  }
}
```

### 6.3 Gauge Panel: Daily Drawdown

```json
{
  "type": "gauge",
  "title": "Daily Drawdown",
  "targets": [
    {
      "expr": "cdb_daily_drawdown_pct",
      "refId": "A"
    }
  ],
  "options": {
    "orientation": "auto",
    "showThresholdLabels": true,
    "showThresholdMarkers": true,
    "reduceOptions": {
      "values": false,
      "calcs": ["lastNotNull"]
    }
  },
  "fieldConfig": {
    "defaults": {
      "unit": "percent",
      "decimals": 2,
      "min": 0,
      "max": 5.0,
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {
            "value": 0,
            "color": "green"
          },
          {
            "value": 3.0,
            "color": "yellow"
          },
          {
            "value": 4.5,
            "color": "red"
          }
        ]
      }
    }
  },
  "gridPos": {
    "h": 6,
    "w": 6,
    "x": 0,
    "y": 0
  }
}
```

### 6.4 Pie Chart Panel: Order Rejection Reasons

```json
{
  "type": "piechart",
  "title": "Order Rejection Reasons",
  "targets": [
    {
      "expr": "sum by (reason_code) (cdb_orders_rejected_total)",
      "legendFormat": "{{reason_code}}",
      "refId": "A"
    }
  ],
  "options": {
    "reduceOptions": {
      "values": false,
      "calcs": ["lastNotNull"]
    },
    "pieType": "pie",
    "tooltip": {
      "mode": "single"
    },
    "legend": {
      "displayMode": "table",
      "placement": "right",
      "values": ["value", "percent"]
    },
    "displayLabels": ["percent"]
  },
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "decimals": 0
    }
  },
  "gridPos": {
    "h": 8,
    "w": 12,
    "x": 0,
    "y": 12
  }
}
```

### 6.5 Table Panel: Position Exposure by Symbol

```json
{
  "type": "table",
  "title": "Position Exposure by Symbol",
  "targets": [
    {
      "expr": "cdb_position_exposure_pct",
      "format": "table",
      "instant": true,
      "refId": "A"
    },
    {
      "expr": "cdb_position_size",
      "format": "table",
      "instant": true,
      "refId": "B"
    }
  ],
  "transformations": [
    {
      "id": "merge",
      "options": {}
    },
    {
      "id": "organize",
      "options": {
        "excludeByName": {
          "Time": true,
          "__name__": true,
          "job": true,
          "instance": true
        },
        "indexByName": {
          "symbol": 0,
          "Value #A": 1,
          "Value #B": 2
        },
        "renameByPattern": {
          "Value #A": "Exposure (%)",
          "Value #B": "Size"
        }
      }
    },
    {
      "id": "sortBy",
      "options": {
        "fields": {},
        "sort": [
          {
            "field": "Exposure (%)",
            "desc": true
          }
        ]
      }
    }
  ],
  "options": {
    "showHeader": true,
    "sortBy": [
      {
        "displayName": "Exposure (%)",
        "desc": true
      }
    ]
  },
  "fieldConfig": {
    "defaults": {
      "custom": {
        "align": "auto",
        "displayMode": "auto"
      },
      "mappings": [],
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {
            "value": null,
            "color": "green"
          },
          {
            "value": 8,
            "color": "yellow"
          },
          {
            "value": 9.5,
            "color": "red"
          }
        ]
      },
      "unit": "percent"
    },
    "overrides": [
      {
        "matcher": {
          "id": "byName",
          "options": "symbol"
        },
        "properties": [
          {
            "id": "custom.width",
            "value": 150
          }
        ]
      },
      {
        "matcher": {
          "id": "byName",
          "options": "Size"
        },
        "properties": [
          {
            "id": "unit",
            "value": "short"
          },
          {
            "id": "decimals",
            "value": 4
          }
        ]
      }
    ]
  },
  "gridPos": {
    "h": 10,
    "w": 24,
    "x": 0,
    "y": 20
  }
}
```

### 6.6 Bar Gauge Panel: Top Traded Symbols

```json
{
  "type": "bargauge",
  "title": "Top Traded Symbols",
  "targets": [
    {
      "expr": "topk(10, sum by (symbol) (cdb_trades_executed_total))",
      "legendFormat": "{{symbol}}",
      "refId": "A"
    }
  ],
  "options": {
    "orientation": "horizontal",
    "displayMode": "gradient",
    "showUnfilled": true,
    "reduceOptions": {
      "values": false,
      "calcs": ["lastNotNull"]
    }
  },
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "decimals": 0,
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {
            "value": null,
            "color": "green"
          },
          {
            "value": 50,
            "color": "yellow"
          },
          {
            "value": 100,
            "color": "red"
          }
        ]
      }
    }
  },
  "gridPos": {
    "h": 8,
    "w": 12,
    "x": 12,
    "y": 4
  }
}
```

---

## 7. Implementierungs-Leitfaden

### 7.1 Schritt 1: Prometheus-Client in Services integrieren

**Datei:** `services/<service>/metrics.py`

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
import time
import logging

logger = logging.getLogger(__name__)

# Business Metrics
signals_generated = Counter(
    'cdb_signals_generated_total',
    'Total signals generated',
    ['symbol', 'direction', 'strategy']
)

orders_approved = Counter(
    'cdb_orders_approved_total',
    'Orders approved by risk',
    ['symbol']
)

orders_rejected = Counter(
    'cdb_orders_rejected_total',
    'Orders rejected by risk',
    ['symbol', 'reason_code']
)

# Risk Metrics
daily_drawdown_pct = Gauge(
    'cdb_daily_drawdown_pct',
    'Current daily drawdown percentage'
)

total_exposure_pct = Gauge(
    'cdb_total_exposure_pct',
    'Total portfolio exposure percentage'
)

position_exposure_pct = Gauge(
    'cdb_position_exposure_pct',
    'Position exposure percentage',
    ['symbol']
)

circuit_breaker_active = Gauge(
    'cdb_circuit_breaker_active',
    'Circuit breaker status (1=active, 0=inactive)'
)

risk_violations = Counter(
    'cdb_risk_violations_total',
    'Risk limit violations',
    ['violation_type', 'layer']
)

# System Metrics
event_processing_duration = Histogram(
    'cdb_event_processing_duration_seconds',
    'Event processing duration',
    ['service', 'event_type'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

health_status = Gauge(
    'cdb_health_status',
    'Service health status (1=healthy, 0=unhealthy)',
    ['service']
)

# Utility Functions
def record_signal(symbol: str, direction: str, strategy: str):
    """Record a generated signal"""
    signals_generated.labels(symbol=symbol, direction=direction, strategy=strategy).inc()
    logger.debug(f"Metric recorded: signal {symbol} {direction}")

def record_risk_decision(symbol: str, approved: bool, reason_code: str = None):
    """Record a risk decision"""
    if approved:
        orders_approved.labels(symbol=symbol).inc()
    else:
        orders_rejected.labels(symbol=symbol, reason_code=reason_code or "UNKNOWN").inc()
    logger.debug(f"Metric recorded: risk_decision {symbol} approved={approved}")

def update_drawdown(drawdown_pct: float):
    """Update daily drawdown gauge"""
    daily_drawdown_pct.set(drawdown_pct)
    logger.debug(f"Metric updated: daily_drawdown_pct={drawdown_pct}")

def update_exposure(total_pct: float, position_exposures: dict = None):
    """Update exposure gauges"""
    total_exposure_pct.set(total_pct)
    if position_exposures:
        for symbol, pct in position_exposures.items():
            position_exposure_pct.labels(symbol=symbol).set(pct)
    logger.debug(f"Metric updated: total_exposure_pct={total_pct}")

def record_violation(violation_type: str, layer: int):
    """Record a risk violation"""
    risk_violations.labels(violation_type=violation_type, layer=str(layer)).inc()
    logger.warning(f"Risk violation: {violation_type} at layer {layer}")

def measure_event_processing(service: str, event_type: str):
    """Context manager for measuring event processing time"""
    return event_processing_duration.labels(service=service, event_type=event_type).time()

def set_health_status(service: str, is_healthy: bool):
    """Set service health status"""
    health_status.labels(service=service).set(1 if is_healthy else 0)
    logger.info(f"Health status: {service} = {'healthy' if is_healthy else 'unhealthy'}")

# Flask/FastAPI endpoint
def get_metrics():
    """Return Prometheus metrics in text format"""
    return generate_latest(REGISTRY)
```

**Integration in Service:**

```python
# services/cdb_core/service.py
from flask import Flask, Response
import metrics

app = Flask(__name__)

@app.route('/metrics')
def prometheus_metrics():
    return Response(metrics.get_metrics(), mimetype='text/plain')

@app.route('/health')
def health():
    # ... health check logic
    is_healthy = check_health()
    metrics.set_health_status('cdb_core', is_healthy)
    return {'status': 'ok' if is_healthy else 'error'}

def process_market_data(event):
    with metrics.measure_event_processing('cdb_core', 'market_data'):
        # ... signal generation logic
        signal = generate_signal(event)
        if signal:
            metrics.record_signal(
                symbol=signal['symbol'],
                direction=signal['direction'],
                strategy=signal['strategy']
            )
```

### 7.2 Schritt 2: Prometheus-Konfiguration

**Datei:** `monitoring/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'claire_de_binaire'
    environment: 'production'

# Alertmanager-Konfiguration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - 'cdb_alertmanager:9093'

# Rule Files
rule_files:
  - '/etc/prometheus/alerts.yml'

# Scrape-Konfigurationen
scrape_configs:
  # Claire Services
  - job_name: 'cdb_services'
    scrape_interval: 15s
    static_configs:
      - targets:
          - 'cdb_ws:8000'
          - 'cdb_rest:8080'
          - 'cdb_core:8001'
          - 'cdb_risk:8002'
          - 'cdb_execution:8003'
    metrics_path: '/metrics'
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        regex: 'cdb_([^:]+):.+'
        replacement: '${1}'

  # Redis (via redis_exporter)
  - job_name: 'redis'
    static_configs:
      - targets: ['cdb_redis_exporter:9121']

  # PostgreSQL (via postgres_exporter)
  - job_name: 'postgres'
    static_configs:
      - targets: ['cdb_postgres_exporter:9187']

  # Prometheus selbst
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### 7.3 Schritt 3: Docker-Compose-Erweiterung

**Datei:** `docker-compose.yml` (Ergänzungen)

```yaml
services:
  # ... existing services

  # Redis Exporter
  cdb_redis_exporter:
    image: oliver006/redis_exporter:latest
    container_name: cdb_redis_exporter
    environment:
      - REDIS_ADDR=cdb_redis:6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    ports:
      - "9121:9121"
    networks:
      - cdb_network
    depends_on:
      - cdb_redis
    restart: unless-stopped

  # PostgreSQL Exporter
  cdb_postgres_exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: cdb_postgres_exporter
    environment:
      - DATA_SOURCE_NAME=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@cdb_postgres:5432/claire_de_binaire?sslmode=disable
    ports:
      - "9187:9187"
    networks:
      - cdb_network
    depends_on:
      - cdb_postgres
    restart: unless-stopped

  # Prometheus
  cdb_prometheus:
    image: prom/prometheus:latest
    container_name: cdb_prometheus
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/prometheus/alerts.yml:/etc/prometheus/alerts.yml
      - cdb_prom_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=14d'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    ports:
      - "19090:9090"
    networks:
      - cdb_network
    restart: unless-stopped

  # Grafana
  cdb_grafana:
    image: grafana/grafana:latest
    container_name: cdb_grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=http://localhost:3000
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
      - cdb_grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
    networks:
      - cdb_network
    depends_on:
      - cdb_prometheus
    restart: unless-stopped

  # Alertmanager (optional)
  cdb_alertmanager:
    image: prom/alertmanager:latest
    container_name: cdb_alertmanager
    volumes:
      - ./monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    ports:
      - "9093:9093"
    networks:
      - cdb_network
    restart: unless-stopped

volumes:
  cdb_prom_data:
  cdb_grafana_data:
```

### 7.4 Schritt 4: Grafana-Provisioning

**Datei:** `monitoring/grafana/provisioning/datasources/prometheus.yml`

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://cdb_prometheus:9090
    isDefault: true
    editable: true
```

**Datei:** `monitoring/grafana/provisioning/dashboards/dashboards.yml`

```yaml
apiVersion: 1

providers:
  - name: 'claire_dashboards'
    orgId: 1
    folder: 'Claire de Binaire'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
```

### 7.5 Schritt 5: Dashboard-Import

1. **Manueller Import:**
   - Grafana UI öffnen: http://localhost:3000
   - Login: admin / `${GRAFANA_PASSWORD}`
   - Dashboards → Import → JSON einfügen

2. **Automatischer Import (Provisioning):**
   - Dashboard-JSON in `monitoring/grafana/dashboards/` ablegen
   - Dateinamen: `trading-overview.json`, `risk-alerts.json`, `system-health.json`
   - Restart Grafana: `docker compose restart cdb_grafana`

### 7.6 Schritt 6: Validierung

```bash
# 1. Services starten
docker compose up -d

# 2. Prometheus erreichbar?
curl -fsS http://localhost:19090/-/healthy
# Erwartung: "Prometheus Server is Healthy."

# 3. Metriken von Services abrufen
curl -fsS http://localhost:8001/metrics | grep cdb_
# Erwartung: Liste von cdb_*-Metriken

# 4. Grafana erreichbar?
curl -fsS http://localhost:3000/api/health
# Erwartung: {"database":"ok","version":"..."}

# 5. Alerts konfiguriert?
curl -fsS http://localhost:19090/api/v1/rules | jq .
# Erwartung: JSON mit Alert-Regeln
```

---

## 8. Troubleshooting

### 8.1 Prometheus kann Services nicht scrapen

**Problem:**
```
Get "http://cdb_core:8001/metrics": dial tcp: lookup cdb_core on 127.0.0.11:53: no such host
```

**Lösung:**
1. Prüfen, ob Services im selben Docker-Netzwerk sind:
   ```bash
   docker network inspect cdb_network
   ```
2. Prüfen, ob `/metrics`-Endpoint existiert:
   ```bash
   docker compose exec cdb_core curl -s http://localhost:8001/metrics
   ```
3. Prometheus-Konfiguration prüfen:
   ```bash
   docker compose exec cdb_prometheus cat /etc/prometheus/prometheus.yml
   ```

### 8.2 Metriken werden nicht angezeigt

**Problem:** Metriken sind in Prometheus vorhanden, aber nicht in Grafana sichtbar.

**Lösung:**
1. Datasource-Verbindung testen:
   - Grafana UI → Configuration → Data Sources → Prometheus → "Test"
2. Query in Prometheus testen:
   ```bash
   curl -s 'http://localhost:19090/api/v1/query?query=cdb_signals_generated_total' | jq .
   ```
3. Grafana-Logs prüfen:
   ```bash
   docker compose logs cdb_grafana | grep -i error
   ```

### 8.3 Alerts werden nicht ausgelöst

**Problem:** Alert-Regel ist konfiguriert, aber Alert erscheint nicht.

**Lösung:**
1. Alert-Status in Prometheus prüfen:
   - http://localhost:19090/alerts
2. Alert-Regel-Syntax validieren:
   ```bash
   docker compose exec cdb_prometheus promtool check rules /etc/prometheus/alerts.yml
   ```
3. Alert-Evaluation prüfen:
   ```bash
   curl -s 'http://localhost:19090/api/v1/query?query=cdb_daily_drawdown_pct>5.0' | jq .
   ```

### 8.4 Hohe Kardinalität (High Cardinality)

**Problem:** Zu viele Metrik-Labels führen zu hohem Speicherverbrauch.

**Symptom:**
```
too many time series (cardinality)
```

**Lösung:**
1. Labels mit hoher Kardinalität identifizieren:
   ```bash
   curl -s http://localhost:19090/api/v1/label/__name__/values | jq .
   ```
2. Labels reduzieren:
   - **Falsch:** `symbol="BTCUSDT_12345"` (Order-ID im Label)
   - **Richtig:** `symbol="BTCUSDT"` (nur Symbol)
3. Retention anpassen:
   ```yaml
   # prometheus.yml
   command:
     - '--storage.tsdb.retention.time=7d'  # Reduzieren von 14d auf 7d
   ```

### 8.5 Grafana-Dashboard zeigt "No Data"

**Problem:** Dashboard-Panels zeigen "No Data", obwohl Metriken existieren.

**Lösung:**
1. Time-Range prüfen (oben rechts in Grafana):
   - Sicherstellen, dass Time-Range den Zeitraum abdeckt, in dem Daten existieren
2. Query in Prometheus testen:
   ```bash
   curl -s 'http://localhost:19090/api/v1/query?query=cdb_signals_generated_total' | jq .
   ```
3. Query-Syntax in Panel prüfen:
   - Dashboard → Panel bearbeiten → Query → "Query Inspector"

---

## Anhang A: Metriken-Referenztabelle

| Service | Business | Risk | System | Infra | Gesamt |
|---------|----------|------|--------|-------|--------|
| **cdb_core** | 4 | — | 4 | — | 8 |
| **cdb_risk** | 4 | 8 | 3 | — | 15 |
| **cdb_execution** | 6 | — | 4 | — | 10 |
| **cdb_ws/rest** | 3 | — | 3 | — | 6 |
| **cdb_redis** | — | — | — | 7 | 7 |
| **cdb_postgres** | — | — | — | 7 | 7 |
| **Container** | — | — | — | 2 | 2 |
| **GESAMT** | **17** | **8** | **14** | **16** | **55** |

---

## Anhang B: Alert-Severity-Matrix

| Severity | Response Time | Examples | Notification |
|----------|--------------|----------|--------------|
| **CRITICAL** | < 5 Min | Daily Drawdown > 5%, Service Down, DB Unavailable | Slack + Email + SMS |
| **WARNING** | < 30 Min | High Error Rate, Exposure > 45%, Stale Data | Slack |
| **INFO** | — | Positive PnL Milestone | Log Only |

---

## Anhang C: Dashboard-Links

| Dashboard | UID | URL |
|-----------|-----|-----|
| Trading Overview | `cdb-trading-overview` | http://localhost:3000/d/cdb-trading-overview |
| Risk & Alerts | `cdb-risk-alerts` | http://localhost:3000/d/cdb-risk-alerts |
| System Health | `cdb-system-health` | http://localhost:3000/d/cdb-system-health |

---

## Changelog

| Version | Datum | Änderungen |
|---------|-------|------------|
| 1.0 | 2025-11-21 | Initial Release – 55 Metriken, 3 Dashboards, 10 Alerts |

---

**Dokument-Status:** ✅ Final
**Genehmigt von:** claire-architect
**Nächste Review:** 2025-12-15

---

**Ende der Spezifikation**
