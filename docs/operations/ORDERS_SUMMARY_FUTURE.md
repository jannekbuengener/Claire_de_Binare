# Daily Orders Summary — Superseded Plan

**Status:** SUPERSEDED  
**Superseded on:** 2026-07-17  
**Current canon:** [`services/reports/README.md`](../../services/reports/README.md)

## Decision

The implementation described by this former future plan already exists.

Current repository reality:

- `services/reports/daily_orders_summary.py` implements the daily report worker.
- `services/reports/Dockerfile` and `services/reports/requirements.txt` exist.
- `cdb_reports` is integrated directly into [`infrastructure/compose/compose.red.yml`](../../infrastructure/compose/compose.red.yml).
- A separate `infrastructure/compose/reports.yml` is not part of the current runtime architecture.
- The service runs daily at 08:00 UTC, reads the previous 24 hours from Postgres, and sends an HTML email through secret-backed SMTP configuration.

This file is retained only as a historical pointer. It is not an implementation backlog, deployment guide, or operator runbook.

## Current references

- [Reports service documentation](../../services/reports/README.md)
- [Service index](../../services/README.md)
- [RED Compose definition](../../infrastructure/compose/compose.red.yml)
- [Architecture map](../../ARCHITECTURE_MAP.md)
- [Service catalog](../../knowledge/governance/SERVICE_CATALOG.md)

## Boundaries

- No separate reports Compose overlay is required.
- No on-demand API or configurable report schedule is currently supported.
- Runtime execution, database reads, SMTP tests, and email delivery require a separately approved operational scope.
- Secret values and recipient addresses must not be placed in documentation, logs, fixtures, or issue comments.
