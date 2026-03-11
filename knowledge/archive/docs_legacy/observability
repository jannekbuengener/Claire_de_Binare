# Grafana Dashboards (Issue #296)

Übersicht aller verfügbaren Grafana Dashboards für Claire de Binare.

## Dashboard-Übersicht

| Dashboard | Datei | Beschreibung |
|-----------|-------|--------------|
| Paper Trading | claire_paper_trading_v1.json | Hauptdashboard für Trading-Übersicht |
| Execution | claire_execution_v1.json | Order-Ausführung, Latenz, Fill-Rate |
| Risk Manager | claire_risk_manager_v1.json | Drawdown, Exposure, Circuit Breaker |
| Signal Engine | claire_signal_engine_v1.json | Signal-Generierung, Confidence |
| System Performance | claire_system_performance_v1.json | CPU, Memory, Disk |
| Database | claire_database_v1.json | PostgreSQL Metriken |
| HITL Control | claire_hitl_control_v1.json | Human-in-the-Loop Controls |
| Dark Theme | claire_dark_v1.json | Dunkles Theme Dashboard |

## Zugriff

```
URL: http://localhost:3001
User: admin
Password: (aus .secrets/GRAFANA_PASSWORD)
```

## Dashboard-Details

### Paper Trading Dashboard

**Panels:**
- Risk Approval Rate (%)
- Signal Generation Rate
- Order Status Distribution
- Portfolio Equity Timeline
- Active Positions
- Daily P&L

**Metriken:**
```promql
# Approval Rate
(orders_approved_total / (orders_approved_total + orders_blocked_total)) * 100

# Signal Rate
rate(signals_generated_total[5m])

# Portfolio Equity
portfolio_equity_usdt
```

### Risk Manager Dashboard

**Panels:**
- Current Drawdown (%)
- Portfolio Exposure (%)
- Circuit Breaker Status
- Risk Rejections
- Position Sizes

**Alerts:**
- Drawdown > 10%: Warning
- Drawdown > 15%: Critical
- Circuit Breaker Triggered: Alert

### Execution Dashboard

**Panels:**
- Order Latency (p50, p95, p99)
- Fill Rate (%)
- Slippage Distribution
- Orders by Status
- MEXC API Status

## Provisioning

Dashboards werden automatisch provisioniert beim Stack-Start:

```yaml
# infrastructure/monitoring/grafana/provisioning/dashboards/dashboards.yml
apiVersion: 1
providers:
  - name: 'Claire Dashboards'
    folder: 'Claire de Binare'
    type: file
    options:
      path: /var/lib/grafana/dashboards
```

## Time Range Presets

| Preset | Verwendung |
|--------|-----------|
| Last 1h | Debugging, Live-Monitoring |
| Last 6h | Session-Review |
| Last 24h | Daily Overview |
| Last 7d | Weekly Performance |
| Last 30d | Monthly Review |

## Auto-Refresh

- Default: 30s
- Empfohlen für Live-Trading: 10s
- Empfohlen für Review: Off

## Alerting

### Konfigurierte Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| High Drawdown | > 15% | Critical |
| Circuit Breaker Active | triggered == 1 | Warning |
| API Connection Lost | up == 0 | Critical |
| High Latency | p99 > 1000ms | Warning |

### Notification Channels

- Alertmanager → Slack (konfigurierbar)
- Email (optional)

## Fehlerbehebung

### "No Data" in Panels

1. Prometheus läuft?
   ```bash
   docker logs cdb_prometheus
   ```

2. Metriken verfügbar?
   ```bash
   curl http://localhost:9090/api/v1/query?query=up
   ```

3. Service exportiert Metriken?
   ```bash
   curl http://cdb_risk:8000/metrics
   ```

### Dashboard lädt nicht

1. Grafana Logs prüfen:
   ```bash
   docker logs cdb_grafana
   ```

2. Provisioning-Pfad prüfen

3. JSON-Syntax validieren

## Custom Dashboard erstellen

1. In Grafana UI: Create → Dashboard
2. Panels hinzufügen
3. Save → Export as JSON
4. JSON in `infrastructure/monitoring/grafana/dashboards/` speichern
5. Grafana neustarten: `docker restart cdb_grafana`
