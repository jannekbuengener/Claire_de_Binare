# Grafana Dashboard Import

## Active Dashboard Canon

Grafana runs at **http://localhost:3000**.
- Username: `admin`
- Password: per secret init (see `SECRETS_PATH` / `bootstrap_local.sh`); not stored in `.env`

The active repo-backed dashboard canon is now a single file:
- `dashboards/cdb_operator_kpis_v1.json`

This dashboard is intentionally narrow and tied to issue `#203`.
- Focus: the minimal operator KPI slice only
- Canonical live number today: `Trades made`
- Current datasource for that KPI: PostgreSQL table `trades`
- `Positive trades` and `Positive trades %` are intentionally not rendered as numeric KPIs yet because the active runtime path does not persist per-trade outcome semantics in `trades`

## KPI Contract In This Dashboard

- `Trades made`
  - query shape: `COUNT(*) FROM trades WHERE $__timeFilter(timestamp)`
  - meaning: executed trades persisted by the active runtime path over the selected Grafana time range
- `Positive trades`
  - status: blocked
  - reason: no repo-backed per-trade positive or negative outcome field in `trades`
- `Positive trades %`
  - status: blocked
  - reason: should remain a derived query once the numerator is repo-backed

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
