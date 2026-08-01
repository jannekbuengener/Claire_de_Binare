# Execution Economics Gross-to-Net Contract v1

**Status:** Canonical research contract for #4150, funding/limit verdict from #4190

**Version:** `execution_economics_gross_to_net.v1`

**Code SSOT:** `core/replay/execution_economics_v1.py`

**Schema:** `docs/contracts/execution_economics_gross_to_net.v1.schema.json`

**Live-Readiness:** NO-GO

**Runtime impact:** none. #4190 touches `services/execution/simulator.py` only in
docstrings, log text and additive result metadata; no fill, fee or slippage
arithmetic changes, and no BLUE/RED/Paper/Live start.

## Purpose

Unify Replay, Mock/Paper comparison, and Candidate Evidence on one versioned,
deterministic economics meaning for fees, spread, slippage, fills, rejects,
latency/delay, and book-depth assumptions — and reconcile every economic claim
from Gross PnL through cost components to Net PnL.

This contract does **not** prove profitability, venue realism, or live readiness.

## Formula

```text
net_pnl =
  gross_pnl
  - total_fee_cost
  - spread_cost
  - slippage_cost
  - partial_fill_impact
  - reject_impact
  - latency_or_delay_impact
  - funding_cost_when_active
```

Rules:

- Cost components are unsigned (`>= 0`) and subtracted from gross.
- `gross_pnl` is reference/mid PnL on **filled** size and must not contain costs
  that are also subtracted as components.
- Slippage that is applied inside `avg_fill_price` must be attributed as
  `slippage_cost` against reference gross, or marked embedded via
  `fill_price_embedded_gross` (informational; never double-subtract).
- Not applicable / inactive / unavailable components use `amount=null` with an
  explicit status, not silent omission and not a measured zero.
- `reported_net_pnl` is optional. When supplied, `residual = reported - computed`
  and `reconciled` is only true within `residual_tolerance`.

### Component status vocabulary

| Status | Amount | Subtracted | Meaning |
|---|---|---|---|
| `active` | number | yes | Measured cost |
| `zero` | `0` | yes | Measured and genuinely zero |
| `embedded_in_fill_price` | number | **no** | Already inside the fill price; informational only |
| `not_applicable` | `null` | no | Does not apply to this path |
| `inactive_not_wired` | `null` | no | Surface exists but no runner consumes it |
| `unavailable` | `null` | no | Applies in principle, but the input cannot be sourced |

### Fail-closed status/value rules

- Supplying a value under a null-amount status raises `ExecutionEconomicsError`.
  A cost is never silently dropped, and a missing input is never silently zeroed.
- Unknown status, `order_type` or `fill_status` strings are rejected.

## Execution semantics

`execution_semantics` disambiguates the maker/taker, fill and funding cases:

| Field | Values | Rule |
|---|---|---|
| `order_type` | `market`, `limit` | ARVP/replay is market-only |
| `fill_status` | `filled`, `partially_filled`, `not_filled` | See below |
| `maker_fill_evidence` | boolean | Required for any non-zero `maker_fee_cost` |
| `funding_basis` | object or `null` | Present only when funding is active |

- `maker_fee_cost > 0` requires `order_type="limit"` **and**
  `maker_fill_evidence=True`. Maker fills are never assumed on the market path.
- `fill_status="not_filled"` requires `gross_pnl == 0` and zero fees/slippage;
  the forgone PnL belongs in `partial_fill_impact`.
- `fill_status="partially_filled"` requires a billable `partial_fill_impact`.
- `fill_status="filled"` forbids a non-zero `partial_fill_impact`.

## Units and boundaries

| Quantity | Unit | Notes |
|---|---|---|
| PnL / costs | quote currency (string decimal) | Quantized to 1e-8 |
| Order size | base quantity | Research default `1.0` (synthetic) |
| Notional / book depth | quote | Depth `max(volume*price*mult, price)` |
| Fee rates | rate | Defaults `0.0002` / `0.0006` (synthetic) |
| Slippage | bps | `0 .. 10000`; rate↔bps conversion explicit |
| Usable depth fraction | fraction | `0 .. 1` (maps to `FILL_THRESHOLD`) |
| Depth impact factor | coefficient | `0 .. 10` (maps to `DEPTH_IMPACT_FACTOR`) |
| Delay | bars | Runner-dependent |
| Latency (mock) | milliseconds | Seeded uniform 50–200 |

Negative rates/BPS (rebates) are **not** supported in v1.

## Scenario field → simulator mapping

| Scenario field | Simulator field | Actual effect |
|---|---|---|
| `execution_slippage_bps` | `BASE_SLIPPAGE_BPS` | Replaces base slippage bps |
| `usable_depth_fraction` | `FILL_THRESHOLD` | Usable depth fraction, **not** probabilistic fill rate |
| `depth_impact_factor` | `DEPTH_IMPACT_FACTOR` | Slippage depth-impact coefficient, **not** depth shrink |
| `execution_delay_bars` | `EXECUTION_DELAY_BARS` | Bar delay when runner implements it |
| `feed_gap_bars` | (replay data) | Stale midpoint bars |
| `execution_posture` | `_execution_posture` | Metadata tag only |

