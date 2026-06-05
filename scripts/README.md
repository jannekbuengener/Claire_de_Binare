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
| `smoke_core_flow.py` | Core flow smoke |
| `validate_paper_market_data_provenance.py` | Paper market_data provenance |
| `smart_health_check.py` | Health aggregation |

## Related

| Pfad | Zweck |
|---|---|
| [`infrastructure/scripts/README.md`](../infrastructure/scripts/README.md) | Stack, backup, E2E |
| [`tools/README.md`](../tools/README.md) | `cdb.ps1`, MCP validate |

## Boundary

LR **NO-GO** — `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
