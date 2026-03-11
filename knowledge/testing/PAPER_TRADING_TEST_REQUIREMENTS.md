# PAPER_TRADING_TEST_REQUIREMENTS

Date: 2025-12-19
Scope: P0 E2E paper trading scenarios
Repository: Claire_de_Binare (execution-only)

## Purpose
Define deterministic P0 E2E paper trading test cases and required conditions.

## Preconditions
- Paper trading mode enabled (MOCK_TRADING=true).
- Redis and Postgres available via docker-compose.
- Risk gates configured for paper-only.

## P0 Test Cases

### TC-P0-001: Happy Path (market_data -> trade)
Goal: End-to-end order flow completes with a filled mock execution.
Steps:
1) Start stack (docker-compose).
2) Submit a valid order to Risk Manager input channel.
3) Verify Execution Service consumes order and returns FILLED status.
4) Verify order persisted in Postgres.
Expected:
- order_results contains FILLED
- DB contains order + trade row

### TC-P0-002: Risk Blockierung (Position Limit)
Goal: Risk layer blocks oversized position.
Steps:
1) Submit order above max_position_size.
2) Verify order is rejected before execution.
Expected:
- order_results shows REJECTED with risk reason
- No trade persisted

### TC-P0-003: Daily Drawdown Stop
Goal: Trigger daily loss guard and block subsequent orders.
Steps:
1) Inject sequence of losing trades to exceed daily loss limit.
2) Submit another order.
Expected:
- risk gate denies new orders
- explicit drawdown stop reason

### TC-P0-004: Circuit Breaker Trigger
Goal: Trigger circuit breaker on error rate or drawdown.
Steps:
1) Inject error rate over threshold or drawdown over threshold.
2) Verify breaker triggers and blocks execution.
Expected:
- breaker flagged
- no execution for subsequent orders

### TC-P0-005: Data Persistence Check
Goal: Ensure persistence for paper trades.
Steps:
1) Place order(s) in paper mode.
2) Query DB for orders and trades.
Expected:
- orders table populated
- trades table populated for filled orders

## Determinism Rules
- Fixed seeds for any simulations
- Fixed timestamps where possible
- No external network calls

## Known Gaps (from code audit)
- PaperTradingEngine and ExecutionSimulator are not wired into runtime path.
- RiskMetrics uses placeholder values.
- LiveTradingGate uses simulated test results.