### Breaking rename (fail-closed)

| Legacy (rejected) | Replacement |
|---|---|
| `fill_rate` | `usable_depth_fraction` |
| `fill_depth_factor` | `depth_impact_factor` |

Legacy keys are rejected with an explicit error. No silent aliasing.

## Assumptions snapshot

Required snapshot fields include `order_size`, `book_depth.depth_multiplier`,
`fee_schedule`, `spread_model`, `slippage_model`, `fill_model`, `reject_model`,
`latency_model`, funding/limit inactivity flags, and a deterministic
`fingerprint`. Secrets are forbidden.

Defaults remain the historical research hardcodes (`order_size=1.0`,
`depth_multiplier=10000`) and are marked **synthetic**.

## Funding and limit orders: wire-or-retire verdict (#4190)

Both surfaces inventoried by #4150 were re-examined against the **active** data
and runner path. Verdict: `RETIRE_OR_PARK_DEAD_SURFACES` for both. Neither is
deleted — each stays visible and explicitly labelled as not active and not
billable.

### Funding — retired, `inactive_not_wired`, input `unavailable`

Evidence:

- Replay datasets are OHLCV only (`open, high, low, close, volume`); the
  repository contains no funding-rate series.
- `ExecutionSimulator.FUNDING_RATE` defaults to `0.0001` with provenance
  `synthetic_default` — an unverified venue assumption, not a measurement.
- No runner tracks per-position holding duration across settlement boundaries,
  so `hours_held` has no measured source either.
- `calculate_funding_fees` has no production caller.

Contract behaviour:

- `funding_cost_when_active` stays `inactive_not_wired` with `amount=null`, and
  `assumptions_snapshot.funding_model.input_availability` reports
  `unavailable_no_funding_rate_series`.
- Activating funding is fail-closed. It requires a complete `funding_basis`
  (`position_value`, `funding_rate`, `funding_rate_source`, `hours_held`,
  optional `settlement_hours`) whose source is **not** in
  `UNPROVEN_FUNDING_RATE_SOURCES`. The cost is then derived by
  `funding_cost_from_rate` — a bare `funding_cost` scalar is rejected.
- A supplied `funding_cost` that disagrees with the derived value is rejected.

This is the wiring seam: once a sourced funding-rate series and holding
durations exist, funding activates through `funding_basis` without further
contract changes.

### Limit orders — retired from the economics path, parked in the simulator

Evidence:

- `simulate_limit_order` has no production caller; the only references live in
  `tests/unit/verlosung/`, which `pytest.ini` excludes via `norecursedirs` and
  which cannot import (`ModuleNotFoundError: services.execution_simulator`).
- Its fill trigger is economically inverted: a buy limit at or above market is
  marketable and crosses the book, yet it is booked at the **maker** rate with
  zero slippage. That guarantees maker fills, which is exactly the assumption
  this contract forbids.

Contract behaviour:

- `ExecutionResult` now carries `order_type`, `fee_role` and
  `economics_billable`. Limit results are `economics_billable=False` with
  `fee_role="maker_assumed_unproven"`; market results are billable takers.
- `assumptions_snapshot.limit_order_model.status` is
  `parked_not_economics_billable`, matched by
  `services.execution.simulator.LIMIT_ORDER_MODEL_STATUS` and asserted by a
  parity test.
- Activating limit orders in the snapshot requires an explicit
  `limit_order_fill_model`; there is no default.

A real limit-order model needs queue position and venue fill evidence and is
out of scope here.

## Replay vs Paper

Component diffs use `compare_economics_components`. Mock economics assumptions
(seeded success/reject, 50–200 ms latency, % slippage, no fees/spread) are
documented under `mock_paper_comparison` and must not be read as venue proof.

Replay, paper and candidate evidence all go through `reconcile_gross_to_net`, so
they share one contract semantics: identical funding/limit status, identical
`execution_semantics`, and an identical `assumptions_snapshot.fingerprint` for
identical assumptions. Components that are null on either side are reported as
`incomparable` or `both_not_applicable_or_missing` — never as a zero delta.

## Relationship to Profitability Economics v1 (#3039)

`profitability_execution_economics_model.v1` /
`profitability_execution_economics_assessment.v1` remain research assessment
surfaces. This v1 contract is the executable Gross-to-Net SSOT consumed by
scenario mapping, candidate evidence cost blocks, and replay-vs-paper component
diffs.

## Safety

- Stage-A/B gates unchanged
- Risk/exposure/drawdown limits unchanged
- No Live-Go / LR-Go / Echtgeld-Go
- Cost assumptions must not be softened to improve Net PnL appearance
