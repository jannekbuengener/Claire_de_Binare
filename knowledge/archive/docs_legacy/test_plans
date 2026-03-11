# E2E Test Suite P0 Scenarios - Implementation Plan
## Issue #113

**Document Version:** 1.0
**Date:** 2025-12-27
**Test Engineer:** test-engineer agent
**Status:** READY FOR IMPLEMENTATION

---

## Executive Summary

This document provides a comprehensive implementation plan for 5 critical P0 end-to-end test scenarios for paper trading. The tests validate the complete flow from market data through signal generation, risk management, execution, and database persistence.

**Current State:** Existing E2E tests (test_paper_trading_p0.py) cover Redis pub/sub flow and deterministic replay. Missing comprehensive risk scenarios.

**Target:** Add 5 deterministic, isolated test cases that validate risk management and execution flows without external dependencies.

**Timeline:** 2-3 development sessions (~6-8 hours total)

---

## 1. CURRENT STATE ANALYSIS

### 1.1 Existing Test Infrastructure ✓

**File:** `tests/e2e/test_paper_trading_p0.py` (436 lines)

**Existing Test Coverage:**
1. ✓ `test_order_to_execution_flow` - Basic pub/sub validation
2. ✓ `test_order_results_schema` - Payload schema validation
3. ✓ `test_stream_persistence` - Redis stream persistence
4. ✓ `test_subscriber_count` - Service availability check
5. ✓ `test_replay_determinism` - Deterministic replay validation

**Test Infrastructure Available:**
- ✓ Redis client fixture (with fallback connection strategies)
- ✓ Unique order ID generator
- ✓ E2E marker and skip logic (`E2E_RUN=1` required)
- ✓ Event logging patterns
- ✓ Schema validation patterns
- ✓ Deterministic replay testing

**Database Fixtures:** `tests/fixtures/db_fixtures.py`
- ✓ `reset_db` - Truncate all tables
- ✓ `seed_db` - Load deterministic seed data
- ✓ `clean_db` - Reset + seed (most common)

**Domain Factories:** `tests/conftest.py`
- ✓ `signal_factory` - Create test Signal objects
- ✓ `order_factory` - Create test Order objects
- ✓ `order_result_factory` - Create test OrderResult objects
- ✓ `mock_redis` - Mock Redis client
- ✓ `mock_postgres` - Mock PostgreSQL connection

### 1.2 Production Components

**Paper Trading Engine:** `services/execution/paper_trading.py` (506 lines)
- Order placement and execution
- Position management (open/add/close)
- PnL tracking (realized/unrealized)
- Performance metrics (Sharpe ratio, drawdown, win rate)
- Market price simulation
- Order validation (balance, position checks)

**Risk Manager:** `services/risk/service.py`
- Position limit checks (MAX_POSITION_PCT)
- Exposure limit checks (MAX_TOTAL_EXPOSURE_PCT)
- Daily drawdown circuit breaker (MAX_DAILY_DRAWDOWN_PCT)
- Circuit breaker shutdown protocol
- Regime awareness and allocation management

**Circuit Breaker:** `services/risk/circuit_breakers.py`
- ERROR_RATE threshold
- DRAWDOWN threshold
- LOSS_LIMIT threshold
- Trigger tracking

**Risk Configuration:** `services/risk/config.py`
```python
max_position_pct: float = 0.10        # 10% per position
max_total_exposure_pct: float = 0.30  # 30% total exposure
max_daily_drawdown_pct: float = 0.05  # 5% daily loss limit
stop_loss_pct: float = 0.02           # 2% stop loss
```

### 1.3 Gaps Identified

**Missing Test Coverage:**
1. ❌ Happy path end-to-end flow (market_data → signal → risk → execution → trade)
2. ❌ Risk blocking scenarios (position limit, exposure limit)
3. ❌ Circuit breaker trigger and shutdown protocol
4. ❌ Daily drawdown stop testing
5. ❌ Database persistence verification (trades, positions, portfolio snapshots)

**Missing Test Utilities:**
1. ❌ Mock market data generator
2. ❌ Risk state setup helpers
3. ❌ Multi-service orchestration for E2E flow
4. ❌ Database assertion helpers
5. ❌ Time mocking for deterministic drawdown tests

---

