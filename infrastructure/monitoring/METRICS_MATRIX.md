# Metrics Matrix

Repo-backed SSOT for Prometheus-scraped metrics in the working repo.

Scope of this file:
- inventory and canon only
- no dashboard spec
- no operator KPI shortlist
- no new telemetry

Collection authority:
- Prometheus scrape plan: `infrastructure/monitoring/prometheus.yml`
- Runtime/job evidence: `infrastructure/compose/compose.blue.yml`, `infrastructure/compose/compose.red.yml`, `infrastructure/compose/base.yml`, `infrastructure/compose/dev.yml`
- Metric producer evidence: service code and exporter wiring in the repo
- Grafana is downstream only and is not a source-of-truth surface for this file

## Ist-Zustand

- Prometheus currently defines 10 scrape jobs in `infrastructure/monitoring/prometheus.yml`.
- Repo-backed custom `/metrics` producers exist for `cdb_risk`, `cdb_execution`, `cdb_signal`, `cdb_db_writer`, `cdb_ws`, and `cdb_candles`.
- Repo-backed exporter jobs exist for `cdb_postgres`, `cdb_redis`, and `cdb_cadvisor`.
- `cdb_paper_runner` exists as a repo-backed runtime service, but it is intentionally not part of the active Prometheus scrape canon because the service only exposes `/health` and `/status`.
- `cdb_node_exporter` is intentionally not part of the active BLUE+RED runtime canon; `#1528` removed the historical `base.yml` / `dev.yml` wiring and the Prometheus scrape job instead of restoring the exporter.
- `infrastructure/monitoring/KPI_REFERENCE.md` had become broader than the repo-backed metric surface and is now reduced to a front-door pointer to this file.

## Scrape Jobs

| job_name | source_service / exporter | scrape_target / endpoint | Runtime evidence | status | Notes |
|---|---|---|---|---|---|
| `prometheus` | Prometheus self-scrape | `localhost:9090/metrics` | `infrastructure/monitoring/prometheus.yml` | `aktiv` | Self metrics plus Prometheus-generated `up` |
| `cdb_execution` | Execution Service | `cdb_execution:8003/metrics` | `services/execution/service.py` | `aktiv` | Manual text/plain metrics endpoint |
| `cdb_signal` | Signal Engine | `cdb_signal:8005/metrics` | `services/signal/service.py` | `aktiv` | Manual text/plain metrics endpoint |
| `cdb_candles` | Candle Aggregator | `cdb_candles:8007/metrics` | `services/candles/service.py` | `aktiv` | Marked `env=dev` in scrape config |
| `cdb_db_writer` | DB Writer | `cdb_db_writer:8010/metrics` | `services/db_writer/db_writer.py` | `aktiv` | `prometheus_client.start_http_server()` |
| `cdb_risk` | Risk Service | `cdb_risk:8002/metrics` | `services/risk/service.py` | `aktiv` | Manual text/plain metrics endpoint |
| `cdb_ws` | WebSocket service | `cdb_ws:8000/metrics` | `services/ws/service.py` | `aktiv` | `prometheus_client.generate_latest()` |
| `cdb_postgres` | postgres-exporter | `cdb_postgres_exporter:9187/metrics` | `infrastructure/compose/base.yml`, `infrastructure/compose/compose.red.yml` | `aktiv` | Standard exporter surface; exact collector set not customized in repo |
| `cdb_redis` | redis-exporter | `cdb_redis_exporter:9121/metrics` | `infrastructure/compose/base.yml`, `infrastructure/compose/compose.red.yml` | `aktiv` | Standard exporter surface; exact collector set not customized in repo |
| `cdb_cadvisor` | cAdvisor | `cdb_cadvisor:8080/metrics` | `infrastructure/compose/base.yml`, `infrastructure/compose/compose.red.yml` | `aktiv` | Container resource metrics |
Note:
- Prometheus generates `up{job,instance,...}` for every configured scrape target. To avoid duplicating one row per job, `up` is only called out below where it is the main known signal for a drifted or exporter-backed target.

## Metrics Matrix

### Repo-backed custom service metrics

