# Verification Snapshot — Issues #230 & #226 (2025-12-25)

## TL;DR
- #230: FAIL overall (Models OK, Integration/E2E missing)
- #226: FAIL (not started)

## Highlights
- `services/risk/models.py` +209 lines: PASS (methods inside class, defaults, deterministic)
- Missing:
  - Config for thresholds (drawdown/breaker)
  - Service integration (`services/risk/service.py`)
  - E2E cases TC-P0-003 & TC-P0-004
  - Runbook section for Risk Guards
