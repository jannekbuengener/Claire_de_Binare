# Execution Economics Gross-to-Net Contract v1

**Status:** Canonical research contract for #4150  
**Version:** `execution_economics_gross_to_net.v1`  
**Code SSOT:** `core/replay/execution_economics_v1.py`  
**Schema:** `docs/contracts/execution_economics_gross_to_net.v1.schema.json`  
**Live-Readiness:** NO-GO  
**Runtime impact:** none (no BLUE/RED/Paper/Live start; no `services/execution/**` edits in this slice)

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
- Not applicable / inactive components use `amount=null` with explicit status
  (`not_applicable` or `inactive_not_wired`), not silent omission.

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

## Inactive surfaces (CDB-032)

- **Funding:** `calculate_funding_fees` / `FUNDING_RATE` exist on the simulator
  but are not wired into ARVP/replay PnL → `inactive_not_wired`.
- **Limit orders:** `simulate_limit_order` exists but ARVP runners do not call it
  → `inactive_not_wired`. No new limit-order engine in this issue.

## Replay vs Paper

Component diffs use `compare_economics_components`. Mock economics assumptions
(seeded success/reject, 50–200 ms latency, % slippage, no fees/spread) are
documented under `mock_paper_comparison` and must not be read as venue proof.

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
