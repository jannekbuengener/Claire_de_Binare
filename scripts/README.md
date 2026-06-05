# Repo Scripts (`scripts/`)

Automation, Guards und Evidence-Helfer auf Repo-Root-Ebene. Für Stack/Backup/Secrets siehe `infrastructure/scripts/` und `tools/`.

## Governance / LR guards

| Script | Zweck |
|---|---|
| `lr003_contract_drift_guard.py` | Contract drift |
| `lr004_completion_guard.py` | LR completion guard |
| `dual_write_evidence_gate.py` | Dual-write evidence |
| `validate_write_zones.sh` | Write-zone validation |
| `pre_close_sweep.sh` | Pre-close untracked sweep |

## Smoke / validation

| Script | Zweck |
|---|---|
| `smoke_core_flow.py` | Core flow smoke (allocation → signal path) |
| `validate_paper_market_data_provenance.py` | Paper market_data provenance |
| `smart_health_check.py` | Health aggregation |
| `smart_startup.py` | Startup helper |

## Ops / reporting

| Script | Zweck |
|---|---|
| `lr_reporter.py` | LR reporting helper |
| `lr020_tier2_evidence_capture.py` | Tier-2 evidence |
| `run_72h_test.py` | Long-run test driver |
| `generate_test_report.py` | Test reports |
| `check_core_duplicates.py` | Duplicate detection |

## GitHub / project (PowerShell)

| Script | Zweck |
|---|---|
| `setup_testnet.ps1` | Testnet setup |
| `manage_secrets.ps1` | Secrets compat (prefer `infrastructure/scripts/manage_secrets.ps1`) |
| `bulk-issue-labeling.ps1` | Issue labeling |
| `milestone-assignment.ps1` | Milestones |

## Related (canonical paths)

| Pfad | Zweck |
|---|---|
| [`infrastructure/scripts/README.md`](../infrastructure/scripts/README.md) | `setup_blue_red.ps1`, `smoke_test.ps1`, backup/DR |
| [`tools/README.md`](../tools/README.md) | `cdb.ps1`, MCP validate, secrets rotator |
| [`.github/scripts/`](../.github/scripts/) | Workflow-backed Python |

## Boundary

Scripts hier ersetzen keine Live-Readiness-Freigabe. LR **NO-GO** — `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
