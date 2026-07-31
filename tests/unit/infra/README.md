# Infra / Compose / Stack / Secrets / Backup Contract Tests

Static and fixture-backed guards for infra ops contracts. Parent meta: **#3855**.

| Slice | Issues | Focus |
|-------|--------|--------|
| Compose BLUE/RED | #3856 | Layer classification, service canon |
| Stack lifecycle | #3857 | Operator gates, fail-closed secrets dir |
| Secrets SSOT | #3858 | `SECRETS_PATH`, canonical path, no secret echo |
| Backup / Restore / DR | #3859 | Manifest drift, destructive gates, artifacts |
| TLS / Network | #3860 | `tls.yml`, `network-prod.yml`, localhost bind, public exposure findings |
| Monitoring config | #3861 | Prometheus/Grafana/Loki/Promtail parse, datasource UID drift |
| Legacy quarantine | #3862 | `infrastructure/scripts/legacy/` banners and drift markers |
| Infra runbook drift | #3863 | Runbook vs repo-live path drift (no auto-fix) |
| Dockerfile pip pins | #4095 | pip advisory floor (CVE-2026-8643), one shared pin, no `.trivyignore` silencing |

## What these tests prove

- Compose layer classification (`canonical_runtime` vs `legacy_ci` / overlays)
- BLUE/RED service canon, network/volume naming, healthcheck posture
- Canonical secrets path `~/Documents/.secrets/.cdb` / `SECRETS_PATH` (not legacy `.cdb_local/.secrets`)
- Docker secrets + env fallback contracts in `core/secrets.py`
- `.env.runtime` export boundary (gitignored, optional — not required for BLUE+RED)
- Backup manifest reconciliation for Postgres / Redis / SurrealDB artifacts
- Restore destructive paths gated (`-Force`, `Read-Host`, explicit `yes`)
- `restore_all.ps1 -ListAvailable` list semantics documented in source
- Scripts do not echo secret payloads
- TLS overlay cert mount paths and `network-prod.yml` internal network posture
- Canonical runtime port bindings stay on `127.0.0.1`; public exposure is an explicit finding
- Monitoring provisioning YAML/JSON parseability and Grafana alert operator contract
- Legacy scripts under `infrastructure/scripts/legacy/` carry `LEGACY` banners
- Infra runbooks reference repo paths that exist (drift surfaced, not auto-corrected)
- Productive service images pin pip at or above every known pip advisory floor, on one shared version
- `services/execution` pins both its build venv pip and its global runtime pip (both are image paths)
- New Dockerfile surfaces must be classified productive vs. non-productive before shipping pip
- pip advisories are fixed rather than silenced via `.trivyignore`

## What these tests do **not** prove

- No real secrets read, rotated, or written
- No `docker compose up/down` — not a runtime or stack-start proof
- No backup or restore execution, no DB writes, no volume deletion
- No container health at execution time
- No operator authorization to mutate production stacks
- No certificate generation, Docker network creation, or live Grafana/Prometheus queries
- No legacy script reactivation or automatic runbook repair
- No image build, no registry access, no Trivy execution — the pip pin guard is static text parsing

Run targeted checks:

```bash
pytest -q tests/unit/infra -m contract
pytest -q tests/unit/infra/test_tls_network_contract.py
pytest -q tests/unit/infra/test_monitoring_config_contract.py
pytest -q tests/unit/infra/test_legacy_script_quarantine_contract.py
pytest -q tests/unit/infra/test_infra_runbook_drift_contract.py
pytest -q tests/unit/infra/test_dockerfile_pip_pin_contract.py
pytest -q tests/unit/scripts -k "backup_manifest or grafana_alerting"
```
