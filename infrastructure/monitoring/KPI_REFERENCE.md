# KPI Reference — Claire de Binare Operational Metrics

Canonical reference for all Prometheus metrics scraped by the CDB monitoring stack.
Metrics are exposed via `/metrics` endpoints on each service and collected by Prometheus (15s scrape interval).

## Risk Manager (`:8002/metrics`)

| Metric | Type | Description |
|--------|------|-------------|
| `signals_received_total` | counter | Signals received from Signal Engine via Redis PubSub |
| `orders_approved_total` | counter | Orders that passed all risk checks and were forwarded to Execution |
| `orders_blocked_total` | counter | Orders rejected by risk checks (limits, circuit breaker, kill-switch) |
| `orders_skipped_total` | counter | Orders skipped due to qty=0 or parse errors |
| `circuit_breaker_active` | gauge | Circuit breaker state (1=tripped, 0=normal) |
| `order_results_received_total` | counter | Order result events processed (fills, rejects) |
| `orders_rejected_execution_total` | counter | Orders rejected by Execution Service |
| `risk_pending_orders_total` | gauge | Open orders awaiting execution confirmation |
| `risk_total_exposure_value` | gauge | Total notional exposure across all positions |
| `risk_reduce_only_approved_total` | counter | Reduce-only SELL orders approved while over exposure limit |
| `risk_proactive_unwind_triggered_total` | counter | Auto-unwind triggers when position exceeds limits |
| `risk_alerts_generated_total` | counter | Risk alerts published to Redis Pub/Sub channel `alerts` (not Prometheus alerting) |
| `risk_kill_switch_active` | gauge | Kill-switch state (1=active/trading halted, 0=inactive) |

## Signal Engine (`:8005/metrics`)

| Metric | Type | Description |
|--------|------|-------------|
| `latency_samples` | gauge | Number of latency observations |
| `latency_sum_ms` | gauge | Cumulative signal processing latency (ms) |
| `latency_count` | counter | Total signal processing invocations |
| `errors_total` | counter | Signal processing errors |

## Execution Service (`:8003/metrics`)

| Metric | Type | Description |
|--------|------|-------------|
| `execution_orders_received_total` | counter | Orders received from Risk Manager |
| `execution_orders_filled_total` | counter | Orders successfully filled on exchange |
| `execution_orders_rejected_total` | counter | Orders rejected (exchange error, invalid params) |
| `execution_shadow_blocked_total` | counter | Orders blocked by shadow mode (no real execution) |
| `execution_invalid_payloads_total` | counter | Malformed order payloads received |

## DB Writer (`:8010/metrics`)

| Metric | Type | Description |
|--------|------|-------------|
| `db_writer_events_processed_total` | counter | Events persisted to PostgreSQL (by channel) |
| `db_writer_events_failed_total` | counter | Events that failed to persist (by channel) |
| `db_writer_uptime_seconds` | gauge | Service uptime |

## WebSocket Screener (`:8000/metrics`)

| Metric | Type | Description |
|--------|------|-------------|
| `decoded_messages_total` | counter | Market data messages decoded from MEXC WebSocket |
| `decode_errors_total` | counter | Failed message decodes |
| `ws_connected` | gauge | WebSocket connection state (1=connected) |
| `last_message_ts_ms` | gauge | Timestamp of last received message (ms since epoch) |
| `redis_publish_total` | counter | Messages published to Redis |
| `redis_publish_errors_total` | counter | Failed Redis publishes |

## Candle Aggregator (`:8007/metrics`)

| Metric | Type | Description |
|--------|------|-------------|
| `candles_trades_processed_total` | counter | Raw trades aggregated into candles |
| `candles_emitted_total` | counter | Completed candles emitted |
| `candles_market_state_updates_total` | counter | Market state updates processed |
| `candles_market_state_skipped_total` | counter | Market state updates skipped (dedup) |

## Infrastructure Exporters

| Exporter | Port | Metrics |
|----------|------|---------|
| `cdb_postgres_exporter` | 9187 | PostgreSQL stats: connections, locks, replication lag, table sizes |
| `cdb_redis_exporter` | 9121 | Redis stats: memory, connected clients, keyspace, commands/s |
| `cdb_cadvisor` | 8080 | Container metrics: CPU, memory, network, disk I/O per container |
| `cdb_node_exporter` | 9100 | Host metrics: CPU, memory, disk, network, load average |

## Prometheus Alert Rules

26 Prometheus alerting rules in 8 groups defined in `infrastructure/monitoring/alerts.yml` (distinct from the Redis Pub/Sub `alerts` channel above):

| Group | Focus | Key Thresholds |
|-------|-------|----------------|
| `minimal_observability` | Service up/down | 4 core services monitored |
| `critical_alerts` | Circuit breaker, DB/Redis loss, drawdown | Drawdown >5% |
| `high_priority_alerts` | Latency, error rate, order processing | P95 >500ms, error >5% |
| `warning_alerts` | Resource usage, throughput | CPU >80%, memory >85% |
| `infrastructure_alerts` | Restarts, disk, targets | Disk <10%, restart loops |
| `soak_test_gates` | 72h soak validation | Zero-restart policy, OOM, stalls |

## Dashboards

15 Grafana dashboards provisioned from `infrastructure/monitoring/grafana/dashboards/`:

| Dashboard | Coverage |
|-----------|----------|
| `claire_minimal_observability_v1` | Entry-level 4-service health |
| `cdb_system_health_v1` | All services up/down, error rates, latency |
| `cdb_system_health_owner_v1` | Enhanced system health (owner view) |
| `claire_risk_manager_v1` | Risk decisions, exposure, circuit breaker |
| `claire_execution_v1` | Order lifecycle, shadow blocks |
| `claire_signal_engine_v1` | Signal generation, latency histogram |
| `claire_database_v1` | PostgreSQL connections, query timing |
| `claire_system_performance_v1` | CPU, memory, disk, container restarts |
| `claire_soak_test_v1` | 72h soak test monitoring |
| `claire_paper_trading_v1` | P&L, win rate, Sharpe ratio |
| `claire_hitl_control_v1` | Human-in-the-loop approval rates |
| `cdb_money_result_owner_v1` | Financial results |
| `risk_decision_accounting` | Risk decision audit trail |
| `signals_sprint1` | Signal generation tracking |
| `claire_dark_v1` | Dark-mode variant |

## Datasources

| Source | Type | Endpoint |
|--------|------|----------|
| Prometheus | Time series | `cdb_prometheus:9090` |
| PostgreSQL | SQL | `cdb_postgres:5432` |
| Loki | Logs | `cdb_loki:3100` |
