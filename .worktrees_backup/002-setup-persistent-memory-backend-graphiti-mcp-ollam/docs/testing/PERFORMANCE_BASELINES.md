# Performance Baselines

## Übersicht

Dieses Dokument definiert die Performance-Baselines für das CDB Trading System gemäß Issue #93.

## Latency Targets

| Pfad | Target | Maximum | Kritikalität |
|------|--------|---------|--------------|
| Market Data → Signal | <100ms | <500ms | HIGH |
| Signal → Risk Approval | <50ms | <200ms | CRITICAL |
| Order → Execution | <100ms | <500ms | CRITICAL |
| End-to-End | <300ms | <1000ms | HIGH |

### Erklärung

- **Market Data → Signal**: Zeit von Marktdaten-Empfang bis Signal-Generierung
- **Signal → Risk Approval**: Zeit für Risk-Checks (Position Limits, Drawdown, Circuit Breaker)
- **Order → Execution**: Zeit von Order-Submission bis Exchange-Confirmation
- **End-to-End**: Gesamte Pipeline vom Marktdaten-Event bis zur Order-Ausführung

## Throughput Targets

| Metrik | Target | Minimum | Einheit |
|--------|--------|---------|---------|
| Market Events | 100 | 50 | events/sec |
| Signals | 50 | 20 | signals/sec |
| Orders | 20 | 10 | orders/sec |

## Test-Ausführung

### Voraussetzungen
```bash
# Performance-Tests sind standardmäßig deaktiviert
# Aktivierung via Environment Variable:
export PERF_BASELINE_RUN=1
```

### Ausführung
```bash
# Alle Performance-Tests
PERF_BASELINE_RUN=1 pytest tests/performance/ -v -s

# Nur Latency-Tests
PERF_BASELINE_RUN=1 pytest tests/performance/test_baseline_measurements.py::TestLatencyBaselines -v -s

# Nur Throughput-Tests
PERF_BASELINE_RUN=1 pytest tests/performance/test_baseline_measurements.py::TestThroughputBaselines -v -s
```

### Output-Beispiel
```
📊 Market→Signal Latency: {'min_ms': 0.001, 'max_ms': 0.05, 'mean_ms': 0.002, 'median_ms': 0.002, 'p95_ms': 0.003, 'p99_ms': 0.004}
✅ Target met: 0.002ms < 100ms

📊 Orders/sec: 1250000.5
✅ Throughput exceeds minimum: 1250000.5/s > 10/s
```

## Metriken-Interpretation

### Latency Percentiles

| Percentile | Bedeutung |
|------------|-----------|
| P50 (Median) | Typische Latency |
| P95 | 95% der Requests sind schneller |
| P99 | Worst-case (außer Outliers) |

### Throughput

- **Target**: Optimale Performance für normale Last
- **Minimum**: Untergrenze für akzeptablen Betrieb

## Monitoring in Grafana

### Prometheus Metriken
```python
# Definiert in services/*/metrics.py
latency_histogram = Histogram(
    "cdb_latency_seconds",
    "Request latency",
    ["service", "operation"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0]
)

throughput_counter = Counter(
    "cdb_operations_total",
    "Total operations",
    ["service", "operation"]
)
```

### Dashboard Queries
```promql
# P95 Latency
histogram_quantile(0.95, rate(cdb_latency_seconds_bucket[5m]))

# Throughput
rate(cdb_operations_total[1m])
```

## Eskalations-Schwellen

| Metrik | Warning | Critical |
|--------|---------|----------|
| E2E Latency P95 | >500ms | >1000ms |
| Order Latency P99 | >300ms | >500ms |
| Throughput | <50% Target | <Min |

## Baseline-Verlauf

| Datum | E2E P95 | Orders/sec | Status |
|-------|---------|------------|--------|
| 2025-12-28 | TBD | TBD | Initial |

## Referenzen

- Issue #93: Performance Baseline Measurements
- Epic #91: Paper Trading
- `tests/performance/test_baseline_measurements.py`
