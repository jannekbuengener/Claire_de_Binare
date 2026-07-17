# CDB Reports Service

`cdb_reports` is the RED-stack reporting worker for the daily orders summary. It reads the last 24 hours of order and trade data from Postgres and sends one HTML email per day.

## Runtime role

- **Stack:** RED
- **Container:** `cdb_reports`
- **Entry point:** `daily_orders_summary.py`
- **Schedule:** daily at 08:00 UTC
- **Restart policy:** `unless-stopped`
- **Healthcheck:** verifies that the `daily_orders_summary.py` process is running
- **Network:** external `cdb_network`, shared with BLUE

The service has no HTTP API and no operator-facing on-demand trigger.

## Inputs

The worker queries Postgres for the previous 24 hours:

- `orders`: order counts by status, total notional, and top rejection reasons
- `trades`: total trades, positive trades, positive-trade rate, and fees

The preferred database connection is read from the file configured by `POSTGRES_DSN_FILE`. If that value is unavailable, the code constructs a DSN from the configured Postgres user, host, database, and the mounted Postgres password.

## Output

The service sends an HTML email containing:

- total, filled, rejected, cancelled, and pending orders
- fill rate
- top five rejection reasons
- trade count and positive-trade rate
- total notional and fees

Report recipients and SMTP credentials are secret-backed. They must not be copied into documentation, logs, fixtures, or issue comments.

## Configuration

Compose supplies the current runtime configuration:

| Setting | Current contract |
|---|---|
| `TZ` | `UTC` |
| `POSTGRES_HOST` | `cdb_postgres` |
| `POSTGRES_DB` | `claire_de_binare` |
| `POSTGRES_USER` | `${POSTGRES_USER:-claire_user}` |
| `POSTGRES_DSN_FILE` | `/run/secrets/postgres_password_dsn` |

Mounted secrets:

- `postgres_password_dsn`
- `postgres_password`
- `smtp_user`
- `smtp_password`
- `smtp_from`
- `alert_email_to`

The schedule is currently fixed in code. There is no supported `REPORT_SCHEDULE` setting.

## Failure behavior

- Missing or unreadable database credentials: the current run is skipped.
- Database connection or query failure: the current run is skipped and logged.
- Missing SMTP credentials or send failure: the email is not sent and the failure is logged without printing recipient addresses or credential values.
- Unexpected loop failure: the worker waits five minutes before retrying.
- Container/process failure: Compose restarts the service according to `unless-stopped`.

## Image and dependencies

- Image base: pinned `python:3.14-slim-bookworm`
- Runtime dependency: `psycopg2-binary==2.9.12`
- Healthcheck dependency: `procps` for `pgrep`
- Runtime user: non-root user `reporter`

## Static verification

This documentation can be checked without starting the runtime:

```bash
python -m tools.validate_readme_links
python -m tools.validate_root_layout
docker compose -f infrastructure/compose/compose.red.yml config
```

The Compose command is configuration rendering only. It does not start containers.

## Canonical references

- [RED Compose definition](../../infrastructure/compose/compose.red.yml)
- [Service index](../README.md)
- [Architecture map](../../ARCHITECTURE_MAP.md)
- [Service catalog](../../knowledge/governance/SERVICE_CATALOG.md)
- [Superseded implementation plan](../../docs/operations/ORDERS_SUMMARY_FUTURE.md)
