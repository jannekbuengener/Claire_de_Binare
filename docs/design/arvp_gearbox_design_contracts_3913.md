# ARVP Gearbox Design Contracts (#3913)

Status Class: **DESIGN_CONTRACT_ONLY** — no runtime authority, no trade approval  
Issue: [#3913](https://github.com/jannekbuengener/Claire_de_Binare/issues/3913)  
Parent: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)  
Related: [#3894](https://github.com/jannekbuengener/Claire_de_Binare/issues/3894) (closed feasibility)  
Live-Readiness: **NO-GO**  
Echtgeld: **not authorized**

---

## 1. Executive Summary

Parallel `cdb_signal` is **infrastructure**, not the Gearbox end state. Before any
2-strategy parallel natural-paper pilot ([#3912](https://github.com/jannekbuengener/Claire_de_Binare/issues/3912)),
CDB defines five repo-backed design contracts:

| Contract | Schema | Role |
|----------|--------|------|
| Gear Registry | `strategy_gear_registry.v1` | Declares a strategy lane as a controlled gear |
| Selector Decision | `selector_decision.v1` | Advisory lane selection envelope |
| Gear Reason Codes | `gear_reason_codes.v1` | Taxonomy for selection / rejection / idle |
| Protective Idle | `protective_idle.v1` | Valid no-trade gearbox output |
| Loop Boundary | `loop_boundary.v1` | Learning Loop vs Trading Loop separation |

**Core doctrine:** continuous market coverage, not continuous trading. Always
evaluating, never forcing. Selector output is **not** trade approval.

Target flow (design reference only):

```text
Gear Registry → Eligibility/Selector → Sleeve Context → Risk → KillSwitch → Execution Gate → Paper/Testnet/Micro-Live Boundary
```

---

## 2. Gear Lifecycle States

| State | Meaning |
|-------|---------|
| `PARKED` | Candidate exists; not eligible for selection |
| `ELIGIBLE` | Conditions and evidence allow consideration |
| `SELECTED` | Selector chose this gear for the current context |
| `IDLE` | Protective Idle — no gear should trade |
| `BLOCKED` | Explicitly blocked (risk, evidence, regime, runtime) |

Idle is **not** failure. It is capital protection.

---

## 3. Contract: `strategy_gear_registry.v1`

Schema: [`docs/contracts/strategy_gear_registry.v1.schema.json`](../contracts/strategy_gear_registry.v1.schema.json)  
Example: [`docs/contracts/examples/strategy_gear_registry_valid.json`](../contracts/examples/strategy_gear_registry_valid.json)

A gear is **not** a strategy implementation. It is the controlled declaration of
when a candidate lane may be considered.

Minimum fields:

- `gear_id`, `strategy_id`, `bot_id` (operational convention)
- `supported_modes` — shadow / paper / live eligibility flags
- `runtime_readiness` — `runtime` | `replay_only`
- `evidence_requirements` — lifecycle, ranking, net economics refs
- `allocation_profile` — link to allocation rules (not implementation)
- `risk_boundaries` — sleeve, exposure caps, `no_live_authority`
- `allowed_outputs` — advisory selector/ranking outputs only
- `known_limitations` — explicit gaps

Gear lifecycle state is carried in `routing_state.lifecycle_state`.

---

## 4. Contract: `selector_decision.v1`

Schema: [`docs/contracts/selector_decision.v1.schema.json`](../contracts/selector_decision.v1.schema.json)  
Example: [`docs/contracts/examples/selector_decision_valid.json`](../contracts/examples/selector_decision_valid.json)

Selector output is **advisory**. It does not authorize orders.

Minimum fields:

- `selected_gear` — nullable; `null` means Protective Idle
- `eligible_gears`, `rejected_gears`
- `reason_codes[]` — from `gear_reason_codes.v1`
- `protective_idle_allowed: true`
- `evidence_snapshot_ref`
- `no_trade_approval: true` (required, must be `true`)
- `decision_scope` — symbol, timeframe, evaluation window

---

## 5. Contract: `gear_reason_codes.v1`

Schema: [`docs/contracts/gear_reason_codes.v1.schema.json`](../contracts/gear_reason_codes.v1.schema.json)  
Example: [`docs/contracts/examples/gear_reason_codes_valid.json`](../contracts/examples/gear_reason_codes_valid.json)

Canonical codes (minimum set):

| Code | Category |
|------|----------|
| `SELECTED` | Gear chosen for current context |
| `PARKED` | Gear exists but not eligible |
| `BLOCKED` | Explicit block |
| `IDLE` | Protective Idle active |
| `EVIDENCE_GAP` | Missing or stale evidence |
| `RISK_BLOCKED` | Risk gate would block |
| `REGIME_MISMATCH` | Regime outside gear scope |
| `NOT_RUNTIME_READY` | Replay-only or adapter missing |
| `DATA_STALE` | Market/data freshness failure |
| `CORRELATION_RISK` | Cross-lane correlation too high |
| `SLEEVE_LIMIT` | Capital sleeve cap reached |

---

## 6. Contract: `protective_idle.v1`

Schema: [`docs/contracts/protective_idle.v1.schema.json`](../contracts/protective_idle.v1.schema.json)  
Example: [`docs/contracts/examples/protective_idle_valid.json`](../contracts/examples/protective_idle_valid.json)

Protective Idle semantics:

- Idle is a **valid** gearbox output.
- Idle is **not** an error or failed run.
- Idle is **not** trading approval.
- Idle may arise from: evidence gap, regime mismatch, risk block, missing
  eligibility, unclear market state, or global gate dirtiness.

ARVP evidence for [#3912](https://github.com/jannekbuengener/Claire_de_Binare/issues/3912) must be able to document
Protective Idle periods per lane without treating them as pilot failure.

---

## 7. Contract: `loop_boundary.v1`

Schema: [`docs/contracts/loop_boundary.v1.schema.json`](../contracts/loop_boundary.v1.schema.json)  
Example: [`docs/contracts/examples/loop_boundary_valid.json`](../contracts/examples/loop_boundary_valid.json)

| Loop | May do | Must not do |
|------|--------|-------------|
| **Learning Loop** | Evaluate candidates, rank gears, collect evidence, produce selector advisories | Submit orders, bypass Risk/KillSwitch/Execution |
| **Trading Loop** | Act only after Risk → KillSwitch → Execution Gate | Collapse evaluation into forced trading |

Rules:

- Selector output is **not** an order approval.
- Evidence may **not** replace runtime gate checks.
- Learning Loop and Trading Loop must **never** be collapsed.

---

## 8. Relationship to Follow-ups

| Issue | Role vs Gearbox | How contracts apply |
|-------|-----------------|---------------------|
| [#3909](https://github.com/jannekbuengener/Claire_de_Binare/issues/3909) | Technical prerequisite — compose isolation | Each `cdb_signal` instance maps to one `gear_id` + `bot_id` in registry |
| [#3910](https://github.com/jannekbuengener/Claire_de_Binare/issues/3910) | Technical prerequisite — allocation | `allocation_profile` links gear to `ALLOCATION_RULES_JSON` entries |
| [#3911](https://github.com/jannekbuengener/Claire_de_Binare/issues/3911) | Technical prerequisite — ledger guards | Evidence extraction per `strategy_id`/`bot_id` supports per-gear provenance |
| [#3912](https://github.com/jannekbuengener/Claire_de_Binare/issues/3912) | Pilot execute — **not ready** | Alignment review against these contracts + separate RUNTIME-GO required |

These follow-ups are **not** the Gearbox end state. They enable safe parallel
observation as a controlled precursor.

---

## 9. Pilot Readiness (#3912)

**#3912 is not ready** after this slice alone. Required before RUNTIME-GO:

1. This design-contract delivery (docs + schemas + contract tests) — **this issue**
2. [#3910](https://github.com/jannekbuengener/Claire_de_Binare/issues/3910) — Donchian allocation rules
3. [#3909](https://github.com/jannekbuengener/Claire_de_Binare/issues/3909) — Compose multi-`cdb_signal` profile
4. [#3911](https://github.com/jannekbuengener/Claire_de_Binare/issues/3911) — Ledger/evidence isolation guards
5. Alignment review: pilot manifest documents gears, selector advisory-only posture, Protective Idle
6. Explicit **RUNTIME-GO** for [#3912](https://github.com/jannekbuengener/Claire_de_Binare/issues/3912)

---

## 10. Boundaries

- LR **NO-GO** — no Live/Echtgeld authorization
- No runtime, Docker, Compose, DB, Risk, Execution, or Allocation implementation
- [#3893](https://github.com/jannekbuengener/Claire_de_Binare/issues/3893) untouched — separate single-strategy observation
- [#205](https://github.com/jannekbuengener/Claire_de_Binare/issues/205) remains parked Gearbox anchor — reference only
- Contracts do not unpark or rescope [#205](https://github.com/jannekbuengener/Claire_de_Binare/issues/205)

---

## 11. References

- [Multi-Strategy Gearbox Architecture v1](https://gist.github.com/jannekbuengener/82db215ed91096d7d864cc51d73f0557)
- [Gearbox Alignment Report](https://gist.github.com/jannekbuengener/cbca4d7e0e85b51e43d772ddfcabc102)
- [`docs/design/arvp_multistrategy_parallel_natural_paper_feasibility_3894.md`](arvp_multistrategy_parallel_natural_paper_feasibility_3894.md)
- [`docs/contracts/README.md`](../contracts/README.md)
