# Test Overlay - Isolated E2E Test Execution

**Purpose**: Provides isolated test stack for running E2E tests without affecting development or production data.

---

## Quick Start

### Run E2E Tests in Isolated Stack

```bash
# From project root
cd infrastructure/compose

# Start test stack and run tests (auto-exit when done)
docker compose -f base.yml -f test.yml up --abort-on-container-exit

# Alternative: Build fresh and run
docker compose -f base.yml -f test.yml up --build --abort-on-container-exit
```

**Expected Output**:
```
cdb_test_runner  | ============================================
cdb_test_runner  | E2E Test Runner Starting...
cdb_test_runner  | ============================================
cdb_test_runner  | Waiting for services to be ready...
cdb_test_runner  | Running E2E tests...
cdb_test_runner  | ============================= test session starts ==============================
cdb_test_runner  | collected 5 items
cdb_test_runner  |
cdb_test_runner  | tests/e2e/test_paper_trading_p0.py::test_order_to_execution_flow PASSED
cdb_test_runner  | ...
cdb_test_runner  | ============================================
cdb_test_runner  | E2E Tests Complete!
cdb_test_runner  | ============================================
```

---

## Architecture

### Overlay Pattern

The test overlay extends the base infrastructure with test-specific overrides:

```
base.yml          # Core infrastructure (Redis, Postgres, network)
  +
test.yml          # Test overrides (isolated volumes, test runner)
  =
Isolated test stack
```

### Key Isolation Features

1. **Separate Containers**
   - `cdb_redis_test` (instead of `cdb_redis`)
   - `cdb_postgres_test` (instead of `cdb_postgres`)

2. **Isolated Volumes**
   - `redis_test_data` (not shared with dev/prod)
   - `postgres_test_data` (not shared with dev/prod)

3. **Test Database**
   - Database name: `claire_de_binare_test`
   - Schema loaded from `schema.sql` on init
   - Migrations applied automatically

4. **Test Runner Service**
   - Runs pytest with E2E marker
   - Auto-exits when tests complete
   - Logs visible in console output

---

## Services

### cdb_redis_test

**Override Changes**:
- Container name: `cdb_redis_test`
- Volume: `redis_test_data` (isolated)
- All other settings inherited from base.yml

### cdb_postgres_test

**Override Changes**:
- Container name: `cdb_postgres_test`
- Volume: `postgres_test_data` (isolated)
- Database name: `claire_de_binare_test`
- Schema: Loaded from `schema.sql` + migrations

### cdb_test_runner (NEW)

**Purpose**: Containerized pytest execution

**Build**:
- Dockerfile: `infrastructure/compose/Dockerfile.test`
- Base image: `python:3.12-slim`
- Dependencies: pytest, psycopg2-binary, all service requirements

**Environment**:
- `POSTGRES_HOST=cdb_postgres_test`
- `POSTGRES_DB=claire_de_binare_test`
- `REDIS_HOST=cdb_redis_test`
- `E2E_RUN=1` (enables E2E tests)
- `E2E_DISABLE_CIRCUIT_BREAKER=1` (prevents retries in tests)

**Volumes (Read-Only)**:
- `/app/core` → Source code
- `/app/services` → Service modules
- `/app/tests` → Test suite
- `/app/infrastructure` → Test fixtures

**Volumes (Writable)**:
- `/app/logs` → Test execution logs

**Command**:
```bash
pytest -m e2e tests/ -v --tb=short --no-cov -p no:cacheprovider --maxfail=3
```

---

## Usage Patterns

### 1. Quick E2E Test Run

```bash
# Start, test, auto-exit
docker compose -f base.yml -f test.yml up --abort-on-container-exit
```

### 2. Rebuild Before Testing

```bash
# Force rebuild test runner image
docker compose -f base.yml -f test.yml build --no-cache cdb_test_runner

# Run with fresh image
docker compose -f base.yml -f test.yml up --abort-on-container-exit
```

### 3. Keep Stack Running for Debugging

```bash
# Start test stack (don't auto-exit)
docker compose -f base.yml -f test.yml up -d

# View logs
docker logs cdb_test_runner -f

# Stop when done
docker compose -f base.yml -f test.yml down
```

### 4. Run Specific Tests

Edit `test.yml` line 86 to change pytest command:

```yaml
# Example: Run only one test
pytest tests/e2e/test_paper_trading_p0.py::test_order_to_execution_flow -v

# Example: Run with more verbose output
pytest -m e2e tests/ -vv --tb=long
```

---

## Validation

### Verify Stack Starts Correctly

```bash
# Start stack
docker compose -f base.yml -f test.yml up -d

# Check all services healthy
docker ps --filter "name=cdb_" --format "table {{.Names}}\t{{.Status}}"
```

**Expected**:
```
NAMES                 STATUS
cdb_test_runner       Up X seconds
cdb_postgres_test     Up X seconds (healthy)
cdb_redis_test        Up X seconds (healthy)
```

### Verify Test Runner Execution

