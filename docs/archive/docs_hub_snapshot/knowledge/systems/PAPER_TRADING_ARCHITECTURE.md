# PAPER_TRADING_ARCHITECTURE

Date: 2025-12-19
Scope: Paper trading implementation analysis (Working Repo)
Source: services/execution, services/risk

## Summary
Paper trading is currently implemented via the Execution Service using a MockExecutor when MOCK_TRADING=true. There is also a standalone PaperTradingEngine and a more detailed ExecutionSimulator, but neither is wired into the runtime service path. Risk-side validation and live-trading gate logic exist but are largely stubbed/simulated.

## Components (observed)

### Execution Service
- Entry: services/execution/service.py
- Mode switch: services/execution/config.py (MOCK_TRADING defaults to true)
- Flow:
  - Subscribe Redis topic orders
  - Execute via MockExecutor (paper trading)
  - Persist to PostgreSQL
  - Publish results to Redis topic order_results

### MockExecutor (active in paper mode)
- services/execution/mock_executor.py
- Simulates latency, slippage, and success/failure
- Returns ExecutionResult with simulated fill/reject

### PaperTradingEngine (not wired)
- services/execution/paper_trading.py
- Full in-memory paper trading session: orders, positions, PnL, metrics, log files
- Not referenced in service.py

### ExecutionSimulator (not wired)
- services/execution/simulator.py
- Higher-fidelity execution simulator (fees, slippage, partial fills)
- Not referenced in service.py

### Risk-side validation
- services/risk/live_trading_gate.py
  - LiveTradingGate uses simulated test results
  - Authorization defaults to PAPER_ONLY unless results pass
- services/risk/metrics.py
  - RiskMetrics includes paper trading validation criteria
  - calculate_comprehensive_metrics returns placeholder values
- services/risk/circuit_breakers.py
  - Breakers for drawdown and error rate (frequency, loss limit not fully implemented)

## Current runtime flow (paper mode)

Signal/Risk -> Redis orders -> Execution Service -> MockExecutor -> Postgres + Redis order_results

ASCII sequence (simplified):

Signal Engine
    |
    v
Risk Manager --(orders)-> Redis:orders
    |                       |
    |                       v
    |                Execution Service
    |                   - MockExecutor (paper)
    |                   - PostgreSQL writes
    |                   - Redis order_results
    v                       |
Order Results <-------------'

## Gaps / Test-readiness issues

### MUST
- PaperTradingEngine is not integrated with the Execution Service runtime path.
- LiveTradingGate uses simulated test results; no persistence or real test-result ingestion.
- RiskMetrics returns placeholder metrics; no linkage to real trades/positions.

### SHOULD
- ExecutionSimulator not integrated; paper mode uses only MockExecutor.
- No event-sourcing integration found in code for paper trading sessions.
- No unified storage for paper trading performance metrics across services.

### NICE
- Add explicit interfaces for pluggable execution simulators (MockExecutor vs ExecutionSimulator).

## References (files)
- services/execution/service.py
- services/execution/config.py
- services/execution/mock_executor.py
- services/execution/paper_trading.py
- services/execution/simulator.py
- services/risk/live_trading_gate.py
- services/risk/metrics.py
- services/risk/circuit_breakers.py