## 2. TEST ARCHITECTURE DESIGN

### 2.1 Test Isolation Strategy

**Principle:** Each test must run independently without external service dependencies.

**Approach:**
- **Option A (Recommended):** Mock Redis/Postgres - Fast, deterministic, CI-friendly
- **Option B:** Real services in Docker - Realistic, but slower and requires `E2E_RUN=1`

**Decision:** Use **Option A** for P0-001 through P0-004 (unit-style E2E), **Option B** for P0-005 (integration-style E2E).

### 2.2 Fixture Design

```python
@pytest.fixture
def mock_redis_for_e2e():
    """Mock Redis with event tracking for E2E tests."""
    mock = MagicMock(spec=Redis)
    mock.events = []  # Track published events

    def track_publish(channel, message):
        mock.events.append({"channel": channel, "data": message})
        return 1

    mock.publish.side_effect = track_publish
    mock.ping.return_value = True
    return mock

@pytest.fixture
def mock_postgres_for_e2e():
    """Mock Postgres with query capture for E2E tests."""
    mock_conn = MagicMock(spec=psycopg2.extensions.connection)
    mock_cursor = MagicMock()
    mock_cursor.queries = []  # Track executed queries

    def track_execute(query, params=None):
        mock_cursor.queries.append((query, params))

    mock_cursor.execute.side_effect = track_execute
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    return mock_conn

@pytest.fixture
def paper_trading_engine_with_mocks(mock_redis_for_e2e, mock_postgres_for_e2e):
    """Paper trading engine with mocked dependencies."""
    from services.execution.paper_trading import PaperTradingEngine

    engine = PaperTradingEngine(initial_balance=100000.0)
    engine.redis_client = mock_redis_for_e2e
    engine.postgres_conn = mock_postgres_for_e2e
    return engine

@pytest.fixture
def risk_manager_with_mocks(mock_redis_for_e2e, mock_postgres_for_e2e):
    """Risk manager with mocked dependencies."""
    from services.risk.service import RiskManager

    manager = RiskManager()
    manager.redis_client = mock_redis_for_e2e
    manager.postgres_conn = mock_postgres_for_e2e
    return manager

@pytest.fixture
def market_data_generator():
    """Generate deterministic market data for testing."""
    def _generate(symbol="BTC/USDT", base_price=50000.0, volatility=0.01):
        import random
        random.seed(42)  # Deterministic

        return {
            "symbol": symbol,
            "price": base_price * (1 + random.uniform(-volatility, volatility)),
            "timestamp": int(time.time()),
            "volume": random.uniform(1.0, 10.0),
        }

    return _generate

@pytest.fixture
def freeze_time():
    """Mock time.time() for deterministic tests."""
    import time
    from unittest.mock import patch

    fixed_time = 1700000000  # Fixed timestamp
    with patch("time.time", return_value=fixed_time):
        yield fixed_time
```

### 2.3 Determinism Strategy

**Time Mocking:**
- Use `unittest.mock.patch` to freeze `time.time()` and `utcnow()`
- Ensures consistent timestamps across test runs

**Random Seed:**
- Set `random.seed(42)` for market data generation
- Ensures reproducible price movements

**Order ID Generation:**
- Override timestamp-based IDs with sequential IDs (`test-order-001`, `test-order-002`)

**Database State:**
- Use `clean_db` fixture to reset state before each test
- Seed with deterministic test data

---

## 3. TEST CASE SPECIFICATIONS

### TC-P0-001: Happy Path (Market Data → Signal → Execution → Trade)

**Objective:** Validate complete end-to-end flow without any risk blocks.

**Test Type:** Integration (mocked dependencies)
**Priority:** P0 (Critical)
**Estimated Runtime:** <5 seconds

**Setup Requirements:**
```python
- Initial balance: $100,000 USDT
- Market price: BTC/USDT @ $50,000
- Risk limits: 10% position, 30% total exposure, 5% daily drawdown
- No existing positions
- Circuit breaker: INACTIVE
```

