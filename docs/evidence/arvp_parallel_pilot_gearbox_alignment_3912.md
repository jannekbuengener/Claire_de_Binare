# ARVP Parallel Pilot — Gearbox Alignment Review (#3912)

Status Class: **DESIGN_ALIGNMENT_ONLY** — no runtime authority, no trade approval  
Issue: [#3912](https://github.com/jannekbuengener/Claire_de_Binare/issues/3912)  
Hypothesis: `HYP-NP-PARALLEL-2S-01`  
Gearbox contracts: [#3913](https://github.com/jannekbuengener/Claire_de_Binare/issues/3913) / [`docs/design/arvp_gearbox_design_contracts_3913.md`](../design/arvp_gearbox_design_contracts_3913.md)  
Live-Readiness: **NO-GO**  
Echtgeld: **not authorized**

**Alignment verdict:** `PASS_DESIGN_ALIGNMENT` — parallel pilot maps to two declared
gears with advisory-only selector posture and Protective Idle semantics documented.

This document satisfies gearbox alignment review gate #5 from
[`arvp_gearbox_design_contracts_3913.md`](../design/arvp_gearbox_design_contracts_3913.md) §9.

---

## 1. Scope

| In scope | Out of scope |
|----------|--------------|
| Map PB1 + Donchian parallel lanes to `strategy_gear_registry.v1` | Implement selector service |
| Document advisory-only / no-trade-approval posture | Unpark #205 |
| Define Protective Idle interpretation per lane | Live/Echtgeld authorization |

---

## 2. Gear registry mapping

### Gear A — Primary Breakout (PB1)

| Field | Value |
|-------|-------|
| `gear_id` | `gear-primary-breakout-v1-parallel-btcusdt` |
| `strategy_id` | `primary_breakout_v1` |
| `bot_id` | `np-pb1-parallel-01` |
| `runtime_readiness` | `runtime` |
| `lifecycle_state` | `ELIGIBLE` (paper observation) |
| `compose_service` | `cdb_signal_pb1` (port 8015) |
| `allocation_profile` | `ALLOCATION_RULES_JSON:primary_breakout_v1` |

### Gear B — Donchian Breakout

| Field | Value |
|-------|-------|
| `gear_id` | `gear-donchian-breakout-v1-parallel-btcusdt` |
| `strategy_id` | `donchian_breakout_v1` |
| `bot_id` | `np-donchian-parallel-01` |
| `runtime_readiness` | `runtime` |
| `lifecycle_state` | `ELIGIBLE` (paper observation) |
| `compose_service` | `cdb_signal_donchian` (port 8016) |
| `allocation_profile` | `ALLOCATION_RULES_JSON:donchian_breakout_v1` (half-cap map) |

Both gears publish to shared Redis bus (`signals` / `stream.signals`). Risk routes by
payload `strategy_id` / `bot_id`. Evidence export **must** use qualified filters
(`strategy_id`, `bot_id`, `config_hash`) per #3911 guards.

---

## 3. Selector posture (advisory-only)

Parallel pilot **does not** implement `selector_decision.v1` runtime selection.

| Contract field | Pilot posture |
|----------------|---------------|
| `no_trade_approval` | **true** — each gear emits signals independently; risk gate decides |
| `selected_gear` | **null** at gearbox layer — both gears run concurrently by design |
| `protective_idle_allowed` | **true** — RC_001 / allocation=0 periods are valid per-lane idle |
| Learning vs Trading loop | Observation-only; no selector output authorizes orders |

This is infrastructure parallel observation, not portfolio selector activation (#205
remains parked).

---

## 4. Protective Idle semantics (#3912 evidence)

Per [`protective_idle.v1`](../contracts/protective_idle.v1.schema.json) and gearbox
doctrine:

| Condition | Lane behavior | Pilot classification |
|-----------|---------------|----------------------|
| `HIGH_VOL_CHAOTIC` + RC_001 | Signals emitted, risk blocks | **Protective Idle** — not pilot failure |
| `allocation_pct <= 0` | No orders | **Protective Idle** |
| Zero signals in window | No activity | **Idle** — document per lane |
| Campaign-scoped chain found | Paper order path | **Evidence event** — per-lane verdict |

Evidence doc for #3912 must report per-strategy outcomes separately. A lane in
Protective Idle while the sibling lane shows activity is **expected** under shared
capital pool + regime constraints.

---

## 5. Prerequisites cross-check

| Prerequisite | Status | Evidence |
|--------------|--------|----------|
| #3909 parallel compose | DONE | `config/arvp/runtime_np_parallel_signal_compose_override.yml` |
| #3910 Donchian allocation | DONE | `config/arvp/runtime_np_parallel_allocation_compose_override.yml` |
| #3911 ledger isolation | DONE | PR #3941 @ `0f273b15` |
| #3913 gearbox contracts | DONE | `docs/design/arvp_gearbox_design_contracts_3913.md` |
| #3893 scheduling | DONE | CLOSED `TIMEOUT_NO_CHAIN`; stack baseline restored |
| Alignment review (this doc) | DONE | this file |
| RUNTIME-GO on #3912 | **PENDING** | Human gate — Jannek |

---

## 6. Boundaries

- LR **NO-GO** — no Live/Echtgeld authorization from this alignment review
- Board stage `trade-capable` ≠ strategy validation or parallel paper GO
- This document does **not** authorize Docker start or campaign execution

---

*Alignment review recorded 2026-07-09 on `main`.*
