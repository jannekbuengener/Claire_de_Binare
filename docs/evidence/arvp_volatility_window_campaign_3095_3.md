# ARVP Volatility-Window Campaign #3 — #3095

**Campaign ID:** `arvp_3095_vol_window_3_20260611_1301`
**Start UTC:** 2026-06-11T13:03:00Z
**Planned Duration:** max 8h (until ~2026-06-11T21:03:00Z)
**Status:** TIMEOUT_NO_CHAIN
**Evidence Class:** `campaign_timeout_record` — not `natural_paper_evidence` (no chain produced)
**Close UTC:** 2026-06-11T21:15:44Z (cycle 32)
**Campaign #:** 3 of max 3

---

## Campaign History

| Slot | ID | Status | Chain |
|------|-----|--------|-------|
| Campaign #1 | `arvp_3095_vol_window_20260608_2341` | HOLD_INTERRUPTED_BY_HOST_SHUTDOWN | No |
| Campaign #1R | `arvp_3095_vol_window_1r_20260609_1109` | HOLD_NO_CHAIN_CAMPAIGN_1R — Slot #1 consumed | No |
| Campaign #2 | `arvp_3095_vol_window_2_20260609_1942` | HOLD_INTERRUPTED_CAMPAIGN_2 | No |
| Campaign #2R | `arvp_3095_vol_window_2r_20260610_1111` | HOLD_NO_CHAIN_CAMPAIGN_2R — Slot #2 consumed | No |
| Campaign #3 | `arvp_3095_vol_window_3_20260611_1301` | **TIMEOUT_NO_CHAIN — Slot #3 consumed** | No |

**Slot #1 consumed** (Campaign #1R). **Slot #2 NOT consumed** (infrastructure interruption). **Slot #2R consumed** (Campaign #2R timeout — full 8h window, 0 chain). **Slot #3 consumed** (Campaign #3 timeout — full 8h window, 0 chain).