**Test Steps:**
```python
def test_happy_path_market_data_to_trade(
    paper_trading_engine_with_mocks,
    risk_manager_with_mocks,
    market_data_generator,
    signal_factory,
    freeze_time
):
    # ARRANGE: Setup components
    engine = paper_trading_engine_with_mocks
    risk_mgr = risk_manager_with_mocks

    # ACT 1: Inject market data
    market_data = market_data_generator(symbol="BTC/USDT", base_price=50000.0)
    engine.update_market_price("BTC/USDT", market_data["price"])

    # ACT 2: Generate signal
    signal = signal_factory(
        symbol="BTC/USDT",
        signal_type="BUY",
        price=Decimal("50000.00"),
        confidence=0.85
    )

    # ACT 3: Risk check (should APPROVE)
    risk_decision = risk_mgr.check_signal(signal)

    # ACT 4: Place order
    if risk_decision["approved"]:
        order_id = engine.place_order(
            symbol="BTC/USDT",
            side="buy",
            quantity=0.1,  # $5000 = 5% of balance (within 10% limit)
            order_type=OrderType.MARKET
        )

    # ASSERT: Risk approval
    assert risk_decision["approved"] is True
    assert risk_decision["reason"] is None

    # ASSERT: Order created
    assert order_id is not None
    assert engine.get_order_status(order_id) == OrderStatus.FILLED

    # ASSERT: Position opened
    position = engine.get_position("BTC/USDT")
    assert position is not None
    assert position.quantity == 0.1
    assert position.average_price == pytest.approx(50000.0, rel=0.01)

    # ASSERT: Balance updated
    assert engine.get_balance() == pytest.approx(95000.0, rel=0.01)  # -$5000

    # ASSERT: Events published (via mock Redis)
    redis_mock = engine.redis_client
    published_events = [e for e in redis_mock.events if e["channel"] == "order_results"]
    assert len(published_events) == 1

    event_data = json.loads(published_events[0]["data"])
    assert event_data["type"] == "order_result"
    assert event_data["status"] == "FILLED"
    assert event_data["symbol"] == "BTC/USDT"
```

**Expected Outcome:**
- ✓ Signal approved by risk manager
- ✓ Order placed and filled immediately (market order)
- ✓ Position opened (0.1 BTC @ $50,000)
- ✓ Balance reduced by $5,000
- ✓ order_result published to Redis
- ✓ No alerts generated

**Assertions:**
1. `risk_decision["approved"] == True`
2. `order_status == OrderStatus.FILLED`
3. `position.quantity == 0.1`
4. `balance == 95000.0`
5. `len(order_result_events) == 1`
6. `event_data["type"] == "order_result"`

---

### TC-P0-002: Risk Blocking (Position Limit Exceeded)

**Objective:** Validate that orders are blocked when position size exceeds MAX_POSITION_PCT.

**Test Type:** Unit (isolated risk check)
**Priority:** P0 (Critical)
**Estimated Runtime:** <2 seconds

**Setup Requirements:**
```python
- Initial balance: $100,000 USDT
- Market price: ETH/USDT @ $3,000
- Risk limits: MAX_POSITION_PCT = 10% ($10,000 max per position)
- Attempt to buy: 4.0 ETH = $12,000 (12% > 10% limit)
```

**Test Steps:**
```python
def test_risk_blocking_position_limit(
    risk_manager_with_mocks,
    signal_factory,
    freeze_time
):
    # ARRANGE: Setup risk manager with config
    risk_mgr = risk_manager_with_mocks
    risk_mgr.config.max_position_pct = 0.10  # 10%
    risk_mgr.current_balance = 100000.0

    # ACT: Generate signal that exceeds position limit
    signal = signal_factory(
        symbol="ETH/USDT",
        signal_type="BUY",
        price=Decimal("3000.00"),
        confidence=0.75
    )

    # Calculate order size that violates limit
    # Max allowed: $100,000 * 0.10 = $10,000
    # Attempted: 4.0 ETH * $3000 = $12,000 (VIOLATION)
    signal.metadata = {"quantity": 4.0}

    # ACT: Risk check
    risk_decision = risk_mgr.check_signal(signal)

    # ASSERT: Order BLOCKED
    assert risk_decision["approved"] is False
    assert "position limit" in risk_decision["reason"].lower()

    # ASSERT: Alert generated
    redis_mock = risk_mgr.redis_client
    alert_events = [e for e in redis_mock.events if e["channel"] == "alerts"]
    assert len(alert_events) == 1

    alert_data = json.loads(alert_events[0]["data"])
    assert alert_data["type"] == "alert"
    assert alert_data["level"] == "WARNING"
    assert alert_data["code"] == "POSITION_LIMIT_EXCEEDED"

    # ASSERT: Risk state updated
    assert risk_mgr.risk_state.signals_blocked == 1
```