```bash
# Check test runner logs
docker logs cdb_test_runner
```

**Expected**:
- "E2E Test Runner Starting..."
- "Running E2E tests..."
- pytest output with test results
- "E2E Tests Complete!"

---

## Troubleshooting

### 1. Network Not Found Error

**Symptom**:
```
ERROR: Network cdb_network declared as external, but could not be found
```

**Fix**:
```bash
# Create network manually
docker network create cdb_network

# Or start dev stack first (creates network)
docker compose -f base.yml -f dev.yml up -d
docker compose -f base.yml -f dev.yml down

# Then run test stack
docker compose -f base.yml -f test.yml up --abort-on-container-exit
```

### 2. Test Runner Exits Immediately

**Symptom**: `cdb_test_runner` exits with code 0 or 1 before running tests

**Check Logs**:
```bash
docker logs cdb_test_runner
```

**Common Issues**:
- **Database not ready**: Test runner starts before Postgres healthy
  - Fix: Check `depends_on` healthchecks in test.yml
- **Import errors**: Missing Python dependencies
  - Fix: Rebuild image with `--no-cache`
- **Connection refused**: Wrong service hostnames
  - Fix: Verify POSTGRES_HOST=cdb_postgres_test (not cdb_redis_test!)

### 3. Tests Fail with Connection Errors

**Symptom**: Tests fail with `psycopg2.OperationalError: could not connect`

**Debug**:
```bash
# Check Postgres is healthy
docker exec cdb_postgres_test pg_isready -U claire_user -d claire_de_binare_test

# Check network connectivity
docker exec cdb_test_runner ping -c 3 cdb_postgres_test

# Verify environment variables
docker exec cdb_test_runner env | grep POSTGRES
```

### 4. Volume Permission Issues

**Symptom**: `Permission denied` errors in logs directory

**Fix**:
```bash
# Ensure logs directory exists and is writable
mkdir -p logs
chmod 777 logs  # Or appropriate permissions for your setup
```

---

## Cleanup

### Remove Test Volumes

```bash
# Stop test stack
docker compose -f base.yml -f test.yml down

# Remove test volumes (deletes all test data!)
docker volume rm claire_de_binare_redis_test_data
docker volume rm claire_de_binare_postgres_test_data
```

### Remove Test Images

```bash
# Remove test runner image
docker rmi claire_de_binare-cdb_test_runner:latest
```

### Full Reset

```bash
# Stop and remove everything
docker compose -f base.yml -f test.yml down -v --rmi local

# Verify cleanup
docker ps -a | grep cdb_test
docker volume ls | grep test_data
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Create .env file
        run: |
          echo "POSTGRES_PASSWORD=${{ secrets.POSTGRES_PASSWORD }}" >> .env
          echo "REDIS_PASSWORD=${{ secrets.REDIS_PASSWORD }}" >> .env

      - name: Run E2E Tests
        run: |
          cd infrastructure/compose
          docker compose -f base.yml -f test.yml up --abort-on-container-exit

      - name: Upload test logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-logs
          path: logs/
```

---

## Best Practices

1. **Always use test overlay for automated testing**
   - Never run E2E tests against dev or prod stack
   - Test volumes are isolated and disposable

2. **Clean volumes between test runs for determinism**
   - `docker compose -f base.yml -f test.yml down -v`
   - Ensures fresh database state each run

3. **Use DB fixtures for test data**
   - See `tests/fixtures/README.md`
   - Fixtures provide deterministic seed data

4. **Check test runner exit code in CI**
   - Exit code 0 = all tests passed
   - Exit code 1 = tests failed
   - Non-zero exit = test execution error

5. **Review logs after failures**
   - `docker logs cdb_test_runner`
   - Test logs in `logs/` directory

---

## Related Documentation

- [Test Fixtures](../../tests/fixtures/README.md) - Database fixtures for E2E tests
- [Test Baseline](../../docs/testing/test_baseline.md) - Test inventory and categories
- [Markers](../../docs/testing/markers.md) - Pytest marker taxonomy

---

## Technical Details

### Environment Variables Required

See `.env` file for all required variables. Key test-specific vars:

| Variable | Value | Purpose |
|----------|-------|---------|
| `POSTGRES_HOST` | `cdb_postgres_test` | Test database host |
| `POSTGRES_DB` | `claire_de_binare_test` | Test database name |
| `REDIS_HOST` | `cdb_redis_test` | Test Redis host |
| `E2E_RUN` | `1` | Enable E2E test execution |
| `E2E_DISABLE_CIRCUIT_BREAKER` | `1` | Disable retries in tests |

### Network Configuration

- Network name: `cdb_network` (external, created by base.yml)
- Driver: bridge
- Isolation: All test containers on same network for connectivity

### Volume Mounts

**Source Code (Read-Only)**:
- Ensures tests run against actual codebase
- No test execution can modify source

**Logs (Writable)**:
- Allows test runner to write execution logs
- Persists even after container exits

---

**Status**: ✅ Production-ready (Issue #274)
**Last Updated**: 2025-12-27
