# Canonical Golden State (2025-12-25)

```powershell
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
docker compose -f infrastructure/compose/compose.blue.yml ps
docker compose -f infrastructure/compose/compose.red.yml ps
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "\dt"
E2E_RUN=1 pytest tests/e2e/test_paper_trading_p0.py -v --no-cov
python -m tools.replay.replay --count 50 --out artifacts/replay.jsonl --verify-hash
```
