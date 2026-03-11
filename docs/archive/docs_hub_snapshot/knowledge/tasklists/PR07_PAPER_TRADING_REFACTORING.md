# PR07_PAPER_TRADING_REFACTORING

Date: 2025-12-19
Scope: Implementation plan for PR-07 (paper trading service refactor)
Repo: Claire_de_Binare (Working Repo)

## Current state (observed)
- services/execution/mock_executor.py: basic mock execution (latency, slippage, success rate)
- services/execution/simulator.py: higher-fidelity simulator (fees, slippage, partial fills)
- services/execution/config.py: MOCK_TRADING defaults true
- services/execution/service.py: uses MockExecutor when MOCK_TRADING=true

## Gap vs PR-07 requirements
- No Prometheus metrics for paper trading yet.
- Multi-asset support is implicit; not explicit in config.
- Partial fills exist in simulator, but not wired to execution service.
- Fees/slippage config not exposed to runtime.

## Proposed implementation steps
1. Extend MockExecutor to support:
   - fee calculation
   - partial fills (optional)
   - configurable symbols and slippage ranges
2. Add metrics module (Prometheus) and export counters/gauges.
3. Add config flags for paper trading parameters.
4. Wire metrics into execution service.
5. Tests: unit tests for mock executor + metrics.

## Dependencies
- None required, but PR-08 schema should follow for persistence.

## Acceptance targets
- Deterministic simulation
- Metrics scrape works
- Tests pass locally
