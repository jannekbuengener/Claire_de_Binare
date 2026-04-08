# Codex Batch 01 Ideas (2025-12-31)

Scope:
- Workflow focus: monitoring, CI noise, performance tests
- Workflow issues (last 10): #162, #170, #169, #155, #151, #145, #356, #355, #354, #352
- Candidate implementation (if gate + branch ok): #352, #355

Ideas:
- Monitoring: align Prometheus scrape targets with actual service ports in `infrastructure/monitoring/prometheus.yml`.
- Grafana: verify provisioning mounts and datasource names in `infrastructure/monitoring/grafana/provisioning/`.
- Alerting: add/verify alert rules for Redis/Postgres and service health endpoints in `infrastructure/monitoring/alerts.yml`.
- Readiness: add healthchecks for `cdb_risk` and `cdb_execution` in `infrastructure/compose/dev.yml`.
- Performance tests: keep `tests/performance` stable; mark tests and isolate in CI job `.github/workflows/performance-monitor.yml`.
- CI back-to-green: audit failing workflows and align required checks list (per #355).
- Branch hygiene: create/confirm long-lived branches for #162/#170/#169/#155/#151 before implementation.

Selected for implementation (if Delivery Gate + branch ok):
- #355 (branch: 355-p0roter_faden007-cicd-back-to-green-actions-+-guards)
- #354 (branch: 354-p0roter_faden006-deterministic-e2e-test-path-local-+-ci)

Issue #355 (CI back to green) ideas:
- Fix perf workflow: install `requirements-dev.txt` or add `pytest` to ensure `python -m pytest` works.
- Gate scheduled automations (Gemini triage, Copilot housekeeping) when required secrets/vars are missing.
- Reduce noise: run label/bootstrap and emoji workflows only on `workflow_dispatch` or PR label events.
- Document required checks list and mark non-critical workflows as informational.

Issue #354 (Deterministic E2E) ideas:
- Add `tests/e2e/README.md` with a single local command + CI command.
- Add `infrastructure/scripts/run_e2e.ps1` to start stack + run E2E with `E2E_RUN=1`.
- Split smoke test into a minimal deterministic test file for CI and keep full P0 suite for local.