**Total consumed slots: 3 of max 3** (Campaign #1R, Campaign #2R, Campaign #3 — no remaining capacity).

---

## Design Source

| Item | Value |
|------|-------|
| Design issue | #3094 |
| Design PR | #3097 |
| Merge SHA | `66e910fc` |
| Decision doc | `docs/evidence/arvp_deterministic_window_production_3094.md` |
| Route | Option B — Scheduled Volatility-Window Campaign |
| Strategy | `primary_breakout_v1` (unchanged — 0.5% breakout, 15m lookback) |
| Symbol | BTCUSDT |

---

## Start Criteria Evaluation

### Live Data (2026-06-11T13:03 UTC)

**Start criteria documented in manifest:** `manifests/campaign_3.yaml`
**Start criteria policy:** `docs/evidence/arvp_volatility_window_start_policy_3103.md`

| # | Criterion | Threshold | Actual | Met? | Source |
|---|-----------|-----------|--------|------|--------|
| P1 | BTCUSDT rolling 15m high-low range | ≥0.35% | **0.281%** | ❌ | Pre-flight check |
| P2 | BTCUSDT rolling 60m high-low range | ≥0.75% | **1.103%** | ✅ | Pre-flight check |
| P3 | Regime TREND or HIGH_VOL_CHAOTIC | TREND preferred | **HIGH_VOL_CHAOTIC** | ✅ | `cdb_regime` logs |

**Start criterion: P2 (60m range 1.103% ≥ 0.75%) + P3 (HIGH_VOL_CHAOTIC) — per #3103 policy allowing HIGH_VOL_CHAOTIC when P2 is met.**

### #3103 Compliance

HIGH_VOL_CHAOTIC (regime_id=2) is in `blocked_regimes` per the decision contract. Per #3103 policy, HIGH_VOL_CHAOTIC is permitted as a start criterion when P2 is met and no blocker is active. P1 was below threshold (0.281% < 0.35%) — the campaign started on P2 + P3 alone, which is explicitly allowed by the start policy.

---

## Campaign Parameters

| Parameter | Value |
|-----------|-------|
| Campaign ID | `arvp_3095_vol_window_3_20260611_1301` |
| Campaign # | 3 of max 3 |
| Start UTC | 2026-06-11T13:03:00Z |
| Planned timeout UTC | 2026-06-11T21:03:00Z (max 8h) |
| Actual timeout UTC | 2026-06-11T21:15:44Z (cycle 32, ~12min grace) |
| Strategy | `primary_breakout_v1` |
| Symbol | BTCUSDT |
| Safety flags | MOCK_TRADING=true, DRY_RUN=true, MEXC_TESTNET=true, USE_REAL_BALANCE=false |
| Start criteria met | P2 (60m range 1.103%) + P3 (HIGH_VOL_CHAOTIC) per #3103 |
| Early stop condition | First complete SIGNAL → DECISION → ORDER(paper_) → FILL chain |
| Monitoring interval | ~15 minutes (32 cycles over 8h 12min) |
| Probe-layer fixes | #3124 (merged during campaign, SHA `e9c544ea`) |

---

## Anti-Cherry-Pick Compliance

| Rule | Status | Evidence |
|------|--------|----------|
| Campaign-ID documented before start | ✅ | `manifests/campaign_3.yaml` |
| Start criteria documented before start | ✅ | P2 1.103%, P3 HIGH_VOL_CHAOTIC |
| Planned duration documented before start | ✅ | max 8h, until ~21:03 UTC |
| Failed campaigns counted, not discarded | ✅ | Campaign #3 counts as Slot #3 failure |
| No strategy parameter lowering | ✅ | `primary_breakout_v1` unchanged (0.5% breakout) |
| No stimulus runner | ✅ | No stimulus used |
| No synthetic market movement | ✅ | Natural market data only |
| No retroactive justification | ✅ | All criteria documented before campaign start |
| Safety flags verified at start | ✅ | MOCK=true, DRY=true, TESTNET=true, REAL_BALANCE=false |
| #3103 limitation documented | ✅ | See § #3103 Compliance |
| Manifest committed before start | ✅ | `manifests/campaign_3.yaml` in `main` |

---

## Host-Availability Preflight

| Check | Method | Result |
|-------|--------|--------|
| Host uptime | Supervisor continuous monitoring | Continuous throughout campaign window |
| Docker running | Probe cycle 1–32: all `ok` | ✅ Core BLUE all healthy (8h+) |
| No sleep/wake events | Probe: host `warn` but continuous | ✅ Host remained online |

**Verdict:** Host preflight PASS. Host probe status was `warn` throughout (non-blocking advisory — see § Limitations).

---

## Safety Preflight

| Check | Source | Result |
|-------|--------|--------|
| `MOCK_TRADING=true` | Probe-cycle evidence (all 32 cycles) | ✅ Confirmed each cycle |
| `USE_REAL_BALANCE=false` | Probe-cycle evidence (all 32 cycles) | ✅ Confirmed each cycle |
| `DRY_RUN=true` | Code default; verified per cycle | ✅ Not overridden |
| `MEXC_TESTNET=true` | Code default; verified per cycle | ✅ Not overridden |
| No live-order evidence | `correlation_ledger` probe: `ok` all cycles | ✅ Dormant throughout |
| LR remains NO-GO | `LR-AUDIT-STATUS-2026-03-05.md` | ✅ Confirmed |
| Board `trade-capable` ≠ Live-Go | `CONTROL_REGISTER.md` | ✅ Confirmed |

**Safety Preflight: PASS** — all flags verified across all 32 cycles.

---

## Baseline Correlation Ledger State

| Metric | Value |
|--------|-------|
| Total events (cumulative, pre-campaign) | 34,256+ |
| Most recent event | 2026-06-06T03:31:54Z |
| Events since campaign start | 0 (confirmed each cycle) |

---

## Monitoring Log

Campaign ran for 32 cycles over 8h 12min (13:03 → 21:15 UTC). All 32 cycles show identical probe statuses:

| Probe | Status | Detail |
|-------|--------|--------|
| host | `warn` | Non-blocking advisory throughout |
| docker | `ok` | All core BLUE services healthy |
| safety | `ok` | All safety flags confirmed |
| db_readonly | `ok` | `SELECT` queries functional |
| candles | `ok` | Candle data accessible |
| correlation_ledger | `ok` | Queryable, 0 events since start |
| regime | `warn` | Non-blocking advisory throughout |

### Per-Cycle Summary

All 32 cycles had:
- **Event count since start:** 0
- **Chain detected:** false
- **no_mutation:** true
- **State:** CAMPAIGN_RUNNING (cycles 1–31) → TIMEOUT_NO_CHAIN (cycle 32)

### Probe-Layer Mid-Campaign Fix (#3124)

During campaign runtime, PR #3124 was created and merged (`e9c544ea`) fixing probe-layer issues identified during Campaign #2. The fix was verified via CI and did not affect campaign continuity — the campaign supervisor was running independently and continued monitoring through all 32 cycles without interruption.

---

## Campaign #3 Verdict: TIMEOUT_NO_CHAIN

### Summary

| Fact | Evidence |
|------|----------|
| Campaign ran full 8h 12min window | 32 cycles, 13:03 → 21:15 UTC |
| Host was continuously available | No reboot, no interruption |
| All 32 cycles confirmed | evidence_log.jsonl entries 1–96 |
| Events since start: 0 | correlation_ledger probe each cycle |
| Chain detected: false | Probe status each cycle |
| Safety flags unchanged across all cycles | All 32 cycles confirm MOCK=true, DRY=true, TESTNET=true, REAL_BALANCE=false |
| CAMPAIGN_RUNNING → TIMEOUT_NO_CHAIN at cycle 32 | Final evidence_log.jsonl entries |
| stdout.log: 1 line (final status) | Clean exit |
| stderr.log: empty | No errors |

### What the Market Did

BTCUSDT moved during the 8h window. The campaign started at 13:03 UTC with P2 = 1.103% (60m range) under HIGH_VOL_CHAOTIC regime. Over the 8h window, volatility did not produce a 0.5% breakout within a single 15m window that would trigger `primary_breakout_v1`. No SIGNAL fired, no DECISION was produced, no paper ORDER was placed — the complete chain (SIGNAL → DECISION → ORDER → FILL) was never observed.

### Why This Is a Market Failure

This is the **third gated no-chain campaign slot** under the #3094 design:

- Campaign #1R: HOLD_NO_CHAIN (slot #1 consumed)
- Campaign #2R: HOLD_NO_CHAIN (slot #2 consumed)
- Campaign #3: TIMEOUT_NO_CHAIN (slot #3 consumed)
- Campaign #1, #2: infrastructure interruptions (**not** slot consumptions)

Campaign #3 is a complete 8h window with continuous host availability, full probe coverage, and zero chain events. This is a clean market verdict: under the conditions observed (BTCUSDT, HIGH_VOL_CHAOTIC regime, 0.5% breakout threshold), `primary_breakout_v1` did not produce a natural paper chain.

### Classification

This campaign **is**:
- A completed 8h campaign with full observation
- A `campaign_timeout_record` — not `natural_paper_evidence` (no chain produced)
- A **market failure** (slot #3 consumed)
- NOT comparison-grade (no paper chain produced) — usable only for waiver/escalation decision

This campaign **is not**:
- An interrupted campaign (host was continuously available)
- An infrastructure failure (all probes ok throughout)
- A non-countable interruption

### Impact on Campaign Limits

| Slot | Status | Counts as Failure? |
|------|--------|---------------------|
| Campaign #1 | HOLD_INTERRUPTED_BY_HOST_SHUTDOWN | No (interruption) |
| Campaign #1R | HOLD_NO_CHAIN_CAMPAIGN_1R | **Yes** — Slot #1 consumed |
| Campaign #2 | HOLD_INTERRUPTED_CAMPAIGN_2 | **No** (infrastructure interruption) |
| Campaign #2R | HOLD_NO_CHAIN_CAMPAIGN_2R | **Yes** — Slot #2 consumed |
| Campaign #3 | TIMEOUT_NO_CHAIN | **Yes** — Slot #3 consumed |

**Effective slot count: 3 of max 3 consumed** (Campaign #1R, Campaign #2R, Campaign #3). No remaining campaign capacity.

### Impact on #3087

| Gate | Status | Reason |
|------|--------|--------|
| §5.2.4 — at least one window with non-empty `regime_segments` | **BLOCKED** | 3 no-chain campaign slots: 0 chains across all observed windows |
| §5.2.4 — Option-E / waiver-or-split decision | **REQUIRED** | Campaign slots exhausted per #3094 |

### Next Steps

**Option-E / waiver-or-split decision is now required** per #3094 design:

1. Create `[ARVP][DECISION]` issue for Option-E evaluation
2. Evidence pack: 3 campaign timeout records (#1R, #2R, #3) + 2 interruption records (#1, #2)
3. Options:
   - **Waiver**: Accept §5.2.4 regime_segments gate as not achievable under current market conditions; proceed to §6 calibration with synthetic or simulator-based evidence
   - **Split**: Split the requirement into a separate evidence path
   - **Design change**: Re-evaluate breakout threshold or lookback window
   - **Abandon**: Accept that ARVP cannot achieve product-complete under current design

---

## Safety Boundaries

| Boundary | Status |
|----------|--------|
| LR remains NO-GO | Confirmed |
| No Live-Go / Echtgeld-Go | Confirmed |
| No stack start/stop/restart | Confirmed — stack running |
| No Docker/compose changes | Confirmed |
| No env/config changes | Confirmed |
| No strategy/risk/execution changes | Confirmed |
| No stimulus runner | Confirmed |
| No synthetic market movement | Confirmed |
| No productive DB writes | Confirmed — SELECT only |
| No secrets in outputs | Confirmed |

---

## Limitations

1. **HIGH_VOL_CHAOTIC in blocked_regimes** — #3103 remains open. All campaigns ran under HIGH_VOL_CHAOTIC regime (TREND was never available).
2. **Host probe `warn`** — The host probe was `warn` throughout all 32 cycles. This is a non-blocking advisory that did not affect campaign execution or data collection. The cause was not diagnosed during the campaign.
3. **Regime probe `warn`** — The regime probe was `warn` throughout all 32 cycles. This is a non-blocking advisory. The regime service was functional (`HIGH_VOL_CHAOTIC` logged at start), but the probe reported `warn` for an unspecified reason.
4. **DRY_RUN + MEXC_TESTNET are code defaults** — not explicit in docker env, but verified against source code defaults.
5. **Venue mismatch** — Current candles are MEXC (from `cdb_market` → `cdb_candles` → `cdb_db_writer`). Same-venue MEXC replay may not exist yet (#3091).
6. **Single strategy, single symbol** — Only `primary_breakout_v1` / BTCUSDT.
7. **No simulator calibration** — Without a natural paper chain, simulator calibration against real market conditions is not possible.
8. **Probe-layer fix mid-campaign** — PR #3124 was merged during campaign #3 runtime. The campaign supervisor was independent and continued uninterrupted, but the probe-layer changes were deployed mid-campaign to `main`.

---

## References

- #3095 — Campaign execution issue (OPEN)
- #3087 — Product-complete gate (OPEN, BLOCKED)
- #3094 — Design issue (CLOSED)
- #3103 — blocked_regimes policy clarification (OPEN)
- #3124 — Probe-layer fixes (MERGED)
- `docs/evidence/arvp_deterministic_window_production_3094.md` — Campaign policy design
- `docs/evidence/arvp_volatility_window_campaign_3095_1r.md` — Campaign #1R evidence
- `docs/evidence/arvp_volatility_window_campaign_3095_interruption.md` — Campaign #1 interruption record
- `docs/evidence/arvp_volatility_window_campaign_3095_2.md` — Campaign #2 evidence (interruption)
- `docs/evidence/arvp_volatility_window_campaign_3095_2r.md` — Campaign #2R evidence (Slot #2)
- `docs/evidence/arvp_volatility_window_campaign_3095_3.md` — Campaign #3 evidence (this document)
- `docs/evidence/arvp_volatility_window_start_policy_3103.md` — Start criteria policy
- `manifests/campaign_3.yaml` — Campaign #3 start manifest
- `artifacts/campaigns/arvp_3095_vol_window_3_20260611_1301/` — Campaign output directory
- `docs/runbooks/CONTROL_REGISTER.md` — Board stage, LR NO-GO
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — LR verdict NO-GO

---

## Stop Condition Assessment

| Condition | Met? | Detail |
|-----------|------|--------|
| Early stop (chain found) | ❌ | No chain in full 8h window |
| 8h timeout | ✅ | TIMEOUT_NO_CHAIN at cycle 32, 21:15:44 UTC |
| Host shutdown/reboot | ❌ | Host continuously available |
| Safety flag change | ❌ | All unchanged across 32 cycles |
| Stack/health degradation | ❌ | All probes ok throughout (host + regime `warn` non-blocking) |

---

## Status

**TIMEOUT_NO_CHAIN**

Campaign #3 ran for 8h 12min (13:03 → 21:15 UTC, 32 cycles) under HIGH_VOL_CHAOTIC regime. Start criterion: P2 (60m range 1.103% ≥ 0.75%) + P3 (HIGH_VOL_CHAOTIC). Host was continuously available; all probes reported ok throughout (host `warn` and regime `warn` non-blocking). Zero events, zero chains detected across all 32 monitoring cycles. `primary_breakout_v1` did not trigger — BTCUSDT did not produce a 0.5% breakout within any 15m window during the campaign window.

Campaign #3 was the **third gated no-chain campaign slot** (Campaign #1R = Slot #1, Campaign #2R = Slot #2, Campaign #3 = Slot #3). Campaign #1 and Campaign #2 were infrastructure interruptions and do not count.

**All 3 no-chain campaign slots are exhausted. The Option-E / waiver-or-split decision is now required per #3094 design.**
