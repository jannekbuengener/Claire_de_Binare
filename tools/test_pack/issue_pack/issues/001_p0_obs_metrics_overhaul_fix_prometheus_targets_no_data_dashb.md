## ISSUE 1 — [P0][OBS] Metrics Overhaul: fix Prometheus targets + “No Data” dashboards + main panel restore
Labels: prio:p0, type:obs, scope:metrics
Scope:
- Prometheus scrape targets
- Grafana datasource
- Dashboard queries/variables
Description:
- Panels showing “No Data” and the broken main panel must be fixed. This is a prerequisite for chaos assertions and kill-switch verification.
Acceptance Criteria:
- Prometheus targets: all core services `UP=1` (stable, no flapping)
- Main dashboard loads without errors
- 0 broken panels; “No Data” either fixed or explicitly marked as “expected empty” with explanation
- Golden Signals section exists: throughput, error rate, latency, backlog/queue, orders/fills, risk blocks, kill-switch state
- Add a 5-step “No Data” troubleshooting checklist to docs
Links/Refs:
- Add links to the dashboards/panels in the issue once identified

---
