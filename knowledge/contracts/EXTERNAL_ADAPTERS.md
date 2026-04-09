# External Strategy and Execution Adapters

**Issue:** #190  
**Status:** Static registry boundary active; runtime wiring pending via `#1580`  
**Scope:** Define the smallest contract boundary for externally dockable
strategy and execution adapters without building a plugin platform.

## Befund

The current pipeline is event-driven, but the extension points are still
service-local:

- `services/signal/service.py` contains the active strategy logic directly.
  The current strategy is a built-in momentum rule keyed by
  `SIGNAL_STRATEGY_ID`.
- `services/execution/service.py` chooses the executor internally via
  `MOCK_TRADING` and wires directly to `MockExecutor` or `LiveExecutor`.
- `services/risk/service.py` is already the central policy and safety gate.
  It builds and verifies `decision_contract_v1`, enforces run modes, and
  publishes canonical orders.

This means strategy logic and venue execution are swappable in practice only
by changing core service code.

## Current Core Coupling

### Strategy path today

- Input: `market_data` event
- Service-local transformation: `services/signal/models.py:MarketData`
- Built-in decision: `services/signal/service.py::process_market_data()`
- Output: canonical `signal` payload to Redis

Coupling that should be loosened:

- signal generation rule lives inside the service loop
- strategy selection is effectively a single env value, not a registry surface
- external strategies would currently need to fork `cdb_signal`

### Execution path today

- Input: canonical `order` payload from Risk
- Service-local dispatch: `services/execution/service.py::init_services()`
- Executor choice:
  - `MockExecutor` for paper mode
  - `LiveExecutor` for MEXC-backed execution
- Output: canonical `order_results` payload

Coupling that should be loosened:

- executor selection is hardwired to internal classes
- venue-specific execution is embedded in the default execution service
- there is no explicit contract for third-party execution backends

## What Must Stay in Core

The following responsibilities remain core-owned and must not be delegated to
external adapters:

- runtime mode policy (`shadow`, `paper`, `replay`, `live`)
- risk gating and allocation checks
- `decision_contract_v1` creation and verification
- kill-switch and shutdown enforcement
- canonical Redis publish/stream behavior
- correlation, replay, and evidence emission
- canonical order/result normalization before leaving the service boundary

Adapters may contribute strategy or venue behavior. They do not become the
source of truth for governance or safety.

## Strategy Adapter Contract

Canonical code contract: `core/contracts/external_adapter_contracts.py`
Static registry: `core/contracts/external_adapter_registry.py`

### Input

A strategy adapter receives a normalized request:

- `symbol`
- `market_event`: raw inbound event snapshot
- `market_snapshot`: normalized market view prepared by the core
- `runtime_context`: run mode, bot context, and other non-authoritative hints

### Output

A strategy adapter returns zero or more signal candidates:

- `strategy_id`
- `symbol`
- `side`
- `reason`
- optional `confidence`
- optional `price`
- optional `pct_change`
- optional adapter metadata

### Boundary rule

The strategy adapter does **not** publish directly to Redis and does **not**
bypass `services/signal/models.py` or the canonical `signal` contract. The core
must translate candidates into canonical signal events.

## Canonical Config Surface for `primary_breakout_v1`

Canonical code contract: `core/contracts/primary_breakout_v1_config.py`
Canonical schema: `docs/contracts/primary_breakout_v1_config.schema.json`

The v1 config surface is intentionally small and explicit:

- `strategy_id = primary_breakout_v1`
- `symbol = BTCUSDT`
- `entry_lookback_minutes = 240`
- `exit_lookback_minutes = 120`
- `breakout_buffer = 0.0005`
- `min_minutes_between_entries = 60`
- `trade_side_mode = long_only`

Boundary rules for this config cut:

- no additional config keys
- no short-side switch in v1
- no multi-asset surface
- no service wiring implied by this config contract

## Execution Adapter Contract

Canonical code contract: `core/contracts/external_adapter_contracts.py`
Static registry: `core/contracts/external_adapter_registry.py`

### Input

An execution adapter receives an already approved order command:

- `order`: canonical order payload from Risk
- `run_mode`
- `decision_contract_v1`
- `runtime_context`
- optional `policy_snapshot`

### Output

An execution adapter returns a normalized execution response:

- `status`
- `order_id`
- `filled_quantity`
- optional `price`
- optional `venue_order_id`
- optional `error_message`
- optional raw venue payload for evidence/debugging

### Boundary rule

The execution adapter does **not** decide whether an order is allowed. It only
translates an already risk-approved order into venue behavior and returns a
normalized outcome for the core to persist and publish.

## Registration and Selection Model

The smallest viable selection model is static and repo-owned:

- one named strategy adapter id: `momentum_builtin`
- two named execution adapter ids: `mock_builtin`, `mexc_builtin`
- registry lives in-repo under `core/contracts/external_adapter_registry.py`
- selection stays ID-based only
- no remote loading
- no arbitrary package discovery

Canonical selection surface reserved for follow-up wiring:

- `SIGNAL_ADAPTER_ID`
- `EXECUTION_ADAPTER_ID`

Current default semantics after the registry cut:

- strategy default: `momentum_builtin`
- execution default: `mock_builtin` when `MOCK_TRADING=true`
- execution default: `mexc_builtin` when `MOCK_TRADING=false`

Current envs such as `SIGNAL_STRATEGY_ID`, `MOCK_TRADING`, and MEXC-specific
credentials remain the active runtime path until `#1580` wires the services to
the static registry.

## Smallest Meaningful Follow-up Implementation

This spec intentionally stops before runtime wiring. The next safe repo slice
would be:

1. Keep the static registry and fixed adapter IDs as the only selection surface.
2. Wire `cdb_signal` and `cdb_execution` to that surface in `#1580`.
3. Keep Risk, contract verification, publishing, and evidence paths unchanged.

This preserves the current core safety path while allowing external strategies
or venue adapters to dock at explicit seams.

## Non-Goals of This Spec Cut

- no plugin marketplace
- no dynamic dependency installation
- no hot-reload system
- no bypass of Risk or Decision Contract
- no cross-process adapter protocol yet
- no new live-trading path
