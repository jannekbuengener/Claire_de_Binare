# ARVP Multi-Strategy Parallel Natural-Paper Feasibility (#3894)

Status Class: **DESIGN_ONLY** — feasibility assessed; **no runtime execution claim**
Issue: [#3894](https://github.com/jannekbuengener/Claire_de_Binare/issues/3894)
Parent: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
Related (out of scope, stays open): [#3893](https://github.com/jannekbuengener/Claire_de_Binare/issues/3893) (24h Donchian single-strategy observation)
Prior art: [#3792](https://github.com/jannekbuengener/Claire_de_Binare/issues/3792) (closed, `TIMEOUT_NO_CHAIN`), `manifests/runtime_3792_signal_compose_override.yml`
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**

---

## 1. Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
context_tool_status: available
context_trust_level: none
records_found: none

tools_or_queries:
  - MCP: cdb_context_briefing (briefing_id d653b883047c503f; operator_trust_level LOW; no enrichment records)
  - read: AGENTS.md, agents/AGENTS.md (Read Order)
  - read: infrastructure/compose/compose.red.yml, compose.blue.yml
  - read: manifests/runtime_3792_signal_compose_override.yml
  - read: services/signal/config.py, services/signal/service.py
  - read: services/risk/config.py, services/risk/service.py
  - read: services/allocation/config.py, compose.blue.yml ALLOCATION_RULES_JSON
  - read: infrastructure/database/migrations/006_correlation_phase8c.sql
  - read: services/validation/strategy_replay_runner.py, paper_reference_window_runner.py
  - read: tests/fixtures/arvp/scenario_pack_matrix_v1.json
  - read: tests/unit/arvp/* (window qualification, campaign supervisor, calibration gate)
  - read: docs/evidence/arvp_natural_paper_window_bank_readonly_feasibility_3742.md (template)
  - bash: git fetch/status/rev-parse; rg across services/core/tools/infrastructure/tests/docs
  - gh: issue view 3894/3893/1900/3792; pr list --state open; issue search (dedupe)

records_or_results:
  - HEAD == origin/main == 223578877a1d72f8a4cb7715314becb6a148f2d6
  - #3894 OPEN; #3893 OPEN (untouched); #1900 OPEN; #3792 CLOSED
  - open PRs: #3755 only (Dependabot Grafana — out of scope)
  - compose.red.yml: exactly one cdb_signal service (container_name cdb_signal, port 8005)
  - ALLOCATION_RULES_JSON: primary_breakout_v1 + paper only; no donchian_breakout_v1
  - MCP briefing: no DB-backed evidence records; repo-only fallback required

repo_crosscheck:
  - infrastructure/compose/compose.red.yml:51-91 (single cdb_signal)
  - services/signal/config.py:94-96 (shared output_topic signals, stream.signals)
  - services/risk/config.py:43-44 (shared input_topic signals)
  - compose.blue.yml:186 (ALLOCATION_RULES_JSON)
  - services/signal/service.py:234-235,341,375 (runtime: PB1 + Donchian only)
  - services/validation/strategy_replay_runner.py:628+ (replay dispatch for 5 strategies)
  - manifests/runtime_3792_signal_compose_override.yml (single-strategy swap pattern)

impact_on_plan:
  - Parallel multi-strategy natural-paper is architecturally plausible but not safe today without compose/ID/allocation/ledger isolation work
  - Smallest pilot must stay 2-strategy, shared-symbol (BTCUSDT), distinct bot_id, and sequential compose evolution — not ad-hoc parallel start
  - #3893 remains the active single-strategy Donchian execute lane; this design does not supersede it

limitations:
  - No Docker/runtime execution in this slice
  - No live Redis/Postgres queries
  - No DB-backed brain claims
  - Exposure/allocation interaction under true parallel load not empirically validated
```

---

## 2. Executive Verdict

| Dimension | Verdict |
|-----------|---------|
| **Parallel feasibility (design)** | **CONDITIONAL YES** — requires bounded follow-up slices before any RUNTIME-GO |
| **Current repo readiness** | **NO-GO** for parallel natural-paper execution |
| **Runtime-ready strategies (2)** | `primary_breakout_v1`, `donchian_breakout_v1` |
| **Replay-only strategies (3)** | `breakout_trend_filter_v1`, `range_mean_reversion_v1`, `momentum_capture_v1` |
| **Smallest safe pilot** | 2-strategy parallel observation: PB1 + Donchian, distinct `SIGNAL_BOT_ID`, compose multi-service profile, Donchian allocation rules, campaign-scoped evidence paths — **after** isolation follow-ups land |
| **LR / Live / Echtgeld** | **NO-GO unchanged** |

---

## 3. Bootloader / Read-Order Evidence

Canonical Read Order resolved per `agents/AGENTS.md`:

1. `knowledge/governance/CDB_CONSTITUTION.md`
2. `knowledge/governance/CDB_GOVERNANCE.md`
3. `knowledge/governance/CDB_AGENT_POLICY.md`
4. `knowledge/governance/SYSTEM_INVARIANTS.md`
5. `knowledge/CDB_KNOWLEDGE_HUB.md`
6. `docs/meta/WORKING_REPO_CANON.md`
7. `CURRENT_STATUS.md`
8. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
9. `docs/runbooks/CONTROL_REGISTER.md`

Context Brain preflight attempted (`cdb_context_briefing`); no usable DB records → repo-only audit.

---

## 4. Live GitHub / Repo State

| Item | State |
|------|-------|
| Base commit | `223578877a1d72f8a4cb7715314becb6a148f2d6` (`origin/main`) |
| #3894 | OPEN — this design slice |
| #3893 | OPEN — 24h Donchian natural-paper execute; **operatively untouched** |
| #1900 | OPEN — ARVP epic parent |
| #3792 | CLOSED — prior Donchian observation (`TIMEOUT_NO_CHAIN`) |
| #205 | OPEN — broader multi-strategy gearbox (orthogonal, not a duplicate) |
| Open PRs | #3755 (Grafana bump — out of scope) |

---

## 5. Repo Audit Summary

### 5.1 Compose / `cdb_signal` surface

- **One** `cdb_signal` service in `infrastructure/compose/compose.red.yml` with fixed `container_name: cdb_signal` and host port `8005`.
- Strategy selection is **env-swap**, not multi-instance: `SIGNAL_STRATEGY_ID` (default `primary_breakout_v1`), `SIGNAL_BOT_ID` (default empty).
- Prior campaign pattern: `manifests/runtime_3792_signal_compose_override.yml` swaps a **single** running instance to `donchian_breakout_v1` — proves single-strategy override works; does **not** prove parallel instances.

### 5.2 Messaging / streams (shared bus)

| Path | Default key | Isolation today |
|------|-------------|-----------------|
| Signal pub/sub out | `signals` | **Shared** — all publishers use same topic |
| Signal stream | `stream.signals` | **Shared** |
| Risk orders | `stream.orders` | **Shared** |
| Fills | `stream.fills` | **Shared** |
| Allocation decisions | `stream.allocation_decisions` | **Shared** (per-strategy payloads) |

Risk subscribes to the global `signals` topic (`services/risk/config.py`). Multiple `cdb_signal` instances would **multiplex** into one consumer unless topics/streams are partitioned.

### 5.3 `correlation_ledger`

- Schema (`006_correlation_phase8c.sql`): no `strategy_id` / `bot_id` columns; identity lives in `payload JSONB` (signal `to_dict()` includes both).
- `paper_reference_window_runner.py` supports `strategy_id`, optional `bot_id`, optional `config_hash` filters for extraction.
- Campaign supervisor probes count ledger events since campaign start but do not enforce per-strategy table partitioning.

### 5.4 Allocation / risk per strategy

- `cdb_allocation` rules from `ALLOCATION_RULES_JSON` in `compose.blue.yml`: entries for `paper` and `primary_breakout_v1` only.
- **`donchian_breakout_v1` has no allocation rule** → `_allocation_allowed()` returns blocked (`allocation_pct <= 0`) even if signals were emitted.
- Risk maintains `allocation_state: dict[str, AllocationState]` keyed by `strategy_id` — multi-strategy **logic exists**, config does not.
- Exposure limits (`check_exposure_limit`) are **portfolio-global**, not per-strategy — parallel strategies share one capital envelope.

### 5.5 Campaign / evidence / logs

- Campaign manifests (`tools/arvp_campaign_supervisor.py`) carry `campaign_id`, `strategy_id`; one campaign ↔ one strategy in fixtures.
- Evidence docs land under `docs/evidence/` with issue-scoped names; no enforced per-strategy subdirectory convention.
- Compose mounts shared `../../logs:/app/logs` — log filenames are service-default, not bot-scoped.

### 5.6 Tests / guards (ledger-evidence mixing)

| Guard | Coverage | Gap |
|-------|----------|-----|
| `test_arvp_window_qualification_contract.py` | Fixture-based `strategy_id`/`bot_id` in paper-reference extraction | Single-strategy fixtures only |
| `test_arvp_calibration_gate_regression_contract.py` | `mixed_signals` drift note (replay calibration semantics) | Not runtime ledger isolation |
| `test_arvp_campaign_supervisor_state_machine_contract.py` | `correlation_ledger` probe in campaign manifest | No cross-strategy contamination assertion |
| `test_arvp_runtime_negative_controls_contract.py` | Runtime negative controls | No parallel-publish scenario |
| Scenario pack matrix (`scenario_pack_matrix_v1.json`) | Maps 5 strategy IDs to replay adapters | Replay-only for 3/5 |

**No test today asserts that parallel runtime publishers cannot contaminate each other's ledger windows or paper-reference extracts.**

### 5.7 Runtime vs replay inventory

| `strategy_id` | Runtime (`services/signal/service.py`) | Replay (`strategy_replay_runner.py`) |
|---------------|----------------------------------------|-------------------------------------|
| `primary_breakout_v1` | ✅ bar-based breakout path | ✅ |
| `donchian_breakout_v1` | ✅ Donchian channel path (#3789) | ✅ |
| `breakout_trend_filter_v1` | ❌ | ✅ |
| `range_mean_reversion_v1` | ❌ | ✅ |
| `momentum_capture_v1` | ❌ | ✅ |

---

## 6. Answers to #3894 Required Questions

### Q1 — Can each strategy run on its own `cdb_signal` instance?

**Design: yes; repo today: no.**

Docker Compose can host multiple build-identical services (e.g. `cdb_signal_pb1`, `cdb_signal_donchian`) with distinct `container_name`, `SIGNAL_PORT`, `SIGNAL_STRATEGY_ID`, and `SIGNAL_BOT_ID`. The canonical `compose.red.yml` defines only one instance. Extending via compose `profiles` or a campaign override manifest is the smallest infra path — not yet authored for parallel layout.

### Q2 — How are `strategy_id` and `bot_id` kept unique per instance?

Per instance:

- `strategy_id` ← `SIGNAL_STRATEGY_ID` env (`services/signal/config.py`)
- `bot_id` ← `SIGNAL_BOT_ID` env (optional; **often empty in default compose**)

Signals embed both in Redis payload and `correlation_ledger.payload`. Uniqueness is **operational convention**, not enforced by compose or DB constraints. **Gap:** empty `SIGNAL_BOT_ID` collapses bot identity; parallel pilot must mandate non-empty, distinct bot IDs (e.g. `np-pb1-01`, `np-donchian-01`).

### Q3 — How are Redis streams, `correlation_ledger`, orders/fills, and evidence separated per strategy?

| Layer | Separation mechanism | Adequate for parallel? |
|-------|---------------------|------------------------|
| Redis pub/sub | None (shared `signals`) | **No** without topic partitioning or risk-side filtering |
| Redis streams | Payload fields `strategy_id`/`bot_id` | **Partial** — consumer must filter |
| `correlation_ledger` | `payload` JSONB | **Partial** — query/filter at extract time |
| Orders/fills | `strategy_id`/`bot_id` on order models | **Partial** — shared execution path |
| Evidence files | Naming convention only | **No** enforced isolation |

`paper_reference_window_runner.py` can extract per `strategy_id` + `bot_id` **if** those fields are set consistently at signal time.

### Q4 — Which risk/allocation rules are missing per non-PB1 strategy (especially `donchian_breakout_v1`)?

`ALLOCATION_RULES_JSON` in `compose.blue.yml` includes `primary_breakout_v1` regime map but **not** `donchian_breakout_v1`. Without a rule entry, allocation service never emits positive `allocation_pct` for Donchian → risk blocks all Donchian signals (`_allocation_allowed` → `allocation_pct <= 0`).

**Required before Donchian parallel paper:** add `donchian_breakout_v1` block to `ALLOCATION_RULES_JSON` (or campaign-scoped compose override of the same), with explicit regime percentages and documented capital-budget split vs PB1.

### Q5 — How are campaign IDs, logs, and artifacts separated?

- **Campaign ID:** manifest field (`campaign_id`); supervisor ties probes to one campaign. Parallel strategies need **distinct campaign manifests** (e.g. `HYP-NP-PB1-01`, `HYP-NP-DONCHIAN-02`) — pattern exists from #3792 override, not generalized.
- **Logs:** shared host `logs/` mount — separation requires per-service log config or subdirectories (not present).
- **Artifacts:** `docs/evidence/arvp_*_<issue>.md` convention; recommend `docs/evidence/arvp_<campaign_id>_<state>.md` for parallel pilots.

### Q6 — Which tests/guards prevent ledger/evidence mixing?

See §5.6. **Summary:** contract tests cover single-strategy qualification, calibration drift semantics, and campaign probe wiring. **No guard** prevents or detects cross-strategy ledger mixing under parallel runtime publish. Follow-up: fixture + unit contract for multi-publisher `correlation_ledger` extract boundaries.

### Q7 — Runtime-ready vs replay-only?

See §5.7 table. Only **two** strategies are runtime-capable today. Parallel natural-paper pilot candidates are limited to PB1 + Donchian unless runtime adapters are built for Pack-A replay-only variants (out of #3894 scope).

### Q8 — What is the smallest safe parallel-paper pilot?

**Pilot hypothesis:** `HYP-NP-PARALLEL-2S-01` — observe `primary_breakout_v1` and `donchian_breakout_v1` in parallel on BTCUSDT natural paper for a bounded window (e.g. 8–24h), with distinct bot IDs and separate campaign manifests.

**Preconditions (must land first):**

1. Compose profile: two `cdb_signal` services OR topic-partitioned outputs (see follow-ups).
2. `ALLOCATION_RULES_JSON` includes `donchian_breakout_v1` with conservative caps.
3. Mandatory non-empty `SIGNAL_BOT_ID` per instance.
4. Campaign manifests + evidence naming per strategy.
5. Guard test: paper-reference extract returns zero cross-strategy rows for mixed ledger fixture.

**Explicit pilot bounds:**

- Symbol: BTCUSDT only (both runtime strategies require it).
- Shared risk/execution — treat as **one capital pool**; cap per-strategy allocation so combined exposure stays within existing `MAX_TOTAL_EXPOSURE_PCT`.
- `MOCK_TRADING=true` / paper path only.
- **No** third strategy, **no** replay-only strategies, **no** Live/Echtgeld.
- **Does not** start while #3893 single-strategy Donchian window is active unless explicitly coordinated (separate RUNTIME-GO).

---

## 7. Gap List

| ID | Severity | Gap | Follow-up recommendation |
|----|----------|-----|--------------------------|
| G1 | **BLOCKER** | Single `cdb_signal` in canonical compose | Compose multi-instance profile for parallel signal services |
| G2 | **BLOCKER** | `donchian_breakout_v1` missing from `ALLOCATION_RULES_JSON` | Add allocation rules + compose override for Donchian paper |
| G3 | **HIGH** | Shared Redis `signals` topic — no publisher isolation | Topic/stream env overrides per signal instance OR risk subscription filter |
| G4 | **HIGH** | `SIGNAL_BOT_ID` defaults empty | Enforce non-empty bot_id in compose profile + validation guard |
| G5 | **HIGH** | No runtime test for ledger/evidence cross-strategy contamination | Contract test + mixed-fixture guard |
| G6 | **MEDIUM** | `correlation_ledger` lacks top-level `strategy_id` index | Optional migration + extract query hardening (future) |
| G7 | **MEDIUM** | Shared `logs/` volume | Per-service log subdir or campaign-prefixed logging |
| G8 | **MEDIUM** | Portfolio-global exposure limit | Document per-strategy allocation budget for parallel pilot |
| G9 | **LOW** | Evidence path naming not campaign-scoped | Convention doc + supervisor template update |
| G10 | **INFO** | #205 multi-strategy gearbox is broader portfolio selector | Link as long-term; not blocking 2-strategy ARVP pilot |

---

## 8. Recommended Follow-Up Issues

Deduplication search (2026-07-07): no open issues match compose isolation / Donchian allocation / ledger mixing guards. Proposed slices (to be filed on merge):

| Slice | Title sketch | Blocks pilot |
|-------|--------------|--------------|
| A | `[ARVP][COMPOSE] Multi-cdb_signal parallel profile for natural-paper` | G1, G3, G4 |
| B | `[ARVP][ALLOCATION] donchian_breakout_v1 rules for natural-paper path` | G2 |
| C | `[ARVP][TEST] Ledger/evidence isolation guards for parallel strategies` | G5 |
| D | `[ARVP][WINDOW][EXECUTE] 2-strategy parallel natural-paper pilot (PB1+Donchian)` | Pilot execution (after A–C) |

**Out of scope / do not duplicate:** #3893 (single-strategy Donchian 24h), #205 (gearbox), #3755 (Dependabot).

---

## 9. Safety Boundaries / NO-GO

- LR remains **NO-GO** — no Live/Echtgeld authorization from this design.
- Board stage `trade-capable` ≠ strategy validation or parallel paper GO.
- This document does **not** authorize Docker start, parallel execution, risk-gate changes, or DB writes.
- #3893 stays **open** and must not be closed or operatively altered by #3894 delivery.
- Replay-only strategies must not be promoted to parallel runtime without separate runtime-adapter issues.
- Shared risk/execution means parallel strategies are **not** capital-isolated — pilot must use conservative per-strategy allocation caps.

---

## 10. Validation (this slice)

```bash
git diff --check
# docs-only; no pytest gate required for merge policy on this PR
```

Design claims are repo-backed only (no runtime/DB verification in this slice).

---

## 11. References

- `infrastructure/compose/compose.red.yml`
- `infrastructure/compose/compose.blue.yml` (`ALLOCATION_RULES_JSON`)
- `manifests/runtime_3792_signal_compose_override.yml`
- `services/signal/config.py`, `services/signal/service.py`
- `services/risk/service.py` (`_allocation_allowed`, exposure checks)
- `services/validation/paper_reference_window_runner.py`
- `services/validation/strategy_replay_runner.py`
- `infrastructure/database/migrations/006_correlation_phase8c.sql`
- `tests/fixtures/arvp/scenario_pack_matrix_v1.json`
- `docs/evidence/arvp_natural_paper_window_bank_readonly_feasibility_3742.md` (doc template)
