# ARVP Parallel Natural-Paper Pilot — Execute (#3912)

Status Class: **OBSERVATION_RUNNING**
Issue: [#3912](https://github.com/jannekbuengener/Claire_de_Binare/issues/3912)
Hypothesis: `HYP-NP-PARALLEL-2S-01`
Parent: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
Preflight: [`arvp_parallel_natural_paper_3912_preflight.md`](arvp_parallel_natural_paper_3912_preflight.md)
Gearbox alignment: [`arvp_parallel_pilot_gearbox_alignment_3912.md`](arvp_parallel_pilot_gearbox_alignment_3912.md)
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**

**Verdict enum:** *pending* — 12h window in progress

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

**Execute note:** `manifests/runtime_np_parallel_signal_compose_override.yml` build `context`
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

*Pending — re-run after window timeout per lane.*

Per-lane verdicts (expected enum): `CHAIN_FOUND` | `TIMEOUT_NO_CHAIN` | `INTERRUPTED` | `BLOCKED_*`

---

## 6. Boundaries

- LR **NO-GO** unchanged
- No Live/Echtgeld authorization
- No `natural_paper_evidence` promotion claim until terminal evaluation
- #3742 stays OPEN

---

*Opened at execute start 2026-07-09 on `main` @ `841d49b0`.*