**Expected Outcome:**
- ✓ Signal REJECTED by risk manager
- ✓ Reason: "Position limit exceeded"
- ✓ Alert published (level: WARNING, code: POSITION_LIMIT_EXCEEDED)
- ✓ No order created
- ✓ Balance unchanged

**Assertions:**
1. `risk_decision["approved"] == False`
2. `"position limit" in reason.lower()`
3. `len(alert_events) == 1`
4. `alert_data["code"] == "POSITION_LIMIT_EXCEEDED"`
5. `risk_state.signals_blocked == 1`

---

### TC-P0-003: Daily Drawdown Stop (Circuit Breaker)

**Objective:** Validate that circuit breaker activates when daily loss exceeds MAX_DAILY_DRAWDOWN_PCT.

**Test Type:** Integration (stateful risk manager)
**Priority:** P0 (Critical)
**Estimated Runtime:** <5 seconds

**Setup Requirements:**
```python
- Initial balance: $100,000 USDT
- Starting equity: $100,000
- Current equity: $94,500 (after losing trades)
- Daily PnL: -$5,500 (-5.5%)
- MAX_DAILY_DRAWDOWN_PCT: 5% (-$5,000 max loss)
- Circuit breaker should TRIGGER at -5.5%
```

**Test Steps:**
```python
def test_circuit_breaker_daily_drawdown(
    risk_manager_with_mocks,
    paper_trading_engine_with_mocks,
    signal_factory,
    freeze_time
):
    # ARRANGE: Setup components
    risk_mgr = risk_manager_with_mocks
    engine = paper_trading_engine_with_mocks

    risk_mgr.config.max_daily_drawdown_pct = 0.05  # 5%
    risk_mgr.current_balance = 100000.0

    # ARRANGE: Simulate losing trades to hit drawdown limit
    engine.start_paper_trading()
    engine.current_balance = 100000.0

    # Losing trade 1: -$3000
    engine.update_market_price("BTC/USDT", 50000.0)
    engine.place_order("BTC/USDT", "buy", 0.1, OrderType.MARKET)
    engine.update_market_price("BTC/USDT", 47000.0)  # Price drops
    engine.place_order("BTC/USDT", "sell", 0.1, OrderType.MARKET)  # Sell at loss

    # Losing trade 2: -$2500
    engine.update_market_price("ETH/USDT", 3000.0)
    engine.place_order("ETH/USDT", "buy", 1.0, OrderType.MARKET)
    engine.update_market_price("ETH/USDT", 2500.0)  # Price drops
    engine.place_order("ETH/USDT", "sell", 1.0, OrderType.MARKET)  # Sell at loss

    # Update risk manager with PnL
    risk_mgr.risk_state.daily_pnl = -5500.0  # Total loss: -$5,500

    # ACT: Check drawdown limit
    ok, reason = risk_mgr.check_drawdown_limit()

    # ASSERT: Circuit breaker TRIGGERED
    assert ok is False
    assert "circuit breaker" in reason.lower() or "drawdown" in reason.lower()
    assert risk_mgr.risk_state.circuit_breaker_active is True

    # ACT: Try to place new signal (should be BLOCKED)
    signal = signal_factory(symbol="BNB/USDT", signal_type="BUY")
    risk_decision = risk_mgr.check_signal(signal)

    # ASSERT: All new signals BLOCKED
    assert risk_decision["approved"] is False
    assert "circuit breaker active" in risk_decision["reason"].lower()

    # ASSERT: Critical alert published
    redis_mock = risk_mgr.redis_client
    alert_events = [e for e in redis_mock.events if e["channel"] == "alerts"]
    critical_alerts = [
        json.loads(e["data"])
        for e in alert_events
        if json.loads(e["data"])["level"] == "CRITICAL"
    ]
    assert len(critical_alerts) >= 1
    assert critical_alerts[0]["code"] == "CIRCUIT_BREAKER_TRIGGERED"
```