| job_name | source_service / exporter | scrape_target / endpoint | metric_name | type | kurze Bedeutung | class | status | labels | spaetere dashboard_eignung |
|---|---|---|---|---|---|---|---|---|---|
| `cdb_risk` | Risk Service | `cdb_risk:8002/metrics` | `signals_received_total` | `counter` | Count of signals consumed from Redis PubSub | `business` | `aktiv` | none visible | `kandidat` |
| `cdb_risk` | Risk Service | `cdb_risk:8002/metrics` | `orders_approved_total` | `counter` | Orders approved by risk checks and forwarded | `business` | `aktiv` | none visible | `kandidat` |
| `cdb_risk` | Risk Service | `cdb_risk:8002/metrics` | `orders_blocked_total` | `counter` | Orders blocked by risk checks | `business` | `aktiv` | none visible | `kandidat` |
| `cdb_risk` | Risk Service | `cdb_risk:8002/metrics` | `orders_skipped_total` | `counter` | Orders skipped due to qty/parsing edge cases | `mixed/unclear` | `aktiv` | none visible | `unklar` |
| `cdb_risk` | Risk Service | `cdb_risk:8002/metrics` | `circuit_breaker_active` | `gauge` | Circuit breaker state, `1` when tripped | `business` | `aktiv` | none visible | `kandidat` |
| `cdb_risk` | Risk Service | `cdb_risk:8002/metrics` | `order_results_received_total` | `counter` | Count of execution result events processed by risk | `mixed/unclear` | `aktiv` | none visible | `unklar` |
| `cdb_risk` | Risk Service | `cdb_risk:8002/metrics` | `orders_rejected_execution_total` | `counter` | Orders rejected downstream by execution | `mixed/unclear` | `aktiv` | none visible | `kandidat` |
| `cdb_risk` | Risk Service | `cdb_risk:8002/metrics` | `risk_pending_orders_total` | `gauge` | Current number of pending order confirmations | `business` | `aktiv` | none visible | `kandidat` |
| `cdb_risk` | Risk Service | `cdb_risk:8002/metrics` | `risk_total_exposure_value` | `gauge` | Current total notional exposure | `business` | `aktiv` | none visible | `kandidat` |
| `cdb_risk` | Risk Service | `cdb_risk:8002/metrics` | `risk_reduce_only_approved_total` | `counter` | Reduce-only sells approved while over exposure limit | `business` | `aktiv` | none visible | `unklar` |
| `cdb_risk` | Risk Service | `cdb_risk:8002/metrics` | `risk_proactive_unwind_triggered_total` | `counter` | Auto-unwind triggers raised by risk logic | `business` | `aktiv` | none visible | `unklar` |
| `cdb_risk` | Risk Service | `cdb_risk:8002/metrics` | `risk_alerts_generated_total` | `counter` | Alerts published to Redis topic `alerts` | `mixed/unclear` | `aktiv` | none visible | `unklar` |
| `cdb_risk` | Risk Service | `cdb_risk:8002/metrics` | `risk_kill_switch_active` | `gauge` | Kill-switch state, `1` when trading is halted | `business` | `aktiv` | none visible | `kandidat` |
| `cdb_execution` | Execution Service | `cdb_execution:8003/metrics` | `execution_orders_received_total` | `counter` | Orders received by execution | `business` | `aktiv` | none visible | `kandidat` |
| `cdb_execution` | Execution Service | `cdb_execution:8003/metrics` | `execution_orders_filled_total` | `counter` | Orders filled successfully | `business` | `aktiv` | none visible | `kandidat` |
| `cdb_execution` | Execution Service | `cdb_execution:8003/metrics` | `execution_orders_rejected_total` | `counter` | Orders rejected by execution | `business` | `aktiv` | none visible | `kandidat` |
| `cdb_execution` | Execution Service | `cdb_execution:8003/metrics` | `execution_invalid_payloads_total` | `counter` | Invalid order payloads dropped fail-closed | `mixed/unclear` | `aktiv` | none visible | `unklar` |
| `cdb_execution` | Execution Service | `cdb_execution:8003/metrics` | `execution_shadow_blocked_total` | `counter` | Orders blocked by shadow-mode gate | `business` | `aktiv` | none visible | `kandidat` |
| `cdb_execution` | Execution Service | `cdb_execution:8003/metrics` | `execution_uptime_seconds` | `gauge` | Service uptime in seconds | `infra` | `aktiv` | none visible | `eher nicht` |
| `cdb_signal` | Signal Engine | `cdb_signal:8005/metrics` | `signals_generated_total` | `counter` | Signals emitted by the signal engine | `business` | `aktiv` | none visible | `kandidat` |
| `cdb_signal` | Signal Engine | `cdb_signal:8005/metrics` | `signal_engine_status` | `gauge` | Service status, `1` when running | `infra` | `aktiv` | none visible | `unklar` |
| `cdb_signal` | Signal Engine | `cdb_signal:8005/metrics` | `signal_processing_latency_ms` | `histogram` | Signal processing latency histogram | `mixed/unclear` | `aktiv` | `le` | `kandidat` |
| `cdb_signal` | Signal Engine | `cdb_signal:8005/metrics` | `signal_errors_total` | `counter` | Signal processing errors by error type | `mixed/unclear` | `aktiv` | `error_type` when present | `kandidat` |
| `cdb_db_writer` | DB Writer | `cdb_db_writer:8010/metrics` | `db_writer_events_processed_total` | `counter` | Persisted Redis events by subscribed channel | `mixed/unclear` | `aktiv` | `channel` | `kandidat` |
| `cdb_db_writer` | DB Writer | `cdb_db_writer:8010/metrics` | `db_writer_events_failed_total` | `counter` | Failed persistence attempts by subscribed channel | `mixed/unclear` | `aktiv` | `channel` | `kandidat` |
| `cdb_db_writer` | DB Writer | `cdb_db_writer:8010/metrics` | `db_writer_uptime_seconds` | `gauge` | Service uptime in seconds | `infra` | `aktiv` | none visible | `eher nicht` |
| `cdb_ws` | WebSocket service | `cdb_ws:8000/metrics` | `decoded_messages_total` | `counter` | Decoded WebSocket market-data messages | `mixed/unclear` | `aktiv` | none visible | `unklar` |
| `cdb_ws` | WebSocket service | `cdb_ws:8000/metrics` | `decode_errors_total` | `counter` | WebSocket message decode failures | `infra` | `aktiv` | none visible | `kandidat` |
| `cdb_ws` | WebSocket service | `cdb_ws:8000/metrics` | `ws_connected` | `gauge` | WebSocket connection state, `1` when connected | `infra` | `aktiv` | none visible | `kandidat` |
| `cdb_ws` | WebSocket service | `cdb_ws:8000/metrics` | `last_message_ts_ms` | `gauge` | Timestamp of last received message in ms | `infra` | `aktiv` | none visible | `kandidat` |
| `cdb_ws` | WebSocket service | `cdb_ws:8000/metrics` | `redis_publish_total` | `counter` | Market-data publishes to Redis | `mixed/unclear` | `aktiv` | none visible | `unklar` |
| `cdb_ws` | WebSocket service | `cdb_ws:8000/metrics` | `redis_publish_errors_total` | `counter` | Failed market-data publishes to Redis | `infra` | `aktiv` | none visible | `kandidat` |
| `cdb_candles` | Candle Aggregator | `cdb_candles:8007/metrics` | `candle_trades_processed_total` | `counter` | Raw trades aggregated into candles | `business` | `aktiv` | none visible | `unklar` |
| `cdb_candles` | Candle Aggregator | `cdb_candles:8007/metrics` | `candle_candles_emitted_total` | `counter` | Completed candles emitted by the aggregator | `business` | `aktiv` | none visible | `unklar` |

