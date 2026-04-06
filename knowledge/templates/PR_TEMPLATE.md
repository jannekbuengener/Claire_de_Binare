# PR Template

## What changed
- …

## Why
- …

## Verify
```powershell
python -m pytest -q <path> -vv
E2E_RUN=1 pytest tests/e2e/test_paper_trading_p0.py -v --no-cov
```

## Risks
- …

## Rollback
```powershell
git revert <SHA>
git push
docker compose -f infrastructure/compose/compose.red.yml down
docker compose -f infrastructure/compose/compose.blue.yml down
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```

## Links
- Closes #<issue>