**Expected Outcome:**
- ✓ Circuit breaker activated after -5.5% daily loss
- ✓ All new signals blocked
- ✓ Critical alert published
- ✓ Risk state: `circuit_breaker_active = True`
- ✓ Reason: "Circuit breaker active - daily drawdown limit exceeded"

**Assertions:**
1. `check_drawdown_limit() returns (False, reason)`
2. `risk_state.circuit_breaker_active == True`
3. `new_signal_decision["approved"] == False`
4. `len(critical_alerts) >= 1`
5. `alert["code"] == "CIRCUIT_BREAKER_TRIGGERED"`

---

### TC-P0-004: Circuit Breaker Trigger (Error Rate)

**Objective:** Validate circuit breaker activation based on error rate threshold.

**Test Type:** Unit (circuit breaker logic)
**Priority:** P0 (Critical)
**Estimated Runtime:** <2 seconds

**Setup Requirements:**
```python
- Circuit breaker config: ERROR_RATE threshold = 0.10 (10%)
- Total trades: 20
- Failed trades: 3 (15% error rate > 10% threshold)
- Circuit breaker should TRIGGER
```

**Test Steps:**
```python
def test_circuit_breaker_error_rate(freeze_time):
    # ARRANGE: Setup circuit breaker
    from services.risk.circuit_breakers import CircuitBreaker, CircuitBreakerType

    breaker = CircuitBreaker()
    breaker.breakers[CircuitBreakerType.ERROR_RATE] = {
        "threshold": 0.10,  # 10%
        "active": True
    }

    # ARRANGE: Metrics with high error rate
    metrics = {
        "total_trades": 20,
        "failed_trades": 3,
        "error_rate": 3 / 20,  # 0.15 = 15%
        "drawdown": 0.02,  # 2% (below threshold)
    }

    # ACT: Check breakers
    result = breaker.check_breakers(metrics)

    # ASSERT: Circuit breaker TRIGGERED
    assert result["triggered"] is True
    assert "error_rate" in result["reasons"]
    assert "error_rate" in breaker.triggered_breakers
```

**Expected Outcome:**
- ✓ Circuit breaker triggered by error_rate
- ✓ Result: `{"triggered": True, "reasons": ["error_rate"]}`
- ✓ Breaker state tracked

**Assertions:**
1. `result["triggered"] == True`
2. `"error_rate" in result["reasons"]`
3. `"error_rate" in breaker.triggered_breakers`

---

### TC-P0-005: Data Persistence Check (Database Writes)

**Objective:** Validate that trades, positions, and portfolio snapshots are persisted to PostgreSQL.

**Test Type:** Integration (real database)
**Priority:** P0 (Critical)
**Estimated Runtime:** <8 seconds

**Setup Requirements:**
```python
- PostgreSQL database running (via docker-compose)
- clean_db fixture applied
- Requires E2E_RUN=1
```

**Test Steps:**
```python
@pytest.mark.e2e
def test_database_persistence(
    clean_db,  # Reset + seed database
    redis_client,  # Real Redis (E2E)
    unique_order_id,
    freeze_time
):
    # ARRANGE: Setup database connection
    conn = clean_db

    # ACT 1: Publish order via Redis
    order_payload = {
        "type": "order",
        "order_id": unique_order_id,
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.1,
        "timestamp": freeze_time,
        "strategy_id": "test-strategy-001"
    }

    redis_client.publish("orders", json.dumps(order_payload))

    # Wait for execution service to process
    time.sleep(3)

    # ACT 2: Wait for order_result
    pubsub = redis_client.pubsub()
    pubsub.subscribe("order_results")

    order_result = None
    for _ in range(20):
        msg = pubsub.get_message(timeout=0.5)
        if msg and msg["type"] == "message":
            order_result = json.loads(msg["data"])
            break
        time.sleep(0.5)

    pubsub.close()
    assert order_result is not None, "No order_result received"

    # ASSERT 1: Trade persisted to database
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM trades WHERE order_id = %s",
            (unique_order_id,)
        )
        trade = cur.fetchone()

    assert trade is not None, f"Trade {unique_order_id} not found in database"
    assert trade["symbol"] == "BTC/USDT"
    assert trade["side"] == "BUY"
    assert float(trade["quantity"]) == pytest.approx(0.1, rel=0.01)
    assert trade["status"] == "FILLED"

    # ASSERT 2: Position persisted to database
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM positions WHERE symbol = %s",
            ("BTC/USDT",)
        )
        position = cur.fetchone()

    assert position is not None, "Position not found in database"
    assert float(position["quantity"]) == pytest.approx(0.1, rel=0.01)
    assert position["side"] == "LONG"

    # ASSERT 3: Portfolio snapshot exists
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * FROM portfolio_snapshots
            ORDER BY timestamp DESC
            LIMIT 1
            """
        )
        snapshot = cur.fetchone()

    assert snapshot is not None, "No portfolio snapshot found"
    assert snapshot["open_positions"] >= 1
    assert float(snapshot["total_equity"]) > 0
```

