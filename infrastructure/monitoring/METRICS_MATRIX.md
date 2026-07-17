# Metrics Matrix

Repo-backed SSOT for Prometheus-scraped metrics in the Claire de Binare repository.

## Authority

This file is the authoritative inventory for active scrape jobs and repo-backed
metric names.

Primary evidence:

- [`prometheus.yml`](prometheus.yml) — scrape plan
- [`compose.blue.yml`](../compose/compose.blue.yml) and [`compose.red.yml`](../compose/compose.red.yml) — active runtime wiring
- [`base.yml`](../compose/base.yml) and [`dev.yml`](../compose/dev.yml) — compatibility/test wiring where still referenced
- service code and exporter configuration — metric producer evidence

[`KPI_REFERENCE.md`](KPI_REFERENCE.md) is only a front-door pointer. It does not
define additional metric names and must not be used as a parallel KPI canon.
Grafana dashboards are downstream consumers, not sources of truth.

## Active scrape jobs

| job_name | target | Producer evidence | Status |
|---|---|---|---|
| `prometheus` | `localhost:9090/metrics` | Prometheus self-scrape | active |
| `cdb_execution` | `cdb_execution:8003/metrics` | [`services/execution/service.py`](../../services/execution/service.py) | active |
| `cdb_signal` | `cdb_signal:8005/metrics` | [`services/signal/service.py`](../../services/signal/service.py) | active |
| `cdb_candles` | `cdb_candles:8007/metrics` | [`services/candles/service.py`](../../services/candles/service.py) | active |
| `cdb_db_writer` | `cdb_db_writer:8010/metrics` | [`services/db_writer/db_writer.py`](../../services/db_writer/db_writer.py) | active |
| `cdb_risk` | `cdb_risk:8002/metrics` | [`services/risk/service.py`](../../services/risk/service.py) | active |
| `cdb_ws` | `cdb_ws:8000/metrics` | [`services/ws/service.py`](../../services/ws/service.py) | active |
| `cdb_postgres` | `cdb_postgres_exporter:9187/metrics` | postgres-exporter wiring | active |
| `cdb_redis` | `cdb_redis_exporter:9121/metrics` | redis-exporter wiring | active |
| `cdb_cadvisor` | `cdb_cadvisor:8080/metrics` | cAdvisor wiring | active |

`cdb_paper_runner` is not part of the active scrape canon because its current
service surface exposes health/status endpoints rather than a repo-backed
Prometheus metrics endpoint. `cdb_node_exporter` is not part of the active
BLUE+RED runtime canon.

## Repo-backed custom metrics

### Risk

- `signals_received_total`
- `orders_approved_total`
- `orders_blocked_total`
- `orders_skipped_total`
- `circuit_breaker_active`
- `order_results_received_total`
- `orders_rejected_execution_total`
- `risk_pending_orders_total`
- `risk_total_exposure_value`
- `risk_reduce_only_approved_total`
- `risk_proactive_unwind_triggered_total`
- `risk_alerts_generated_total`
- `risk_kill_switch_active`

### Execution

- `execution_orders_received_total`
- `execution_orders_filled_total`
- `execution_orders_rejected_total`
- `execution_invalid_payloads_total`
- `execution_shadow_blocked_total`
- `execution_uptime_seconds`

### Signal

- `signals_generated_total`
- `signal_engine_status`
- `signal_processing_latency_ms`
- `signal_errors_total`

### DB Writer

- `db_writer_events_processed_total`
- `db_writer_events_failed_total`
- `db_writer_uptime_seconds`

### WebSocket

- `decoded_messages_total`
- `decode_errors_total`
- `ws_connected`
- `last_message_ts_ms`
- `redis_publish_total`
- `redis_publish_errors_total`

### Candles

- `candle_trades_processed_total`
- `candle_candles_emitted_total`

## Exporter-backed families

Exporter families are recorded by stable, repo-used examples rather than an
invented exhaustive list:

- Prometheus: `up`, `prometheus_*`
- Postgres exporter: `pg_up`, `pg_*`
- Redis exporter: `redis_up`, `redis_*`
- cAdvisor: `container_cpu_usage_seconds_total`, `container_memory_usage_bytes`,
  `container_memory_limit_bytes`, `container_restart_count`,
  `container_memory_oom_kill_total`

Exact exporter collector subsets remain exporter-defined unless explicitly
configured in this repository.

## Maintenance rule

A metric belongs here only when all of the following are present:

1. a repo-backed producer or exporter configuration,
2. an active or explicitly classified scrape target,
3. the exact emitted metric name or a clearly marked exporter family.

Do not copy historical KPI names from old documents into this matrix. New
metrics require code/config evidence first, then this inventory and downstream
dashboards may be updated.
