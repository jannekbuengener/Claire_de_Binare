# Milestone 7 (M7): Production-Ready Paper Trading System

**Status:** Planning
**Target:** Complete production-ready paper trading infrastructure with full observability and operational tooling
**Dependencies:** M6 (E2E Test Infrastructure) ✅ COMPLETE

---

## Cluster Overview

| Cluster | Focus | Dependencies | Priority |
|---------|-------|-------------|----------|
| [C1: Data/Feed](#c1-datafeed) | Market data ingestion & validation | None | MUST |
| [C2: Signal](#c2-signal) | Signal generation & strategy execution | C1 | MUST |
| [C3: Risk](#c3-risk) | Position sizing & risk management | C1, C2 | MUST |
| [C4: Execution](#c4-execution) | Order routing & fill simulation | C1, C3 | MUST |
| [C5: PSM](#c5-psm-position--state-management) | Position tracking & state consistency | C4 | MUST |
| [C6: Observability](#c6-observability) | Metrics, logging, alerting | All clusters | SHOULD |
| [C7: Reporting](#c7-reporting) | Performance analytics & dashboards | C5, C6 | SHOULD |
| [C8: Ops](#c8-ops) | Deployment, runbooks, backup/restore | All clusters | MUST |

---

## C1: Data/Feed

**Goal:** Reliable market data ingestion with validation and caching

### Subtasks

#### C1-01: Market Data Service Implementation
- **Description:** Implement dedicated market data service (WebSocket + REST fallback)
- **Acceptance Criteria:**
  - WebSocket connection to MEXC testnet
  - Automatic reconnection on disconnect
  - REST API fallback when WebSocket unavailable
  - 99.9% uptime during 14-day test
- **Dependencies:** None
- **Estimated Effort:** 2-3 sessions

#### C1-02: Data Validation & Sanitization
- **Description:** Validate incoming market data (price sanity checks, timestamp validation)
- **Acceptance Criteria:**
  - Reject prices outside 3σ from moving average
  - Validate timestamp freshness (<5s latency)
  - Log and alert on validation failures
  - Circuit breaker on sustained bad data (>10 failures/min)
- **Dependencies:** C1-01
- **Estimated Effort:** 1 session

#### C1-03: Redis Market Data Cache
- **Description:** Implement Redis cache for latest market prices (OHLCV, orderbook)
- **Acceptance Criteria:**
  - Latest price cached with TTL=10s
  - Pub/Sub channel for real-time price updates
  - Cache hit rate >95% during normal operation
  - Graceful degradation when cache unavailable
- **Dependencies:** C1-01
- **Estimated Effort:** 1-2 sessions

#### C1-04: Historical Data Backfill
- **Description:** PostgreSQL storage for historical OHLCV data
- **Acceptance Criteria:**
  - Schema: `ohlcv_history` table (symbol, interval, timestamp, OHLCV)
  - Backfill mechanism for gaps in data
  - Retention policy (e.g., 90 days for 1m bars)
  - Query performance <100ms for 1000 candles
- **Dependencies:** C1-01
- **Estimated Effort:** 1 session

#### C1-05: Data Service Health Monitoring
- **Description:** Health checks and metrics for data pipeline
- **Acceptance Criteria:**
  - `/health` endpoint (connection status, data freshness)
  - Prometheus metrics: `data_latency_ms`, `data_validation_failures`, `websocket_reconnects`
  - Grafana dashboard for data pipeline
  - Alert on WebSocket disconnect >60s
- **Dependencies:** C1-01, C1-02
- **Estimated Effort:** 1 session

---

## C2: Signal

**Goal:** Strategy signal generation with backtesting capability

### Subtasks

#### C2-01: Signal Strategy Interface
- **Description:** Abstract base class for trading strategies
- **Acceptance Criteria:**
  - `StrategyBase` class with `generate_signal(market_data) -> Signal` method
  - Support for multiple timeframes (1m, 5m, 1h)
  - Strategy configuration via YAML (parameters, symbols, timeframe)
  - Hot-reload of strategy parameters without restart
- **Dependencies:** C1
- **Estimated Effort:** 1 session

#### C2-02: Simple Moving Average (SMA) Strategy
- **Description:** Reference implementation of SMA crossover strategy
- **Acceptance Criteria:**
  - Buy signal: SMA(fast) crosses above SMA(slow)
  - Sell signal: SMA(fast) crosses below SMA(slow)
  - Configurable periods (default: 10/30)
  - Minimum confidence threshold (e.g., 0.7)
  - Unit tests for crossover logic
- **Dependencies:** C2-01
- **Estimated Effort:** 1 session

#### C2-03: Signal Publishing Pipeline
- **Description:** Redis Pub/Sub for signal distribution
- **Acceptance Criteria:**
  - Publish signals to `signals` channel
  - Signal schema: `{symbol, signal_type, price, confidence, timestamp, strategy_id}`
  - PostgreSQL persistence (`signals` table)
  - Signal deduplication (no duplicate signals within 1min window)
- **Dependencies:** C2-01
- **Estimated Effort:** 1 session

#### C2-04: Signal Backtesting Framework
- **Description:** Historical simulation of strategy signals
- **Acceptance Criteria:**
  - Backtest runner using historical OHLCV data
  - Metrics: signal accuracy, win rate, avg confidence
  - Comparison vs. buy-and-hold benchmark
  - Report generation (Markdown + PNG charts)
- **Dependencies:** C1-04, C2-01
- **Estimated Effort:** 2 sessions

---

## C3: Risk

**Goal:** Position sizing and risk guardrails

### Subtasks

#### C3-01: Position Sizing Algorithm
- **Description:** Kelly Criterion or fixed-fraction position sizing
- **Acceptance Criteria:**
  - Calculate position size based on account equity and signal confidence
  - Max position size: 10% of equity (configurable)
  - Max leverage: 1x (spot trading, no margin)
  - Rounding to exchange lot size
- **Dependencies:** C2
- **Estimated Effort:** 1 session

#### C3-02: Drawdown Guard Implementation
- **Description:** Circuit breaker on excessive drawdown
- **Acceptance Criteria:**
  - Calculate current drawdown from peak equity
  - Halt trading when drawdown exceeds threshold (e.g., -15%)
  - Publish alert to `alerts` channel
  - Resumption requires manual intervention
  - E2E test: TC-P0-003 (drawdown guard test)
- **Dependencies:** C5 (PSM for equity tracking)
- **Estimated Effort:** 1 session

#### C3-03: Max Daily Loss Limit
- **Description:** Daily loss limit to prevent runaway losses
- **Acceptance Criteria:**
  - Track cumulative P&L per day (resets at UTC midnight)
  - Halt trading when daily loss exceeds limit (e.g., -5% of equity)
  - Alert and log when limit triggered
  - PostgreSQL: `risk_events` table for audit trail
- **Dependencies:** C5
- **Estimated Effort:** 1 session

#### C3-04: Exposure Limits (Per-Symbol, Total)
- **Description:** Limit exposure to single symbol and total portfolio
- **Acceptance Criteria:**
  - Max exposure per symbol: 20% of equity
  - Max total exposure: 50% of equity (allows 2-3 positions max)
  - Reject orders exceeding limits
  - Metrics: `risk_exposure_pct{symbol}`, `risk_total_exposure_pct`
- **Dependencies:** C5
- **Estimated Effort:** 1 session

#### C3-05: Risk Service Health & Metrics
- **Description:** Observability for risk module
- **Acceptance Criteria:**
  - `/health` endpoint (risk checks status, current drawdown, exposure)
  - Prometheus metrics: `risk_drawdown_pct`, `risk_daily_pnl`, `risk_rejections_total`
  - Grafana dashboard for risk metrics
  - E2E test: Verify risk service responds to orders channel
- **Dependencies:** C3-01 to C3-04
- **Estimated Effort:** 1 session

---

## C4: Execution

**Goal:** Order lifecycle management with paper trading fills

### Subtasks

#### C4-01: Order Validation & Enrichment
- **Description:** Validate and enrich orders before execution
- **Acceptance Criteria:**
  - Validate order fields (symbol, quantity, price, type)
  - Check balance sufficiency (USDT available >= order value)
  - Enrich order with `order_id`, `timestamp`, `status=pending`
  - Reject invalid orders with reason
- **Dependencies:** C3
- **Estimated Effort:** 1 session

#### C4-02: Paper Trading Fill Simulation
- **Description:** Realistic fill simulation (no live exchange calls)
- **Acceptance Criteria:**
  - Market orders: Fill at latest cached price ± slippage (0.1%)
  - Limit orders: Fill when market price crosses limit
  - Partial fills: Simulate for large orders (>1% of volume)
  - Fill latency simulation: 100-500ms random delay
- **Dependencies:** C1-03 (Redis cache)
- **Estimated Effort:** 1-2 sessions

#### C4-03: Order Results Publishing
- **Description:** Publish order results to `order_results` channel
- **Acceptance Criteria:**
  - Schema: `{order_id, status, filled_qty, fill_price, fee, timestamp}`
  - PostgreSQL persistence (`orders` table)
  - Status transitions: pending → filled | rejected | partially_filled
  - E2E test: Verify order_results received by PSM
- **Dependencies:** C4-01, C4-02
- **Estimated Effort:** 1 session

#### C4-04: Order Retry & Timeout Handling
- **Description:** Retry logic for transient failures
- **Acceptance Criteria:**
  - Retry failed orders up to 3 times (exponential backoff: 1s, 2s, 4s)
  - Timeout orders stuck in pending >30s
  - Publish timeout event to `alerts` channel
  - E2E test: TC-P0-004 (circuit breaker test)
- **Dependencies:** C4-03
- **Estimated Effort:** 1 session

#### C4-05: Execution Service Metrics
- **Description:** Observability for execution service
- **Acceptance Criteria:**
  - `/health` endpoint (active orders count, last fill timestamp)
  - Prometheus metrics: `execution_orders_total{status}`, `execution_fill_latency_ms`, `execution_slippage_pct`
  - Grafana dashboard for execution metrics
  - Alert on fill latency >5s (indicates stale cache)
- **Dependencies:** C4-01 to C4-04
- **Estimated Effort:** 1 session

---

## C5: PSM (Position & State Management)

**Goal:** Maintain accurate position and account state

### Subtasks

#### C5-01: Position Tracking (Open/Close)
- **Description:** Track open positions from order fills
- **Acceptance Criteria:**
  - Create position on buy fill (long position)
  - Close position on sell fill (flat position)
  - Calculate realized P&L on close
  - PostgreSQL: `positions` table (symbol, qty, avg_price, unrealized_pnl, realized_pnl)
- **Dependencies:** C4
- **Estimated Effort:** 1-2 sessions

#### C5-02: Unrealized P&L Calculation
- **Description:** Mark-to-market P&L for open positions
- **Acceptance Criteria:**
  - Update unrealized P&L every 10s using latest market price
  - Formula: `(current_price - avg_entry_price) * qty`
  - Redis: Cache unrealized P&L for quick access
  - Prometheus metric: `psm_unrealized_pnl{symbol}`
- **Dependencies:** C5-01, C1-03
- **Estimated Effort:** 1 session

#### C5-03: Account Equity Tracking
- **Description:** Total account equity (cash + positions value)
- **Acceptance Criteria:**
  - Equity = Available Balance + Sum(Position Values)
  - Update equity on every fill and price update
  - PostgreSQL: `portfolio_snapshots` table (timestamp, total_equity, available_balance)
  - Snapshot every 1 hour for historical tracking
- **Dependencies:** C5-02
- **Estimated Effort:** 1 session

#### C5-04: State Consistency Checks
- **Description:** Detect and alert on state inconsistencies
- **Acceptance Criteria:**
  - Verify positions match order fills (no orphaned positions)
  - Verify balance = initial - sum(order costs) + sum(realized pnl)
  - Alert on mismatch (publish to `alerts` channel)
  - Daily reconciliation job (runs at 00:00 UTC)
- **Dependencies:** C5-01, C5-03
- **Estimated Effort:** 1-2 sessions

#### C5-05: PSM Service Health & Metrics
- **Description:** Observability for PSM
- **Acceptance Criteria:**
  - `/health` endpoint (positions count, total equity, balance)
  - Prometheus metrics: `psm_total_equity`, `psm_position_count`, `psm_reconciliation_errors`
  - Grafana dashboard for account state
  - E2E test: Verify positions created after fills
- **Dependencies:** C5-01 to C5-04
- **Estimated Effort:** 1 session

---

## C6: Observability

**Goal:** Comprehensive monitoring, logging, and alerting

### Subtasks

#### C6-01: Prometheus Metrics Standardization
- **Description:** Unified metrics naming and labeling across services
- **Acceptance Criteria:**
  - Naming convention: `<service>_<metric>_<unit>` (e.g., `risk_drawdown_pct`)
  - Standard labels: `service`, `environment`, `instance`
  - All services export `/metrics` endpoint
  - Metrics documented in `docs/metrics.md`
- **Dependencies:** C1-05, C3-05, C4-05, C5-05
- **Estimated Effort:** 1 session

#### C6-02: Grafana Dashboard Suite
- **Description:** Operational dashboards for all clusters
- **Acceptance Criteria:**
  - Dashboard 1: System Overview (all services health, uptime)
  - Dashboard 2: Trading Activity (signals, orders, fills, P&L)
  - Dashboard 3: Risk Monitoring (drawdown, exposure, limits)
  - Dashboard 4: Data Pipeline (WebSocket status, cache hit rate, latency)
  - JSON dashboards committed to `infrastructure/grafana/dashboards/`
- **Dependencies:** C6-01
- **Estimated Effort:** 2 sessions

#### C6-03: Structured Logging Standard
- **Description:** JSON logging with consistent fields
- **Acceptance Criteria:**
  - Log format: `{timestamp, level, service, message, context}`
  - Context includes: `order_id`, `symbol`, `strategy_id` (when applicable)
  - All services use same logging library (Python: `structlog`)
  - Logs written to `logs/<service>_YYYY-MM-DD.jsonl`
- **Dependencies:** None
- **Estimated Effort:** 1 session

#### C6-04: Alerting Rules (Prometheus Alertmanager)
- **Description:** Critical alerts for production incidents
- **Acceptance Criteria:**
  - Alert: Service down >1min (any service)
  - Alert: Drawdown exceeds threshold (-15%)
  - Alert: WebSocket disconnected >5min
  - Alert: Order fill latency >10s (sustained)
  - Alerts route to email or Slack (configurable)
- **Dependencies:** C6-01
- **Estimated Effort:** 1-2 sessions

#### C6-05: Log Aggregation & Search
- **Description:** Centralized log querying (optional: Loki)
- **Acceptance Criteria:**
  - All service logs ingested to Loki
  - Grafana Explore UI for log queries
  - Example queries documented in runbook
  - Retention: 7 days (configurable)
- **Dependencies:** C6-03
- **Estimated Effort:** 1 session

---

## C7: Reporting

**Goal:** Performance analytics and trade reporting

### Subtasks

#### C7-01: Daily P&L Report
- **Description:** Automated daily performance summary
- **Acceptance Criteria:**
  - Report includes: daily P&L, cumulative P&L, win rate, # trades
  - Generated at 00:05 UTC daily
  - Saved to `reports/daily/YYYY-MM-DD_pnl.md`
  - Optional: Email or Slack notification
- **Dependencies:** C5
- **Estimated Effort:** 1 session

#### C7-02: Trade Log Export
- **Description:** Export all trades to CSV for analysis
- **Acceptance Criteria:**
  - CSV columns: timestamp, symbol, side, qty, price, fee, realized_pnl
  - Command: `make export-trades START=2025-12-01 END=2025-12-31`
  - Output: `reports/trades_YYYY-MM-DD_to_YYYY-MM-DD.csv`
  - Supports filtering by symbol, strategy_id
- **Dependencies:** C5
- **Estimated Effort:** 1 session

#### C7-03: Equity Curve Visualization
- **Description:** Chart of account equity over time
- **Acceptance Criteria:**
  - Python script using `matplotlib` or `plotly`
  - X-axis: timestamp, Y-axis: total equity
  - Overlay drawdown shaded regions
  - Output: PNG or HTML file
  - Example: `python tools/plot_equity_curve.py --start 2025-12-01 --end 2025-12-31`
- **Dependencies:** C5-03
- **Estimated Effort:** 1 session

#### C7-04: Strategy Performance Metrics
- **Description:** Backtesting-style metrics for live trading
- **Acceptance Criteria:**
  - Metrics: Sharpe ratio, max drawdown, win rate, avg win/loss, profit factor
  - Calculated over rolling windows (7d, 30d, all-time)
  - Saved to PostgreSQL: `performance_metrics` table
  - Grafana dashboard for metric trends
- **Dependencies:** C5, C7-03
- **Estimated Effort:** 1-2 sessions

---

## C8: Ops

**Goal:** Production deployment and operational tooling

### Subtasks

#### C8-01: Production Docker Compose Stack
- **Description:** Separate `prod.yml` overlay for production config
- **Acceptance Criteria:**
  - `prod.yml` inherits from `base.yml`
  - Differences vs dev: no debug logging, tighter health checks, resource limits
  - Environment: `TRADING_MODE=paper`, `DRY_RUN=true` (initially)
  - Command: `docker compose -f base.yml -f prod.yml up -d`
- **Dependencies:** None
- **Estimated Effort:** 1 session

#### C8-02: Backup & Restore Scripts
- **Description:** Automated PostgreSQL backup and restore
- **Acceptance Criteria:**
  - Backup script: `make backup` (saves to `backups/postgres_YYYY-MM-DD.sql.gz`)
  - Restore script: `make restore FILE=backups/postgres_YYYY-MM-DD.sql.gz`
  - Automated daily backup (cron job or Docker scheduled task)
  - Backup retention: 30 days
- **Dependencies:** None
- **Estimated Effort:** 1 session

#### C8-03: Paper Trading Runbook
- **Description:** Complete operational runbook (already exists, extend)
- **Acceptance Criteria:**
  - Start/stop procedures for paper trading
  - Monitoring checklist (health, metrics, logs)
  - Common troubleshooting scenarios
  - Disaster recovery procedures (backup restore, full reset)
  - File: `docs/runbook_papertrading.md` ✅ COMPLETE (from Issue #123)
- **Dependencies:** All clusters
- **Estimated Effort:** 1 session (extend existing runbook)

#### C8-04: Pre-Flight Checklist Automation
- **Description:** Automated validation before starting trading
- **Acceptance Criteria:**
  - Script: `make preflight-check`
  - Checks: all services healthy, Redis/Postgres accessible, WebSocket connected, balance > minimum
  - Exit code 0 = ready, non-zero = not ready (logs failures)
  - Run automatically in `docker-compose up` startup sequence
- **Dependencies:** C1-05, C3-05, C4-05, C5-05
- **Estimated Effort:** 1 session

#### C8-05: 14-Day Paper Trading Test Plan
- **Description:** Documented test plan for final validation
- **Acceptance Criteria:**
  - Test plan includes: duration (14 days), expected signals, min # trades
  - Success criteria: zero critical errors, P&L within expected range, all health checks green
  - Daily checklist for manual review (logs, metrics, alerts)
  - Post-test report template
  - File: `docs/testing/14day_paper_test_plan.md`
- **Dependencies:** All clusters
- **Estimated Effort:** 1 session

---

## Dependencies Graph

```
C1 (Data/Feed)
  └─> C2 (Signal)
        └─> C3 (Risk)
              └─> C4 (Execution)
                    └─> C5 (PSM)

C1, C3, C4, C5 → C6 (Observability)
C5, C6 → C7 (Reporting)
All → C8 (Ops)
```

**Critical Path:** C1 → C2 → C3 → C4 → C5 → C8
**Parallelizable:** C6 can start after any cluster completes its health/metrics subtask

---

## Milestone Completion Criteria

M7 is complete when:

- [ ] All MUST-priority clusters (C1, C2, C3, C4, C5, C8) are 100% complete
- [ ] All subtasks have passing E2E tests (where applicable)
- [ ] All services have health endpoints + Prometheus metrics
- [ ] Grafana dashboards deployed and accessible
- [ ] Paper trading runbook complete and validated
- [ ] 14-day paper trading test completed successfully (zero critical errors)
- [ ] All documentation updated (`docs/`, `README.md`)

**Estimated Total Effort:** 30-40 sessions (6-8 weeks at 5 sessions/week)

---

## Next Steps

1. Review M7 skeleton with stakeholders (Approval required)
2. Convert each subtask into GitHub issues (tag with `milestone:m7`, `cluster:c1`, etc.)
3. Prioritize clusters based on dependencies (C1 → C2 → C3 → C4 → C5 → C6/C7 → C8)
4. Start implementation with C1-01 (Market Data Service)

---

**Status:** ✅ SKELETON COMPLETE
**Created:** 2025-12-27
**Last Updated:** 2025-12-27