**Expected Outcome:**
- ✓ Trade record inserted (order_id, symbol, side, quantity, status=FILLED)
- ✓ Position record created/updated (symbol, quantity, side=LONG)
- ✓ Portfolio snapshot updated (open_positions, total_equity)
- ✓ Timestamps are consistent
- ✓ No database errors

**Assertions:**
1. `trade["order_id"] == unique_order_id`
2. `trade["status"] == "FILLED"`
3. `position["quantity"] == 0.1`
4. `position["side"] == "LONG"`
5. `snapshot["open_positions"] >= 1`

---

## 4. IMPLEMENTATION CHECKLIST

### Phase 1: Foundation (2 hours)

- [ ] **Create test fixtures file:** `tests/e2e/fixtures_p0.py`
  - [ ] `mock_redis_for_e2e` - Event-tracking mock
  - [ ] `mock_postgres_for_e2e` - Query-capturing mock
  - [ ] `paper_trading_engine_with_mocks` - Isolated engine
  - [ ] `risk_manager_with_mocks` - Isolated risk manager
  - [ ] `market_data_generator` - Deterministic price generator
  - [ ] `freeze_time` - Time mocking context manager

- [ ] **Create test utilities:** `tests/e2e/utils_p0.py`
  - [ ] `assert_order_filled(engine, order_id)` - Order assertion
  - [ ] `assert_position_opened(engine, symbol, qty)` - Position assertion
  - [ ] `assert_event_published(redis_mock, channel, type)` - Event assertion
  - [ ] `assert_alert_generated(redis_mock, level, code)` - Alert assertion
  - [ ] `simulate_losing_trades(engine, loss_amount)` - Drawdown helper

### Phase 2: Test Implementation (3 hours)

- [ ] **TC-P0-001:** Happy path test
  - [ ] Write test function skeleton
  - [ ] Implement ARRANGE phase (setup)
  - [ ] Implement ACT phase (execute flow)
  - [ ] Implement ASSERT phase (verify outcomes)
  - [ ] Add inline documentation
  - [ ] Verify test passes (deterministic)

- [ ] **TC-P0-002:** Position limit blocking
  - [ ] Write test function
  - [ ] Setup risk limit violation scenario
  - [ ] Verify rejection logic
  - [ ] Verify alert generation
  - [ ] Add edge case tests (boundary values)

- [ ] **TC-P0-003:** Daily drawdown circuit breaker
  - [ ] Write test function
  - [ ] Implement losing trade simulation
  - [ ] Verify circuit breaker trigger
  - [ ] Verify signal blocking after trigger
  - [ ] Verify critical alert

- [ ] **TC-P0-004:** Error rate circuit breaker
  - [ ] Write test function
  - [ ] Setup error rate metrics
  - [ ] Verify circuit breaker logic
  - [ ] Test threshold boundary

- [ ] **TC-P0-005:** Database persistence
  - [ ] Write E2E test (requires docker-compose)
  - [ ] Implement database assertions
  - [ ] Verify trade persistence
  - [ ] Verify position persistence
  - [ ] Verify portfolio snapshot

### Phase 3: Quality Assurance (1.5 hours)

- [ ] **Run all tests 10 times** - Verify determinism
  ```bash
  for i in {1..10}; do pytest tests/e2e/test_paper_trading_p0.py::test_happy_path -v; done
  ```