### Exporter-backed and scrape-level families

| job_name | source_service / exporter | scrape_target / endpoint | metric_name | type | kurze Bedeutung | class | status | labels | spaetere dashboard_eignung |
|---|---|---|---|---|---|---|---|---|---|
| `prometheus` | Prometheus self-scrape | `localhost:9090/metrics` | `up` | `gauge` | Scrape success for the Prometheus target itself | `infra` | `aktiv` | `job`, `instance`, static target labels | `kandidat` |
| `prometheus` | Prometheus self-scrape | `localhost:9090/metrics` | `prometheus_*` | `mixed/unclear` | Prometheus server internal metric families; exact subset not enumerated here | `infra` | `unklar` | exporter-defined | `unklar` |
| `cdb_postgres` | postgres-exporter | `cdb_postgres_exporter:9187/metrics` | `pg_up` | `gauge` | Postgres scrape/connectivity state used by alerts | `infra` | `aktiv` | exporter-defined | `kandidat` |
| `cdb_postgres` | postgres-exporter | `cdb_postgres_exporter:9187/metrics` | `pg_*` | `mixed/unclear` | Standard postgres-exporter families; exact collector subset not customized in repo | `infra` | `unklar` | exporter-defined | `unklar` |
| `cdb_redis` | redis-exporter | `cdb_redis_exporter:9121/metrics` | `redis_up` | `gauge` | Redis scrape/connectivity state used by alerts | `infra` | `aktiv` | exporter-defined | `kandidat` |
| `cdb_redis` | redis-exporter | `cdb_redis_exporter:9121/metrics` | `redis_*` | `mixed/unclear` | Standard redis-exporter families; exact subset not customized in repo | `infra` | `unklar` | exporter-defined | `unklar` |
| `cdb_cadvisor` | cAdvisor | `cdb_cadvisor:8080/metrics` | `container_cpu_usage_seconds_total` | `counter` | Per-container CPU usage | `infra` | `aktiv` | cAdvisor container labels | `kandidat` |
| `cdb_cadvisor` | cAdvisor | `cdb_cadvisor:8080/metrics` | `container_memory_usage_bytes` | `gauge` | Per-container memory usage | `infra` | `aktiv` | cAdvisor container labels | `kandidat` |
| `cdb_cadvisor` | cAdvisor | `cdb_cadvisor:8080/metrics` | `container_memory_limit_bytes` | `gauge` | Per-container memory limit | `infra` | `aktiv` | cAdvisor container labels | `kandidat` |
| `cdb_cadvisor` | cAdvisor | `cdb_cadvisor:8080/metrics` | `container_restart_count` | `gauge` | Container restart count used by soak/infra alerts | `infra` | `aktiv` | cAdvisor container labels | `kandidat` |
| `cdb_cadvisor` | cAdvisor | `cdb_cadvisor:8080/metrics` | `container_memory_oom_kill_total` | `counter` | OOM kill count per container | `infra` | `aktiv` | cAdvisor container labels | `kandidat` |
### Documented but not repo-backed as active exports

