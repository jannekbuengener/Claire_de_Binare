# Monitoring & Alerting Setup

## Übersicht

Dieses Dokument beschreibt die Monitoring- und Alerting-Infrastruktur für CDB gemäß Issue #96.

## Komponenten

| Service | Port | Funktion |
|---------|------|----------|
| Prometheus | 9090 | Metriken-Sammlung |
| AlertManager | 9093 | Alert-Routing & Deduplication |
| Grafana | 3000 | Visualisierung & Dashboards |

## Dashboards

### Verfügbare Dashboards

| Dashboard | UID | Beschreibung |
|-----------|-----|--------------|
| System Performance | `claire_system_v1` | Container Health, CPU, Memory |
| Signal Engine | `claire_signal_v1` | Signal-Generierung, Events/sec |
| Risk Manager | `claire_risk_v1` | P&L, Exposure, Rejections |
| Execution | `claire_execution_v1` | Order Latency, Fill Rate |
| Paper Trading | `claire_paper_v1` | Paper Trading Metrics |
| Database | `claire_database_v1` | PostgreSQL & Redis Metrics |
| HITL Control | `claire_hitl_v1` | Human-in-the-Loop Controls |

### Dashboard URLs

```
System:     http://localhost:3000/d/claire_system_v1
Signal:     http://localhost:3000/d/claire_signal_v1
Risk:       http://localhost:3000/d/claire_risk_v1
Execution:  http://localhost:3000/d/claire_execution_v1
Database:   http://localhost:3000/d/claire_database_v1
```

## Alert Rules

### Critical Alerts (Sofortige Aktion)

| Alert | Condition | Description |
|-------|-----------|-------------|
| `ServiceDown` | `up == 0` for 1m | Service nicht erreichbar |
| `CircuitBreakerTriggered` | `cdb_circuit_breaker_triggered == 1` | Trading gestoppt |
| `DatabaseConnectionLost` | `pg_up == 0` for 30s | PostgreSQL-Verbindung verloren |
| `RedisConnectionLost` | `redis_up == 0` for 30s | Redis-Verbindung verloren |
| `DailyDrawdownExceeded` | `cdb_daily_drawdown_pct > 5` | Drawdown >5% |

### High Priority Alerts

| Alert | Condition | Description |
|-------|-----------|-------------|
| `HighLatency` | P95 > 500ms for 5m | Hohe Latenz erkannt |
| `HighErrorRate` | Error Rate > 5% for 5m | Viele Fehler |
| `OrderProcessingDelayed` | Processing > 1s for 2m | Order-Verarbeitung verzögert |
| `PositionLimitApproaching` | Utilization > 80% | Position-Limit nähert sich |

### Warning Alerts

| Alert | Condition | Description |
|-------|-----------|-------------|
| `HighCPUUsage` | CPU > 80% for 10m | Hohe CPU-Auslastung |
| `HighMemoryUsage` | Memory > 85% for 10m | Hohe Memory-Auslastung |
| `ContainerRestarting` | >3 Restarts/h | Container instabil |

## AlertManager Konfiguration

### Routing

```yaml
route:
  receiver: 'default-receiver'
  group_by: ['alertname', 'severity', 'service']
  routes:
    - match: { severity: critical }
      receiver: 'critical-receiver'
      group_wait: 10s
    - match: { alertname: CircuitBreakerTriggered }
      receiver: 'trading-halt-receiver'
      group_wait: 0s
```

### Inhibition Rules

- Service Down → alle anderen Alerts für den Service unterdrückt
- Database Down → Order Processing Alerts unterdrückt
- Critical → Warning Alerts für gleichen Service unterdrückt

## Konfigurationsdateien

```
infrastructure/monitoring/
├── prometheus.yml        # Prometheus scrape config
├── alerts.yml           # Alert rules
├── alertmanager.yml     # AlertManager routing
└── grafana/
    ├── dashboards/      # Dashboard JSON exports
    └── provisioning/    # Auto-provisioning configs
```

## Prometheus Metriken

### Standard Metriken

```promql
# Service Health
up{job="cdb_*"}

# Request Rate
rate(cdb_requests_total[5m])

# Latency P95
histogram_quantile(0.95, rate(cdb_latency_seconds_bucket[5m]))

# Error Rate
rate(cdb_errors_total[5m]) / rate(cdb_requests_total[5m])
```

### Trading-spezifische Metriken

```promql
# Orders per Second
rate(cdb_orders_processed_total[1m])

# Position Utilization
cdb_position_utilization_pct

# Daily Drawdown
cdb_daily_drawdown_pct

# Circuit Breaker Status
cdb_circuit_breaker_triggered
```

## Eskalation

| Severity | Response Time | Actions |
|----------|---------------|---------|
| Critical | < 5 min | Page On-Call, Auto Kill-Switch |
| High | < 30 min | Notification, Manual Review |
| Warning | < 4h | Ticket erstellen |

## Referenzen

- Issue #96: Monitoring: Grafana Dashboards & Alerting
- Epic #91: Paper Trading
- [Prometheus Docs](https://prometheus.io/docs/)
- [AlertManager Config](https://prometheus.io/docs/alerting/latest/configuration/)
