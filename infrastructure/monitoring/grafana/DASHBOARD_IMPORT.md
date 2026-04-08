# Grafana Dashboard Import

## Active Dashboard Canon

Grafana runs at **http://localhost:3000**.
- Username: `admin`
- Password: per secret init (see `SECRETS_PATH` / `bootstrap_local.sh`); not stored in `.env`

The active repo-backed dashboard canon is a single file:
- `dashboards/cdb_operator_kpis_v1.json`

This dashboard is intentionally narrow and tied to issue `#203`.
- Focus: the minimal operator KPI slice only
- Current datasource for all three KPIs: PostgreSQL table `trades`
- Repo-backed outcome field: `trades.realized_pnl`
- `Positive trades %` remains a derived query, not a raw stored metric

## KPI Contract In This Dashboard

- `Trades made`
  - query shape: `COUNT(*) FILTER (WHERE realized_pnl IS NOT NULL) FROM trades WHERE $__timeFilter(timestamp)`
  - meaning: trade rows that carry a realized outcome over the selected Grafana time range
- `Positive trades`
  - query shape: `COUNT(*) FILTER (WHERE realized_pnl > 0) FROM trades WHERE $__timeFilter(timestamp)`
  - meaning: positive realized outcomes over the selected Grafana time range
- `Positive trades %`
  - query shape: `100 * positive_trades / trades_made`
  - meaning: derived ratio over the same realized-outcome denominator

## Provisioning

Dashboards are file-provisioned from `/var/lib/grafana/dashboards` via:
- `infrastructure/monitoring/grafana/provisioning/dashboards/claire.yml`

Because this folder now contains a single active dashboard JSON, Grafana should provision exactly one Claire dashboard for this slice.

## Runtime Preconditions

- Use the canonical BLUE+RED runtime via `compose.blue.yml` + `compose.red.yml`
- The PostgreSQL datasource `postgres` must be provisioned and healthy
- `db_writer` must be persisting trade events into the `trades` table

## Troubleshooting

If the dashboard shows `0` or `No data`:
1. Check the Grafana time range first.
2. Check the PostgreSQL datasource health.
3. Run a direct SQL sanity check against `trades`.
4. Verify that `db_writer` is persisting trade events from the active runtime path.

If the dashboard import or provisioning fails:
1. Validate the JSON syntax.
2. Confirm Grafana can read `/var/lib/grafana/dashboards`.
3. Confirm the datasource UID is `postgres`.
