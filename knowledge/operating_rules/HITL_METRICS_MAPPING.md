# HITL Metrics Mapping

**Zweck**: Mapping von Prometheus Metrics zu HITL Dashboard Panels.

**Status**: ✅ Dokumentiert (Issue #244)
**Zuletzt aktualisiert**: 2025-12-27

---

## Übersicht

Dieses Dokument definiert, welche Prometheus Metrics für welche HITL Dashboard Panels verwendet werden und wie Services diese Metrics exportieren müssen.

---

## Safety & Control Metrics

### kill_switch_active

**Panel**: 🚨 KILL-SWITCH STATUS
**Type**: Gauge (0 = inactive, 1 = active)
**Source**: Risk Service (`services/risk/service.py`)
**Prometheus Query**: `kill_switch_active`

**Implementation**:
```python
from prometheus_client import Gauge

kill_switch_metric = Gauge('kill_switch_active', 'Kill-switch status (0=inactive, 1=active)')

# Update in main loop
from core.safety import get_kill_switch_state
kill_switch_metric.set(1 if get_kill_switch_state() else 0)
```

**Expected Values**:
- `0`: Kill-Switch inactive (trading allowed) → ✅ INACTIVE (green)
- `1`: Kill-Switch active (trading stopped) → 🚨 ACTIVE (red)

---

### trading_mode

**Panel**: ⚙️ TRADING MODE
**Type**: Gauge (0 = paper, 1 = staged, 2 = live)
**Source**: Risk Service
**Prometheus Query**: `trading_mode`

**Implementation**:
```python
from prometheus_client import Gauge
from core.config.trading_mode import get_trading_mode, TradingMode

trading_mode_metric = Gauge('trading_mode', 'Trading mode (0=paper, 1=staged, 2=live)')

# Update on startup and mode changes
mode = get_trading_mode()
if mode == TradingMode.PAPER:
    trading_mode_metric.set(0)
elif mode == TradingMode.STAGED:
    trading_mode_metric.set(1)
elif mode == TradingMode.LIVE:
    trading_mode_metric.set(2)
```

**Expected Values**:
- `0`: PAPER mode → 📄 PAPER (blue)
- `1`: STAGED mode → 🧪 STAGED (yellow)
- `2`: LIVE mode → 💰 LIVE (red)

---

### circuit_breaker_active

**Panel**: ⚡ CIRCUIT BREAKER
**Type**: Gauge (0 = safe, 1 = tripped)
**Source**: Risk Service
**Prometheus Query**: `circuit_breaker_active`

**Implementation**:
```python
from prometheus_client import Gauge

circuit_breaker_metric = Gauge('circuit_breaker_active', 'Circuit breaker status (0=safe, 1=tripped)')

# Update when circuit breaker trips
if daily_pnl_percent < MAX_DAILY_LOSS_PERCENT:
    circuit_breaker_metric.set(1)
    activate_kill_switch(KillSwitchReason.CIRCUIT_BREAKER, f"Daily loss {daily_pnl_percent}% exceeded limit")
else:
    circuit_breaker_metric.set(0)
```

**Expected Values**:
- `0`: Circuit breaker safe → ✅ SAFE (green)
- `1`: Circuit breaker tripped → ⚠️ TRIPPED (orange)

---

## Financial Metrics

### daily_pnl_percent

**Panel**: 📊 DAILY P&L (%), 📈 Daily P&L Trend
**Type**: Gauge (percentage)
**Source**: Risk Service
**Prometheus Query**: `daily_pnl_percent`

**Implementation**:
```python
from prometheus_client import Gauge

daily_pnl_metric = Gauge('daily_pnl_percent', 'Daily profit/loss percentage')

# Calculate daily P&L
current_value = portfolio_total_value_usdt.get()
start_of_day_value = get_start_of_day_value()  # From Redis or DB
pnl_percent = ((current_value - start_of_day_value) / start_of_day_value) * 100

daily_pnl_metric.set(pnl_percent)
```

**Expected Range**:
- `> 0%`: Profit (green)
- `-2% to 0%`: Small loss (yellow)
- `< -2%`: Significant loss (red)
- `< -5%`: Circuit breaker triggers

---

### portfolio_total_value_usdt

**Panel**: 💰 Portfolio Value (USDT)
**Type**: Gauge (USDT)
**Source**: Risk Service
**Prometheus Query**: `portfolio_total_value_usdt`

**Implementation**:
```python
from prometheus_client import Gauge

portfolio_value_metric = Gauge('portfolio_total_value_usdt', 'Total portfolio value in USDT')

# Update periodically (e.g., every 10s)
total_value = calculate_portfolio_value()  # Sum of all positions + cash
portfolio_value_metric.set(total_value)
```

**Expected Range**: Depends on initial capital (e.g., 1000 - 100000 USDT)

---

## Risk Metrics

### risk_limit_max_daily_loss_percent

**Panel**: 🔒 Active Risk Limits
**Type**: Gauge (percentage)
**Source**: Risk Service
**Prometheus Query**: `risk_limit_max_daily_loss_percent`

**Implementation**:
```python
from prometheus_client import Gauge

max_daily_loss_metric = Gauge('risk_limit_max_daily_loss_percent', 'Maximum allowed daily loss percentage')

# Set from config
max_daily_loss_metric.set(MAX_DAILY_LOSS_PERCENT)  # e.g., 5.0
```

**Expected Value**: Typically `5.0` (5% max daily loss)

---

### risk_limit_max_exposure_percent

**Panel**: 🔒 Active Risk Limits
**Type**: Gauge (percentage)
**Source**: Risk Service
**Prometheus Query**: `risk_limit_max_exposure_percent`

**Implementation**:
```python
from prometheus_client import Gauge

max_exposure_metric = Gauge('risk_limit_max_exposure_percent', 'Maximum allowed exposure as percentage of portfolio')

max_exposure_metric.set(MAX_EXPOSURE_PERCENT)  # e.g., 30.0
```

**Expected Value**: Typically `30.0` (30% max exposure)

---

### risk_limit_max_position_size_usdt

**Panel**: 🔒 Active Risk Limits
**Type**: Gauge (USDT)
**Source**: Risk Service
**Prometheus Query**: `risk_limit_max_position_size_usdt`

**Implementation**:
```python
from prometheus_client import Gauge

max_position_metric = Gauge('risk_limit_max_position_size_usdt', 'Maximum allowed position size in USDT')

max_position_metric.set(MAX_POSITION_SIZE_USDT)  # e.g., 1000.0
```

**Expected Value**: Depends on portfolio size (e.g., 100 - 10000 USDT)

---

## Intervention Metrics

### kill_switch_activations_total

**Panel**: 📜 Recent Manual Interventions
**Type**: Counter
**Source**: Risk Service
**Prometheus Query**: `increase(kill_switch_activations_total[24h])`

**Implementation**:
```python
from prometheus_client import Counter

kill_switch_activations = Counter('kill_switch_activations_total', 'Total kill-switch activations')

# Increment when activated
def activate_kill_switch_with_metrics(reason, message, operator):
    activate_kill_switch(reason, message, operator)
    kill_switch_activations.inc()
```

**Expected Value**: `0` (no activations) in normal operation

---

### kill_switch_deactivations_total

**Panel**: 📜 Recent Manual Interventions
**Type**: Counter
**Source**: Risk Service
**Prometheus Query**: `increase(kill_switch_deactivations_total[24h])`

**Implementation**:
```python
from prometheus_client import Counter

kill_switch_deactivations = Counter('kill_switch_deactivations_total', 'Total kill-switch deactivations')

# Increment when deactivated
def deactivate_kill_switch_with_metrics(operator, justification):
    ks = KillSwitch()
    result = ks.deactivate(operator, justification)
    if result:
        kill_switch_deactivations.inc()
```

**Expected Value**: Should match activations (every activation → deactivation)

---

### manual_order_cancellations_total

**Panel**: 📜 Recent Manual Interventions
**Type**: Counter
**Source**: Execution Service
**Prometheus Query**: `increase(manual_order_cancellations_total[24h])`

**Implementation**:
```python
from prometheus_client import Counter

manual_cancellations = Counter('manual_order_cancellations_total', 'Total manual order cancellations')

# Increment when order manually cancelled
def cancel_order_manual(order_id, operator):
    result = cancel_order(order_id)
    if result:
        manual_cancellations.inc()
```

**Expected Value**: `0` (no manual cancellations) in normal operation

---

## Order & Position Metrics

### orders_active

**Panel**: 🎯 Active Orders
**Type**: Gauge (count)
**Source**: Execution Service
**Prometheus Query**: `count(orders_active)`

**Implementation**:
```python
from prometheus_client import Gauge

orders_active_metric = Gauge('orders_active', 'Number of active orders', ['order_id'])

# Update when orders created/filled/cancelled
active_orders = get_active_orders()
for order in active_orders:
    orders_active_metric.labels(order_id=order['order_id']).set(1)

# Remove when order completed
orders_active_metric.labels(order_id=completed_order_id).set(0)
```

**Expected Range**:
- `0-10`: Normal (green)
- `10-50`: High activity (yellow)
- `> 50`: Potential stuck orders (red)

---

### position_value_usdt

**Panel**: 💸 Total Exposure (USDT)
**Type**: Gauge (USDT per position)
**Source**: Risk Service
**Prometheus Query**: `sum(position_value_usdt)`

**Implementation**:
```python
from prometheus_client import Gauge

position_value_metric = Gauge('position_value_usdt', 'Position value in USDT', ['symbol'])

# Update for each open position
for position in get_open_positions():
    value = position['quantity'] * position['current_price']
    position_value_metric.labels(symbol=position['symbol']).set(value)

# Remove when position closed
position_value_metric.labels(symbol=closed_symbol).set(0)
```

**Expected Range**: Depends on risk limits (should be < 30% of portfolio)

---

## System Health Metrics

### up

**Panel**: ⏱️ Service Uptime
**Type**: Gauge (0 = down, 1 = up)
**Source**: Prometheus (automatic scraping)
**Prometheus Query**: `min(up{job=~".*cdb.*"})`

**Implementation**: Automatic via Prometheus scraping targets

**prometheus.yml**:
```yaml
scrape_configs:
  - job_name: 'cdb_risk'
    static_configs:
      - targets: ['cdb_risk:8002']

  - job_name: 'cdb_execution'
    static_configs:
      - targets: ['cdb_execution:8003']
```

**Expected Value**: `1` (all services up)

---

## Metric Export Configuration

### Prometheus Client Setup

**services/risk/service.py**:
```python
from prometheus_client import start_http_server, Gauge, Counter

# Start metrics server
start_http_server(8002)  # Expose metrics on :8002/metrics

# Define all metrics
kill_switch_metric = Gauge('kill_switch_active', 'Kill-switch status')
trading_mode_metric = Gauge('trading_mode', 'Trading mode')
# ... etc
```

### Prometheus Scrape Configuration

**infrastructure/monitoring/prometheus.yml**:
```yaml
scrape_configs:
  - job_name: 'cdb_risk'
    scrape_interval: 10s
    static_configs:
      - targets: ['cdb_risk:8002']

  - job_name: 'cdb_execution'
    scrape_interval: 10s
    static_configs:
      - targets: ['cdb_execution:8003']
```

---

## Metric Testing

### Verify Metric Export

```powershell
# 1. Check if service exports metrics
curl http://localhost:8002/metrics | Select-String "kill_switch"

# Expected output:
# kill_switch_active 0.0

# 2. Check if Prometheus scrapes metrics
curl http://localhost:9090/api/v1/query?query=kill_switch_active

# Expected output:
# {"status":"success","data":{"resultType":"vector","result":[{"metric":{"__name__":"kill_switch_active"},"value":[1735315200,"0"]}]}}
```

### Verify Dashboard Queries

```powershell
# 1. Open Grafana dashboard
# 2. Edit panel
# 3. Click "Query inspector"
# 4. Verify query returns data
# 5. Check "Stats" tab for query performance
```

---

## Metric Retention

### Prometheus Configuration

**prometheus.yml**:
```yaml
global:
  scrape_interval: 10s
  evaluation_interval: 10s

storage:
  tsdb:
    retention.time: 30d  # Keep metrics for 30 days
    retention.size: 10GB # Or max 10GB
```

### Disk Space Requirements

- **10s scrape interval**: ~100 samples/hour per metric
- **100 metrics total**: ~10k samples/hour
- **30 days retention**: ~7.2M samples
- **Estimated size**: ~500MB - 1GB (compressed)

---

## Implementation Checklist

Services müssen folgende Metrics exportieren:

### Risk Service (Port 8002)
- [ ] `kill_switch_active`
- [ ] `trading_mode`
- [ ] `circuit_breaker_active`
- [ ] `daily_pnl_percent`
- [ ] `portfolio_total_value_usdt`
- [ ] `risk_limit_max_daily_loss_percent`
- [ ] `risk_limit_max_exposure_percent`
- [ ] `risk_limit_max_position_size_usdt`
- [ ] `kill_switch_activations_total`
- [ ] `kill_switch_deactivations_total`
- [ ] `position_value_usdt` (labeled by symbol)

### Execution Service (Port 8003)
- [ ] `orders_active` (labeled by order_id)
- [ ] `manual_order_cancellations_total`

### Prometheus
- [ ] Scrape configs für alle Services
- [ ] Retention Policy konfiguriert

### Grafana
- [ ] Dashboard provisioned
- [ ] Datasource configured
- [ ] Queries tested

---

## Referenzen

- **HITL Dashboard**: infrastructure/monitoring/grafana/dashboards/claire_hitl_control_v1.json
- **HITL Runbook**: docs/HITL_RUNBOOK.md
- **Prometheus Client Docs**: https://github.com/prometheus/client_python
- **Grafana Query Docs**: https://grafana.com/docs/grafana/latest/datasources/prometheus/
- **Issue**: #244 (HITL Monitoring Dashboard)

---

**Version**: 1.0
**Status**: ✅ Dokumentiert
