# CDB Phase 2 Pack — Playbooks + #255 Regression Shield
Stand: 2025-12-25

## Was ist drin?
### Playbooks (kannonisch)
- `knowledge/playbooks/*` (Golden Path, Security, DB Init/Migrations, Redis Debug, E2E Spec)

### #255 MVP Test
- `tests/e2e/test_paper_trading_regression_shield.py`
  - Publish `orders`
  - Subscribe `order_results`
  - Assert payload contract
  - Optional: stream persistence (`CDB_E2E_REQUIRE_STREAM=1`)

### Local runner
- `scripts/run_e2e_regression_shield.ps1`

## Einbau ins Repo
1) ZIP ins Repo-Root entpacken (Ordner `knowledge/`, `tests/`, `scripts/` entstehen/werden ergänzt)
2) `git status` prüfen
3) Commit + PR erstellen

## Lokaler Run (Beispiel)
```powershell
docker compose up -d
.\scriptsun_e2e_regression_shield.ps1 -TimeoutSeconds 10
```

## CI Hinweis
Für CI muss Redis + Execution erreichbar sein. Üblich:
- docker compose up -d
- pytest -m e2e ...