- [ ] **Check test runtime** - All tests <10s each
  ```bash
  pytest tests/e2e/test_paper_trading_p0.py -v --durations=0
  ```

- [ ] **Code review checklist**
  - [ ] All assertions have descriptive messages
  - [ ] No hardcoded timestamps (use freeze_time)
  - [ ] No external API calls
  - [ ] No sleep() calls (except for E2E with real services)
  - [ ] All fixtures properly scoped (function-level)
  - [ ] Test names follow convention (test_<scenario>_<expected_outcome>)

- [ ] **Documentation**
  - [ ] Add docstrings to all test functions
  - [ ] Update `tests/e2e/README.md` with new tests
  - [ ] Add troubleshooting section for common failures

### Phase 4: CI/CD Integration (0.5 hours)

- [ ] **Update pytest configuration**
  - [ ] Verify `pytest.ini` marker exists: `e2e: End-to-End Tests`
  - [ ] Ensure E2E tests skip by default (unless `E2E_RUN=1`)

- [ ] **GitHub Actions workflow**
  - [ ] Add optional E2E job (manual trigger)
  - [ ] Setup docker-compose for TC-P0-005
  - [ ] Add test result reporting

---

## 5. RISK ASSESSMENT

### 5.1 Flakiness Risks

| Risk | Probability | Mitigation |
|------|------------|-----------|
| **Non-deterministic timestamps** | HIGH | Use `freeze_time` fixture, patch `time.time()` and `utcnow()` |
| **Race conditions in pub/sub** | MEDIUM | Use mocks for TC-P0-001 to P0-004, real services only for P0-005 |
| **Database state leakage** | MEDIUM | Use `clean_db` fixture, ensure transaction rollback |
| **Network timeouts (E2E)** | LOW | TC-P0-005 only, increase timeout to 10s, add retries |
| **Order ID collisions** | LOW | Use `unique_order_id` fixture with timestamp + random suffix |
| **Random number variance** | LOW | Set `random.seed(42)` in market data generator |

### 5.2 Dependency Risks

| Dependency | Risk | Mitigation |
|-----------|------|-----------|
| **Redis** | Service unavailable in CI | Mock for P0-001 to P0-004 |
| **PostgreSQL** | Database schema changes | Use fixtures, version control SQL scripts |
| **Paper trading engine** | API changes | Pin test to interface contract, not implementation |
| **Risk manager** | Config changes | Override config in tests, don't rely on .env |

### 5.3 Maintenance Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Test becomes obsolete** | Test doesn't catch real bugs | Review tests quarterly, align with production changes |
| **Overcomplicated mocks** | Tests become brittle | Keep mocks simple, only mock external I/O |
| **Test data drift** | Seed data doesn't match production | Sync `01_seed_data.sql` with production schema |

---

## 6. IMPLEMENTATION GUIDELINES

### 6.1 Code Style

**Test Function Structure:**
```python
def test_<scenario>_<expected_outcome>(fixtures):
    """
    Test: <One-line description>

    Validates:
    - <Assertion 1>
    - <Assertion 2>

    Flow:
    1. <Step 1>
    2. <Step 2>
    3. <Step 3>
    """
    # ARRANGE: Setup test data and state

    # ACT: Execute the operation under test

    # ASSERT: Verify outcomes
    assert condition, "Descriptive failure message"
```

**Assertion Messages:**
```python
# ✓ GOOD - Descriptive
assert balance == 95000.0, f"Expected balance $95,000 after $5,000 purchase, got ${balance}"

# ✗ BAD - No context
assert balance == 95000.0
```

**Fixture Usage:**
```python
# ✓ GOOD - Scoped to function
@pytest.fixture(scope="function")
def clean_state():
    return {"balance": 100000.0}

# ✗ BAD - Module scope for mutable state
@pytest.fixture(scope="module")
def shared_state():
    return {"balance": 100000.0}  # Will leak between tests!
```

### 6.2 Debugging Failed Tests

**Step 1:** Check test isolation
```bash
# Run test alone
pytest tests/e2e/test_paper_trading_p0.py::test_happy_path -v

# Run test 5 times
pytest tests/e2e/test_paper_trading_p0.py::test_happy_path -v --count=5
```

**Step 2:** Enable debug logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Step 3:** Inspect mock calls
```python
print(f"Redis publish calls: {mock_redis.publish.call_args_list}")
print(f"Events published: {mock_redis.events}")
```

