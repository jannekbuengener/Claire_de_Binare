# KPI Reference

Front-door pointer for monitoring canon.

Current SSOT for the actually scraped and repo-backed metric surface:
- `infrastructure/monitoring/METRICS_MATRIX.md`

Use this file only as a navigation entry point.

Scope split:
- scrape truth: `infrastructure/monitoring/prometheus.yml`
- metric inventory and drift status: `infrastructure/monitoring/METRICS_MATRIX.md`
- alert rules: `infrastructure/monitoring/alerts.yml`

Explicit non-scope for this file:
- no dashboard spec
- no operator KPI shortlist
- no duplicate per-metric inventory
