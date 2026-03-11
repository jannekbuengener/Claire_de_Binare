# E2E Shield & CI Operations (2025-12-25)

## TL;DR
E2E ist ein **Regression Shield**, kein Always-On. Lokal gated, CI gezielt.

## Lokal laufen lassen
```powershell
E2E_RUN=1 pytest tests/e2e/test_paper_trading_p0.py -v --no-cov
```

## CI Erwartung
- Workflow: `.github/workflows/e2e-tests.yml` (Name kann abweichen)
- Trigger: PRs, die `services/`, `tests/e2e/`, `infrastructure/` betreffen + manuell via dispatch
- Healthchecks: Redis/Postgres/Core Services
- Failure Diagnostics:
  - `docker compose ps`
  - Last logs (tail 300)
  - Upload artifacts (Logs), retention begrenzt

## Wenn E2E flakey wird
1) Prüfe, ob Tests **Input fixieren** (IDs / Stream range).
2) Timeouts runter/hoch? Diagnose zuerst, dann Tuning.
3) Nur deterministische Quellen: keine wall-clock Abhängigkeit.