**Step 4:** Check database state (for TC-P0-005)
```sql
-- Check trades
SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10;

-- Check positions
SELECT * FROM positions;

-- Check snapshots
SELECT * FROM portfolio_snapshots ORDER BY timestamp DESC LIMIT 5;
```

---

## 7. SUCCESS CRITERIA

### 7.1 Acceptance Criteria

- [ ] All 5 test cases implemented
- [ ] All tests pass 100% of the time (10 consecutive runs)
- [ ] All tests complete in <10 seconds each
- [ ] Tests run successfully with `pytest -m e2e`
- [ ] No external service dependencies (except TC-P0-005)
- [ ] Code coverage >80% for paper_trading.py and risk/service.py
- [ ] Documentation complete (docstrings, README)

### 7.2 Performance Benchmarks

| Test Case | Max Runtime | Actual Runtime | Status |
|-----------|------------|----------------|--------|
| TC-P0-001 | 5s | TBD | ⏳ |
| TC-P0-002 | 2s | TBD | ⏳ |
| TC-P0-003 | 5s | TBD | ⏳ |
| TC-P0-004 | 2s | TBD | ⏳ |
| TC-P0-005 | 10s | TBD | ⏳ |
| **Total** | **24s** | **TBD** | **⏳** |

### 7.3 Quality Metrics

- **Determinism:** 100% (all tests pass 10/10 runs)
- **Code Coverage:** >80% for tested modules
- **Test Isolation:** 100% (tests can run in any order)
- **Documentation:** All functions have docstrings
- **CI Integration:** Tests run in GitHub Actions (E2E optional)

---

## 8. NEXT STEPS

1. **Review this plan** with development team (30 min)
2. **Allocate developer** for implementation (1 developer, 6-8 hours)
3. **Phase 1:** Create fixtures and utilities (2 hours)
4. **Phase 2:** Implement test cases (3 hours)
5. **Phase 3:** Quality assurance (1.5 hours)
6. **Phase 4:** CI/CD integration (0.5 hours)
7. **Close Issue #113** with test evidence

---

## 9. APPENDIX

### A. File Structure

```
tests/
├── e2e/
│   ├── __init__.py
│   ├── test_paper_trading_p0.py          # Existing E2E tests
│   ├── test_paper_trading_p0_risk.py     # NEW: Risk scenario tests (TC-P0-001 to TC-P0-005)
│   ├── fixtures_p0.py                     # NEW: E2E test fixtures
│   └── utils_p0.py                        # NEW: E2E test utilities
├── fixtures/
│   ├── db_fixtures.py                     # Existing DB fixtures
│   └── sql/
│       ├── 00_reset.sql
│       └── 01_seed_data.sql
└── conftest.py                            # Existing global fixtures
```

### B. Reference Commands

```bash
# Run all E2E tests (with real services)
E2E_RUN=1 pytest tests/e2e/test_paper_trading_p0.py -v

# Run specific test case
pytest tests/e2e/test_paper_trading_p0_risk.py::test_happy_path -v

# Run with coverage
pytest tests/e2e/test_paper_trading_p0_risk.py --cov=services.execution.paper_trading --cov=services.risk.service -v

# Check test runtime
pytest tests/e2e/test_paper_trading_p0_risk.py -v --durations=5

# Run tests 10 times (determinism check)
pytest tests/e2e/test_paper_trading_p0_risk.py --count=10 -v
```

### C. Mock Examples

**Redis Mock with Event Tracking:**
```python
mock_redis = MagicMock(spec=Redis)
mock_redis.events = []

def track_publish(channel, message):
    mock_redis.events.append({"channel": channel, "data": message})
    return 1

mock_redis.publish.side_effect = track_publish
```

**Time Freezing:**
```python
from unittest.mock import patch

fixed_time = 1700000000
with patch("time.time", return_value=fixed_time):
    # All time.time() calls return fixed_time
    pass
```

---

**END OF TEST PLAN**

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-27 | test-engineer | Initial test plan for Issue #113 |

---

**Approval:**
☐ Development Team Lead
☐ QA Lead
☐ Product Owner

**Status:** READY FOR IMPLEMENTATION