| job_name | source_service / exporter | scrape_target / endpoint | metric_name | type | kurze Bedeutung | class | status | labels | spaetere dashboard_eignung |
|---|---|---|---|---|---|---|---|---|---|
| `cdb_signal` | Signal Engine | `cdb_signal:8005/metrics` | `latency_samples`, `latency_sum_ms`, `latency_count` | `gauge/counter` | Older names still documented in `KPI_REFERENCE.md`, but current code exports `signal_processing_latency_ms_*` | `deprecated/drift` | `deprecated/drift` | none visible | `eher nicht` |
| `cdb_signal` | Signal Engine | `cdb_signal:8005/metrics` | `errors_total` | `counter` | Older doc name; current code exports `signal_errors_total` | `deprecated/drift` | `deprecated/drift` | none visible | `eher nicht` |
| `cdb_candles` | Candle Aggregator | `cdb_candles:8007/metrics` | `candles_trades_processed_total`, `candles_emitted_total` | `counter` | Older doc names; current code exports `candle_trades_processed_total` and `candle_candles_emitted_total` | `deprecated/drift` | `deprecated/drift` | none visible | `eher nicht` |
| `cdb_candles` | Candle Aggregator | `cdb_candles:8007/metrics` | `candles_market_state_updates_total`, `candles_market_state_skipped_total` | `counter` | Stats exist in code, but they are not exported on `/metrics` | `mixed/unclear` | `deprecated/drift` | none visible | `eher nicht` |

## Erkannte Canon- und Dokudrift

1. `infrastructure/monitoring/KPI_REFERENCE.md` documented Signal metrics with outdated names (`latency_samples`, `latency_sum_ms`, `latency_count`, `errors_total`) while the actual service exports `signal_processing_latency_ms_*` and `signal_errors_total`.
2. `infrastructure/monitoring/KPI_REFERENCE.md` documented Candle metrics with outdated names (`candles_*`) and extra market-state counters that are tracked in memory but not exposed on `/metrics`.
3. `#1536` resolved the stale `cdb_paper_runner` scrape by removing the `prometheus.yml` job instead of inventing a fake `/metrics` endpoint for a health/status-only runtime.
4. `#1528` resolved the `cdb_node_exporter` canon split by removing the stale scrape job and historical `base.yml` / `dev.yml` service wiring to match the active BLUE+RED runtime and `SERVICE_MAPPING.md`.
5. `infrastructure/monitoring/alerts.yml` is reconciled fail-closed against the current repo-backed metric surface:
   - retained repo-backed examples: `circuit_breaker_active`, `pg_up`, `redis_up`, `execution_orders_received_total`, `signals_received_total`, `orders_approved_total`, `orders_blocked_total`, `execution_orders_filled_total`, `container_*`
   - stale/non-repo-backed alert expressions were removed instead of being kept on guessed metric names: `cdb_daily_drawdown_pct`, `cdb_latency_seconds_bucket`, `cdb_errors_total`, `cdb_requests_total`, `cdb_order_processing_seconds`, `cdb_position_utilization_pct`, `cdb_orders_processed_total`, `cdb_signal_queue_length`
   - `SoakTest_HighMemoryUsage` now uses repo-backed cAdvisor metric `container_memory_limit_bytes` instead of the previously unverified `container_spec_memory_limit_bytes`
6. `#1537` resolved the front-door compose drift by marking `cdb_paper_runner` active in `infrastructure/compose/COMPOSE_LAYERS.md` to match the repo-backed dev overlay and runtime wiring.

## Schnitt fuer spaetere Grafana- und KPI-Auswahl

This matrix is intentionally split so the next session can filter without re-inventorying:
- `business`: trade-path and operator-control metrics that could become candidate KPIs later
- `infra`: health, scrape, runtime, and exporter metrics
- `mixed/unclear`: persistence or pipeline metrics that need operator-context decisions later

Recommended next step after this file:
- choose a minimal operator-facing subset from the rows already marked `kandidat`
- do not add new metrics before that selection is justified against this inventory
