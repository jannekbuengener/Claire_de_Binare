# Test Overlay — Isolated E2E Test Execution

**Purpose:** Isolated Docker test stack for E2E validation without using development or production data.  
**Status:** Canonical Docker CI lab baseline for 431B (`base.yml + test.yml`).

## Quick start

From the repository root:

```bash
cd infrastructure/compose
docker compose -f base.yml -f test.yml up --build --abort-on-container-exit
```

The overlay starts isolated Redis and Postgres services, the Risk and Execution
test services, and `cdb_test_runner`. It does not authorize or start live trading.

## Current P0 test contract

The active P0 source is:

- [`tests/e2e/test_paper_trading_p0.py`](../../tests/e2e/test_paper_trading_p0.py)

The file currently defines **10 E2E tests**. The container command selects E2E
tests through the `e2e` marker:

```bash
pytest -m e2e tests/ -v --tb=short --no-cov -p no:cacheprovider --maxfail=3
```

Expected result for a healthy stack is a fully green selected E2E run. The old
five-test example and the expected Windows charmap failure are historical and no
longer describe the current UTF-8-safe test behavior.

Do not hard-code a repository-wide collected/deselected count here. That count
changes whenever unrelated E2E tests are added. The authoritative count for the
P0 slice is the set of test functions in the active P0 file.

## Overlay pattern

```text
base.yml          core Redis/Postgres/network services
  +
test.yml          isolated test overrides and test runner
  =
isolated E2E stack
```

`base.yml + dev.yml` remains a secondary local compatibility path and is not the
canonical 431B CI-lab path.

## Isolation boundaries

- Test containers use test-specific names and volumes.
- The test database is `claire_de_binare_test`.
- Test services use `TRADING_MODE=paper` and `DRY_RUN=1`.
- `E2E_RUN=1` enables the guarded E2E tests.
- Test data and volumes are disposable.
- No live exchange credentials or real-money path is required.

## Main services

| Service | Role |
|---|---|
| `cdb_redis_test` | isolated Redis transport |
| `cdb_postgres_test` | isolated test database |
| `cdb_risk_test` | Risk service for the test flow |
| `cdb_execution_test` | paper/non-live Execution service |
| `cdb_test_runner` | containerized pytest runner |

The concrete service definitions and environment values are authoritative in:

- [`base.yml`](base.yml)
- [`test.yml`](test.yml)
- [`Dockerfile.test`](Dockerfile.test)

## Useful commands

Rebuild only the test runner:

```bash
docker compose -f base.yml -f test.yml build --no-cache cdb_test_runner
```

Run the stack in the foreground:

```bash
docker compose -f base.yml -f test.yml up --abort-on-container-exit
```

Inspect the runner:

```bash
docker logs cdb_test_runner
```

Clean the isolated stack and volumes:

```bash
docker compose -f base.yml -f test.yml down -v
```

## Troubleshooting

When the runner exits before tests execute, check in this order:

1. Redis and Postgres health.
2. Test service hostnames from `test.yml`.
3. Secret mounts required by the test stack.
4. Python dependencies in `Dockerfile.test`.
5. Full `cdb_test_runner` logs.

Do not fix documentation drift by weakening tests or adding runtime behavior.
Update this file only from current Compose, Dockerfile, and P0-test evidence.

## Verification

Static verification:

```bash
python -m tools.validate_readme_links
```

Runtime verification is optional and must remain isolated:

```bash
docker compose -f infrastructure/compose/base.yml \
  -f infrastructure/compose/test.yml config
```

Rendering Compose configuration does not start containers.
