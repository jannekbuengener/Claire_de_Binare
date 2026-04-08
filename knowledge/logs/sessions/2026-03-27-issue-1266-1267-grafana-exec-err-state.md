# Session Log — 2026-03-27 — Issues #1266/#1267 Closure

## Task
Bundled investigation and closure of #1266 (Orders-Rejected-Alert) and #1267 (High-Error-Rate-Alert),
both failing with DatasourceError due to Prometheus hostname resolution failure.

## Shared Root Cause

**Error observed:**
```
failed to execute query [A]: Post "http://cdb_prometheus:9090/api/v1/query_range":
dial tcp: lookup cdb_prometheus on 127.0.0.11:53: no such host
```

**Cause chain:**
1. During environment restart, Docker's embedded DNS (127.0.0.11:53) transiently removes
   `cdb_prometheus` while the container is stopped.
2. Grafana evaluates the alert rule during this window.
3. `execErrState: Error` causes an immediate alert notification — false-positive DatasourceError mail.

The datasource URL `http://cdb_prometheus:9090` was always structurally correct.
Both `cdb_grafana` and `cdb_prometheus` are on `cdb_network` (confirmed in compose.red.yml).
The problem was exclusively the error-handling policy on the alert rules.

## Fix (already landed before this session)

Commit: `216d0eb` (2026-03-26)

| File | Change |
|---|---|
| `infrastructure/monitoring/grafana/provisioning/alerting/orders_rejected.yml` | `execErrState: Error` → `execErrState: KeepLast` |
| `infrastructure/monitoring/grafana/provisioning/alerting/high_error_rate.yml` | `execErrState: Error` → `execErrState: KeepLast` |

Note: An earlier attempt (`KeepLastState` in PR #1273) was reverted — `KeepLastState` is not a valid
Grafana unified alerting enum. `KeepLast` is correct for Grafana 10.4+/11.x.

## Validation Performed

- `orders_rejected.yml` L53: `execErrState: KeepLast` ✓
- `high_error_rate.yml` L53: `execErrState: KeepLast` ✓
- `prometheus.yml` datasource: `url: http://cdb_prometheus:9090` ✓
- `compose.red.yml`: both services on `cdb_network` ✓
- `tests/unit/scripts/test_grafana_alerting_provisioning.py`: regression guards for both rules ✓

## Files Checked

- `infrastructure/monitoring/grafana/provisioning/alerting/orders_rejected.yml`
- `infrastructure/monitoring/grafana/provisioning/alerting/high_error_rate.yml`
- `infrastructure/monitoring/grafana/provisioning/datasources/prometheus.yml`
- `infrastructure/compose/compose.red.yml`
- `tests/unit/scripts/test_grafana_alerting_provisioning.py`
- `CURRENT_STATUS.md`

## Actions This Session

- Confirmed fix fully landed in `main` — no code changes required
- Updated `CURRENT_STATUS.md` L22 (session summary) and L94 (known blockers) to reflect closure
- Posted closing comments on #1266 and #1267
- Closed both issues on GitHub

## Status

**#1266:** CLOSED
**#1267:** CLOSED
