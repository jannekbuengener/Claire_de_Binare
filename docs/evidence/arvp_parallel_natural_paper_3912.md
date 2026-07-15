# ARVP Parallel Natural-Paper Pilot — Execute (#3912)

Status Class: **OBSERVATION_COMPLETE**
Issue: [#3912](https://github.com/jannekbuengener/Claire_de_Binare/issues/3912)
Hypothesis: `HYP-NP-PARALLEL-2S-01`
Parent: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
Preflight: [`arvp_parallel_natural_paper_3912_preflight.md`](arvp_parallel_natural_paper_3912_preflight.md)
Gearbox alignment: [`arvp_parallel_pilot_gearbox_alignment_3912.md`](arvp_parallel_pilot_gearbox_alignment_3912.md)
Telemetry fix: [#3955](https://github.com/jannekbuengener/Claire_de_Binare/issues/3955) / PR [#3956](https://github.com/jannekbuengener/Claire_de_Binare/pull/3956) @ `03b27a99`
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**

**Verdict enum:** `TIMEOUT_NO_CHAIN` (both lanes)

---

## 1. RUNTIME-GO

Posted on #3912 @ `2026-07-09T13:27:00Z` (comment after prep PR #3942 merge @ `841d49b0`).

---

## 2. Campaign lanes

| Lane | campaign_id | strategy_id | bot_id | Window (UTC) |
|------|-------------|-------------|--------|--------------|
| A (PB1) | `arvp_3912_np_parallel_pb1_20260709_1327` | `primary_breakout_v1` | `np-pb1-parallel-01` | `2026-07-09T13:27:00Z` → `2026-07-10T01:27:00Z` |
| B (Donchian) | `arvp_3912_np_parallel_donchian_20260709_1327` | `donchian_breakout_v1` | `np-donchian-parallel-01` | same |

---

## 3. Preflight (PASS)

| Check | Result |
|-------|--------|
| ARVP contract tests (44) | PASS |
| Compose config (parallel overrides) | PASS |
| Safety probe (`cdb_execution`) | PASS |
| `cdb_signal_pb1` health :8015 | PASS — `primary_breakout_v1` / `np-pb1-parallel-01` |
| `cdb_signal_donchian` health :8016 | PASS — `donchian_breakout_v1` / `np-donchian-parallel-01` |
| Canonical `cdb_signal` | **stopped** during parallel window |

**Execute note:** `config/arvp/runtime_np_parallel_signal_compose_override.yml` build `context`
required `../..` (not `..`) when compose base file is `infrastructure/compose/` — local fix
applied at execute time; follow-up PR recommended.

---

## 4. Supervisor start (cycle 1)

| Lane | State | Probes | events_since_start |
|------|-------|--------|-------------------|
| PB1 | `CAMPAIGN_RUNNING` | docker/safety/db ok; host/regime warn | 0 |
| Donchian | `CAMPAIGN_RUNNING` | docker/safety/db ok; host/regime warn | 0 |

Supervisors: host PIDs, poll 900s, terminal due after `2026-07-10T01:27:00Z`.

Evidence logs:
- `artifacts/campaigns/arvp_3912_np_parallel_pb1_20260709_1327/`
- `artifacts/campaigns/arvp_3912_np_parallel_donchian_20260709_1327/`

---

## 5. Terminal evaluation

**Evaluated at (UTC):** `2026-07-10T01:38:37Z` (supervisor cycle 48)

| Lane | Terminal state | Supervisor `events_since_start` | chain_detected | Actual lane activity |
|------|----------------|----------------------------------:|----------------|----------------------|
| PB1 | `TIMEOUT_NO_CHAIN` | 0 | false | 0 signals (regime-gated idle) |
| Donchian | `TIMEOUT_NO_CHAIN` | 0 | false | 50 signals emitted; 0 orders / 0 fills |

Infrastructure probes: docker/safety/db ok; host/regime warn (non-blocking).

**Stack baseline restored** post-eval: `cdb_signal` → `primary_breakout_v1`; parallel containers stopped.

No `natural_paper_evidence` promotion claim. Hypothesis `HYP-NP-PARALLEL-2S-01`: infrastructure parallel observation complete; no campaign-scoped promotable chains in either lane.

---

## 6. Root cause (terminal understanding)

### Lane outcomes

| Lane | Signals | Risk | Orders / Fills | Verdict rationale |
|------|--------:|------|----------------|-------------------|
| PB1 | 0 | — | 0 / 0 | `primary_breakout_v1` requires TREND regime; window was `HIGH_VOL_CHAOTIC` throughout |
| Donchian | 50 | 50× **RC_001** | 0 / 0 | Signals emitted but allocation gate blocked every path; no promotable chain |

`TIMEOUT_NO_CHAIN` is correct for both lanes: no SIGNAL→DECISION→ORDER→FILL chain completed in the observation window.

### Why supervisor showed `events_since_start=0` on Donchian (telemetry gap, not strategy success)

At terminal evaluation the supervisor reported `events_since_start=0` on **both** lanes. For PB1 this matched reality (0 signals). For Donchian it was **misleading**:

1. **Deterministic `signal_id` collision** — runtime IDs reused after container restart collided with prior `correlation_ledger` rows; `ON CONFLICT DO NOTHING` suppressed new inserts in the window.
2. **Global-only ledger count** — supervisor counted all ledger rows since `start_utc` without `bot_id` / `strategy_id` lane filters.

Post-run RCA and engineering fix: [#3955](https://github.com/jannekbuengener/Claire_de_Binare/issues/3955) / PR [#3956](https://github.com/jannekbuengener/Claire_de_Binare/pull/3956) @ `03b27a99`. Detail: [`arvp_3912_zero_event_telemetry_fix_3955.md`](arvp_3912_zero_event_telemetry_fix_3955.md).

Future runs will expose lane-scoped counts and collision-safe runtime signal IDs. This does **not** change the #3912 terminal verdict.

---

## 7. Boundaries

- LR **NO-GO** unchanged
- No Live/Echtgeld authorization
- No `natural_paper_evidence` promotion claim
- [#3742](https://github.com/jannekbuengener/Claire_de_Binare/issues/3742) stays OPEN

---

*Opened at execute start 2026-07-09 on `main` @ `841d49b0`. Closeout reconciled 2026-07-10 after telemetry fix #3956.*
