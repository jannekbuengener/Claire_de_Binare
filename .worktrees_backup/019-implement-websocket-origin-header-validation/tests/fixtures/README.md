# Test Fixtures - Deterministic Database State

**Purpose**: Provide repeatable, deterministic PostgreSQL state for E2E tests.

---

## Quick Start

### Use in E2E Tests

```python
import pytest

@pytest.mark.e2e
def test_order_flow(clean_db):
    """E2E test with clean, seeded database."""
    # DB is reset and contains seed data
    # - 1 portfolio snapshot (100k USDT)
    # - 3 signals (BTC/ETH/BNB)
    # - 3 orders (1 filled, 1 rejected, 1 pending)
    # - 1 trade (BTC buy)
    # - 1 position (BTC long)

    # Your test code here
    pass
```

### Available Fixtures

| Fixture | Description | Use Case |
|---------|-------------|----------|
| `reset_db` | Truncate all tables | When you only need clean state |
| `seed_db` | Reset + load seed data | Most common for E2E tests |
| `clean_db` | Alias for `seed_db` | Semantic clarity |

---

## Seed Data Overview

### Portfolio Snapshot (ID: 1)
```
Total Equity: 100,000 USDT
Available Balance: 100,000 USDT
Deployment Mode: test
```

### Signals (3)
1. **BTC** (ID: 1): BUY signal, 42000.00, confidence 0.95
2. **ETH** (ID: 2): SELL signal, 2200.00, confidence 0.65
3. **BNB** (ID: 3): BUY signal, 310.00, confidence 0.75

### Orders (3)
1. **BTC Order** (ID: 1): FILLED, 0.5 BTC @ 42010.00
2. **ETH Order** (ID: 2): REJECTED (insufficient balance)
3. **BNB Order** (ID: 3): PENDING, 10 BNB @ 310.00

### Trades (1)
1. **BTC Trade** (ID: 1): 0.5 BTC bought @ 42010.00, fees 21.00 USDT

### Positions (1)
1. **BTC Position** (ID: 1): Long 0.5 BTC @ 42010.00, current 42500.00, +245 USD unrealized PnL

---

## Manual Database Management

### Reset Database Only
```bash
cd tests/fixtures
python db_fixtures.py reset
```

### Reset + Seed
```bash
cd tests/fixtures
python db_fixtures.py seed
```

### From Python Code
```python
from tests.fixtures.db_fixtures import reset_database, seed_database

# Reset only
reset_database()

# Reset + Seed
seed_database()
```

---

## SQL Scripts

### 00_reset.sql
- Truncates all tables (signals, orders, trades, positions, portfolio_snapshots)
- Resets sequences (auto-increment IDs start from 1)
- Verifies all tables are empty
- Raises exception if reset fails

### 01_seed_data.sql
- Loads deterministic test data
- Sets explicit IDs for reproducibility
- Resets sequences to continue from last seed ID
- Verifies row counts match expectations

---

## Architecture

```
tests/fixtures/
├── __init__.py          # Package exports
├── README.md            # This file
├── db_fixtures.py       # Pytest fixtures + manual functions
└── sql/
    ├── 00_reset.sql     # Truncate all tables
    └── 01_seed_data.sql # Load seed data
```

---

## E2E Test Pattern

### Standard E2E Test
```python
@pytest.mark.e2e
def test_signal_to_order_flow(clean_db):
    """Test: Signal → Risk → Order creation."""
    # Arrange
    conn = clean_db
    cursor = conn.cursor()

    # Act: Trigger signal processing
    # (Your test logic here)

    # Assert: Verify expected DB state
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'filled'")
    filled_count = cursor.fetchone()[0]
    assert filled_count == 1  # Expect 1 filled order from seed data
```

### Custom Seed Data
```python
@pytest.mark.e2e
def test_custom_scenario(reset_db):
    """Test with custom data (no seed)."""
    conn = reset_db
    cursor = conn.cursor()

    # Insert custom test data
    cursor.execute("""
        INSERT INTO signals (symbol, signal_type, price, confidence, timestamp)
        VALUES ('ADAUSDT', 'buy', 0.50, 0.90, NOW())
    """)
    conn.commit()

    # Your test logic here
```

---

## Environment Variables

Required for DB connection:

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=claire_user
POSTGRES_PASSWORD=<secret>
POSTGRES_DB=claire_de_binare
```

**Note**: Fixtures automatically read from environment variables. No hardcoded credentials.

---

## Troubleshooting

### Connection Refused
```
psycopg2.OperationalError: could not connect to server
```
**Fix**: Ensure PostgreSQL container is running
```bash
docker ps | grep cdb_postgres
# If not running:
docker-compose up -d cdb_postgres
```

### Permission Denied
```
psycopg2.errors.InsufficientPrivilege: permission denied for table signals
```
**Fix**: Verify `claire_user` has GRANT ALL on tables (see schema.sql line 221)

### Seed Data Mismatch
```
Seed data counts unexpected
```
**Fix**: Check for manual table modifications. Re-run reset to clear state.

---

## Best Practices

1. **Always use `clean_db` for E2E tests** unless you need custom data
2. **Never modify seed data files during tests** - they should be immutable
3. **Use explicit IDs in seed data** for deterministic test assertions
4. **Reset between test runs** to avoid state pollution
5. **Document custom seed scenarios** if you create test-specific data

---

## Future Enhancements

- [ ] Add migration testing fixtures
- [ ] Add performance benchmark seed data (large datasets)
- [ ] Add corrupted data fixtures for error handling tests
- [ ] Add multi-account seed data for scaling tests

---

## References

- Issue #275: Deterministic PostgreSQL Fixtures
- schema.sql: Complete DB schema
- pytest.ini: Test markers and configuration
