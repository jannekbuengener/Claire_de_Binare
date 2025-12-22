# E2E Tests (P0 Paper Trading)

These tests validate the P0 paper trading scenarios against a local Docker Compose stack.

## Preconditions
- Docker Compose stack running (base + dev):
  - `docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml up -d`
- Services reachable on localhost:
  - core: `http://localhost:8001/health`
  - risk: `http://localhost:8002/health`
  - execution: `http://localhost:8003/health`
- Redis and Postgres credentials available in the environment:
  - `REDIS_PASSWORD`
  - `POSTGRES_PASSWORD`
  - The E2E harness loads `.env` via python-dotenv when available.

## Run
```bash
E2E_RUN=1 E2E_DISABLE_CIRCUIT_BREAKER=1 pytest -m e2e tests/e2e/test_paper_trading_p0.py
```

## Circuit-breaker resets
- The harness now clears `stream.bot_shutdown` automatically before each run by calling `redis-cli DEL/UNLINK` to guarantee there are no stuck guard events.
- Optionally set `E2E_DISABLE_CIRCUIT_BREAKER=1` when running the stack to skip the risk manager’s bot-shutdown guard and let the paper-trading orders flow for testing. The default `0` keeps the safety logic active outside of E2E runs.

## Notes
- Tests skip with a clear reason when services or credentials are missing.
- TC-P0-003 is currently skipped because the drawdown guard is not wired into runtime state.
