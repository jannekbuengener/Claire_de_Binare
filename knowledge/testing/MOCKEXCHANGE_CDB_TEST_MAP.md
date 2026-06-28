# MockExchange CDB Test Map

Status: active planning map
Date: 2026-06-23
Scope: CDB test design, MockExchange reference usage, no runtime activation

## Purpose

This document makes the local MockExchange reference concretely usable for CDB.
It does not integrate MockExchange into CDB yet. It translates the strongest
MockExchange test patterns into CDB test targets.

MockExchange is valuable because it solves the same practical problem as CDB's
paper/execution layer: safe order handling without live capital.

## Sources Read

- Local toolchain source: `D:\Dev\Tools\GitHub\Desktop\SKILLS\mockexchange\`
- MockExchange README: `packages/engine`, `packages/oracle`, `packages/periscope`, `packages/valkey`
- MockExchange unit tests:
  - `packages/engine/tests/unit/test_market.py`
  - `packages/engine/tests/unit/test_orderbook.py`
- MockExchange integration tests:
  - `test_03_market_orders_property.py`
  - `test_04_limit_orders_property.py`
  - `test_06_fund_and_full_rejected_insufficient_trade_when_buy.py`
  - `test_09_fund_and_rejected_insufficient_fee_when_sell.py`
- CDB current references:
  - `tools/test_pack/README.md`
  - `.opencode/skills/cdb-shadow-validation/SKILL.md`
  - `knowledge/governance/SERVICE_CATALOG.md`
  - `knowledge/testing/PAPER_TRADING_TEST_REQUIREMENTS.md`
  - `knowledge/testing/TEST_HARNESS_V1.md`
  - `tests/unit/services/test_execution_state_machine.py`
  - `tests/integration/test_execution_pipeline.py`
  - `tests/e2e/test_paper_trading_p0.py`
  - `tests/unit/replay/test_replay_vs_paper_compare.py`

## Existing CDB Boundary

MockExchange already exists in CDB as a local reference copy, not as active
runtime.

- `tools/test_pack/mock_exchange/` is gitignored and must not be staged.
- `mockx-valkey` is non-canonical dev/test reference infra.
- Expected state for `mockx-valkey`: absent by default.
- CDB canonical Redis remains `cdb_redis`.
- Full MockExchange stack use requires explicit future issue and Jannek Ops GO.
- No Live-Go or Echtgeld-Go follows from any MockExchange result.

## Practical Meaning For CDB

MockExchange should first be used as a test-pattern source, not as a runtime
dependency.

The immediate CDB value is not "run their stack". The immediate value is:

- copy the test ideas,
- adapt the invariants to CDB's execution and risk contracts,
- keep the tests deterministic,
- keep the path mock/shadow only,
- prove that CDB leaves no stuck orders, locked funds, false fills, or fee leaks.

## Strongest MockExchange Test Ideas

| MockExchange pattern | What it proves | CDB translation |
|---|---|---|
| `Market.fetch_ticker()` returns parsed ticker or `None` on malformed data | Bad market data must not become a valid price | CDB market/candles consumers should reject malformed payloads fail-closed |
| `OrderBook.add()` indexes only open orders | Closed orders must not remain active | CDB execution state must not leave terminal orders in active queues |
| `OrderBook.remove()` clears symbol and global indexes | Cancel/remove must clean all views | CDB order lifecycle should remove or mark all active references consistently |
| Market order property test | Every market order converges to terminal state and no funds remain locked | CDB execution mock should prove state convergence and no residual reservations |
| Limit order property test | Price move triggers matching and then terminal state | CDB replay/emulator tests should prove deterministic limit-order trigger behavior |
| BUY insufficient-funds tamper test | Reservation rollback after pre-fill shortfall | CDB Risk/Execution should reject and leave no persisted false fill |
| SELL insufficient-fee tamper test | Fee shortage blocks execution and releases all reservations | CDB fee/slippage model should prove fee fail-closed behavior |
| Order generator example | High-volume random order stimulus | CDB can use this idea for soak, watchdog, and replay-vs-paper stress tests |

## Test Basket Mapping

### 1. Bauteil-Tests

Best MockExchange source:

- `test_market.py`
- `test_orderbook.py`

CDB target:

- `tests/unit/services/test_execution_state_machine.py`
- `tests/unit/services/test_execution_negative_payloads.py`
- future focused tests around execution order indexing, terminal-state handling,
  malformed market data, and no stale active-order references.

Concrete CDB test ideas:

- terminal execution statuses have no outgoing transitions,
- rejected and filled orders never remain in active/open views,
- malformed price payload cannot create a fill,
- unknown symbol or missing ticker must fail closed.

### 2. Ketten-Tests

Best MockExchange source:

- market-order property test,
- limit-order property test,
- API-level integration helpers.

CDB target:

- `tests/integration/test_execution_pipeline.py`
- `tests/e2e/test_paper_trading_p0.py`
- replay-vs-paper compare tests.

Concrete CDB test ideas:

- signal/order/result chain reaches exactly one terminal outcome,
- order result is published once and persisted once,
- replay output and paper output agree on order/fill counts,
- market and limit order paths share the same terminal-state contract.

### 3. Schutz-Tests

Best MockExchange source:

- insufficient BUY funds after reservation,
- insufficient SELL fee after reservation,
- cancel limit orders,
- partial reject tests.

CDB target:

- Risk Service guard tests,
- execution shadow gate tests,
- emergency stop and circuit breaker tests.

Concrete CDB test ideas:

- if balance disappears after risk approval but before execution, execution must reject,
- if fee budget is insufficient, execution must reject and record no fill,
- if shadow mode is active, executor must not be called,
- if kill switch is active, no order enters execution.

### 4. Wirtschafts-Tests

Best MockExchange source:

- commission calculation,
- fee reservation,
- slippage-like market fill parameters,
- portfolio `free`/`used` accounting.

CDB target:

- paper runner profitability checks,
- replay-vs-paper comparison,
- future ARVP profitability evidence.

Concrete CDB test ideas:

- gross PnL and net PnL differ by explicit fees,
- slippage changes net result and can flip marginal winners into losers,
- rejected orders do not count as fills,
- partial fills produce explicit residual exposure.

### 5. Betriebs-Tests

Best MockExchange source:

- order generator example,
- async settle wait,
- polling until open orders disappear,
- service-specific logs/status commands.

CDB target:

- soak-style paper runs,
- watchdog checks,
- long-run evidence bundles.

Concrete CDB test ideas:

- random but seeded order bursts leave zero active orders after shutdown,
- long paper run leaves no orphaned order IDs,
- recovery after restart does not duplicate fills,
- evidence bundle includes counts for orders, fills, rejects, locks, and fees.

### 6. Wissens-Tests

Best MockExchange source:

- readable test docstrings,
- test README explaining unit vs integration boundaries,
- explicit package boundaries.

CDB target:

- SurrealDB/context intelligence evidence model,
- agent onboarding,
- docs-to-test consistency checks.

Concrete CDB test ideas:

- every paper/execution test has a documented target contract,
- docs say `mockx-valkey` is absent by default and service catalog agrees,
- shadow-validation skill says exchange-facing changes require MockExchange or
  emulator evidence,
- future SurrealDB evidence rows link code path, test, issue, and result without
  conflicting truths.

## Recommended First Implementation Slice

First implement CDB-native tests. Do not import MockExchange yet.

### Slice A: Execution terminal-state convergence

Goal: prove every accepted CDB mock execution reaches exactly one terminal state.

Candidate files:

- `tests/unit/services/test_execution_state_machine.py`
- `tests/integration/test_execution_pipeline.py`

Expected assertions:

- every path ends in `FILLED`, `REJECTED`, `FAILED`, or `CANCELLED`,
- no terminal state transitions again,
- repeated partial-fill updates are idempotent only while still partial,
- published result matches persisted result.

### Slice B: No residual lock / no false fill

Goal: port MockExchange's strongest accounting invariant to CDB language.

Candidate files:

- `tests/integration/test_execution_pipeline.py`
- `tests/e2e/test_paper_trading_p0.py`
- future paper-runner accounting tests.

Expected assertions:

- rejected orders produce zero filled quantity,
- blocked shadow orders never call executor,
- no fill event is emitted for a rejected order,
- no order can be both rejected and filled.

### Slice C: Fee and slippage realism

Goal: make profitability tests less naive.

Candidate files:

- replay-vs-paper compare tests,
- paper runner tests,
- future strategy profitability tests.

Expected assertions:

- fees are explicit,
- slippage is explicit,
- net result is reported separately from gross result,
- profitability gates use net result, not only fill count.

## When To Use Full MockExchange Later

Use the full MockExchange stack only when the CDB change touches one of these
surfaces:

- exchange adapter behavior,
- order matching assumptions,
- fill handling,
- fee/slippage accounting,
- portfolio reservation logic,
- high-volume randomized order behavior,
- REST-style exchange API compatibility.

Do not use full MockExchange for:

- pure docs changes,
- isolated utility functions,
- SurrealDB-only context tooling,
- non-execution CI hygiene,
- normal unit-test-only changes.

## Stop Conditions

- Stop if a planned test requires starting Docker without Jannek Ops GO.
- Stop if a test would use live exchange credentials or live order endpoints.
- Stop if `mockx-valkey` is treated as a replacement for `cdb_redis`.
- Stop if the nested MockExchange repo would be staged or committed.
- Stop if a validation result is used as LR-Go, Echtgeld-Go, or strategy release.
- Stop if CDB and MockExchange order semantics differ and the adapter contract is
  not explicitly documented.

## Minimal Next Actions

1. Add CDB-native state-convergence tests inspired by MockExchange market-order
   properties.
2. Add CDB-native reject/no-fill accounting tests inspired by MockExchange
   insufficient-funds and insufficient-fee scenarios.
3. Extend replay-vs-paper comparison to report gross result, fees, slippage, and
   net result separately.
4. Decide in a dedicated issue whether CDB needs the upstream MockExchange Engine
   package pinned from tag `v0.1.5`.
5. If full MockExchange is approved later, keep it session-local and prove
   teardown of `mockx-valkey` as part of the evidence.

## Bottom Line

MockExchange should become CDB's reference for execution realism tests, not a
new always-on dependency. The first useful move is to port its invariants into
CDB-native pytest coverage: terminal-state convergence, no residual locks, no
false fills, explicit fee/slippage accounting, and deterministic order bursts.
