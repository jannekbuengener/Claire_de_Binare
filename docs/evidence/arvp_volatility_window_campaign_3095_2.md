# ARVP Volatility-Window Campaign #2 — #3095

**Campaign ID:** `arvp_3095_vol_window_2_20260609_1942`
**Start UTC:** 2026-06-09T19:42:00Z
**Planned Duration:** max 8h (until ~2026-06-10T03:42:00Z)
**Status:** HOLD_INTERRUPTED_CAMPAIGN_2
**Evidence Class:** `interruption_record` — not `natural_paper_evidence` (host reboot before timeout)
**Close UTC:** 2026-06-10T13:30:00Z (post-reboot reconciliation)
**Campaign #:** 2 of max 3

---

## Campaign History

| Slot | ID | Status | Chain |
|------|-----|--------|-------|
| Campaign #1 | `arvp_3095_vol_window_20260608_2341` | HOLD_INTERRUPTED_BY_HOST_SHUTDOWN | No |
| Campaign #1R | `arvp_3095_vol_window_1r_20260609_1109` | HOLD_NO_CHAIN_CAMPAIGN_1R — Slot #1 consumed | No |
| Campaign #2 | `arvp_3095_vol_window_2_20260609_1942` | **HOLD_INTERRUPTED_CAMPAIGN_2** | No (observed 3h 14min) |
| Campaign #3 | — | Available | — |

**Slot #1 consumed** (Campaign #1R failure). **Slot #2 interrupted — does NOT count as a market failure.**

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

### Live Data (2026-06-09T19:42 UTC)

**Candle source:** `public.candles_1m` via `docker exec cdb_postgres psql -U claire_user` (65 candles)
**Regime source:** `docker logs cdb_regime --tail 5`

| # | Criterion | Threshold | Actual | Met? | Source |
|---|-----------|-----------|--------|------|--------|
| P1 | BTCUSDT rolling 15m high-low range | ≥0.35% | **0.46%** | ✅ | 15 most recent 1m candles |
| P2 | BTCUSDT rolling 60m high-low range | ≥0.75% | ~0.73% | ❌ | 65 candles available |
| P3 | Regime TREND or HIGH_VOL_CHAOTIC | TREND preferred | **HIGH_VOL_CHAOTIC** | ✅ | `cdb_regime` logs (19:42:59 UTC) |

**Start criterion: P1 (15m range 0.46%) + P3 (HIGH_VOL_CHAOTIC)**

### Range Computation Detail

**15-minute window** (last 15 candles):
- Max high: 62050.00 (ts_ms 1781033520000)
- Min low: 61765.66 (ts_ms 1781034000000)
- Range: (62050.00 − 61765.66) ÷ 61765.66 × 100 ≈ **0.46%**

**Regime:**
```
2026-06-09 19:42:59,963 [INFO] regime_service: Regime-Signal: BTCUSDT 60s HIGH_VOL_CHAOTIC
```

### #3103 Limitation

HIGH_VOL_CHAOTIC (regime_id=2) is in `blocked_regimes` per the decision contract. A SIGNAL that fires during this regime may have its DECISION gate reject entry. Campaign #2 accepts this risk with explicit documentation. TREND is unavailable — accepting HIGH_VOL_CHAOTIC as the best available regime with P1 met as a secondary validation.

---

## Campaign Parameters

| Parameter | Value |
|-----------|-------|
| Campaign ID | `arvp_3095_vol_window_2_20260609_1942` |
| Campaign # | 2 of max 3 |
| Start UTC | 2026-06-09T19:42:00Z |
| Planned timeout UTC | ~2026-06-10T03:42:00Z (max 8h) |
| Strategy | `primary_breakout_v1` |
| Symbol | BTCUSDT |
| Safety flags | MOCK_TRADING=true, DRY_RUN=true, MEXC_TESTNET=true, USE_REAL_BALANCE=false |
| Start criteria met | P1 (15m range 0.46%) + P3 (HIGH_VOL_CHAOTIC) |
| Early stop condition | First complete SIGNAL → DECISION → ORDER(paper_) → FILL chain |
| Monitoring interval | ~20-30 minutes |

---

## Anti-Cherry-Pick Compliance

| Rule | Status | Evidence |
|------|--------|----------|
| Campaign-ID documented before start | ✅ | `arvp_3095_vol_window_2_20260609_1942` |
| Start criteria documented before start | ✅ | P1 0.46%, P3 HIGH_VOL_CHAOTIC |
| Planned duration documented before start | ✅ | max 8h, until ~2026-06-10T03:42 UTC |
| Failed campaigns counted, not discarded | ✅ | Campaign #1R counts as Slot #1 failure |
| No strategy parameter lowering | ✅ | `primary_breakout_v1` unchanged (0.5% breakout) |
| No stimulus runner | ✅ | No stimulus used |
| No synthetic market movement | ✅ | Natural market data only |
| No retroactive justification | ✅ | All criteria documented before campaign start |
| Safety flags verified at start | ✅ | MOCK=true, DRY=true, TESTNET=true, REAL_BALANCE=false |
| #3103 limitation documented | ✅ | See § #3103 Limitation |

---

## Host-Availability Preflight

| Check | Method | Result |
|-------|--------|--------|
| Host uptime | `Get-CimInstance Win32_OperatingSystem` | Since 2026-06-09T10:00:20 UTC — ~9h 42m uptime |
| Power sleep risk | `powercfg /lastwake` | 0 wake events — no sleep recorded since boot |
| Docker running | `docker ps` — all core BLUE services healthy | ✅ Core BLUE all healthy (9h+) |
| Runtime continuity | Docker uptime 9h+ | Stable |

**Verdict:** Host preflight PASS.

---

## Safety Preflight

| Check | Source | Result |
|-------|--------|--------|
| `MOCK_TRADING=true` | `docker inspect cdb_execution` env | ✅ Explicit |
| `USE_REAL_BALANCE=false` | `docker inspect cdb_execution` env | ✅ Explicit |
| `DRY_RUN=true` | Code default (`services/execution/config.py:27`) | ✅ Not overridden |
| `MEXC_TESTNET=true` | Code default (`services/execution/config.py:22`) | ✅ Not overridden |
| No live-order evidence | `correlation_ledger` recent events from 2026-06-06 | ✅ Dormant |
| LR remains NO-GO | `LR-AUDIT-STATUS-2026-03-05.md` | ✅ Confirmed |
| Board `trade-capable` ≠ Live-Go | `CONTROL_REGISTER.md` | ✅ Confirmed |

**Safety Preflight: PASS** — all flags verified.

---

## Baseline Correlation Ledger State

| Metric | Value |
|--------|-------|
| Total events (cumulative) | 34,256+ |
| Most recent event | 2026-06-06T03:31:54Z (ts_ms 1780716714105) |
| Events since campaign start | 0 (baseline) |

---

## Monitoring Log

### Cycle 2 — 2026-06-09T20:55 UTC

| Metric | Value |
|--------|-------|
| Core BLUE services | All healthy (10h+ uptime) |
| Host continuity | ✅ Continuous since boot 10:00 UTC |
| Safety flags | All confirmed |
| Regime | HIGH_VOL_CHAOTIC (20:55:00 UTC) |
| BTCUSDT 15m range | 0.21% (62186.44 − 62055.30) — fading from start |
| BTCUSDT 60m range | ~0.50% (62272.10 − 61960.00) |
| correlation_ledger events since start | 0 |
| Chain candidate | None |

### Cycle 3 — 2026-06-09T21:00 UTC

| Metric | Value |
|--------|-------|
| Core BLUE services | All healthy (10h+ uptime) |
| Host continuity | ✅ ~11h uptime, 0 sleep/wake |
| Safety flags | All confirmed |
| Regime | HIGH_VOL_CHAOTIC (20:59 UTC) |
| BTCUSDT 15m range | 0.17% (62162.83 − 62055.30) — still compressing |
| BTCUSDT latest | ~62100 (consolidating) |
| correlation_ledger events since start | 0 |
| Chain candidate | None |

### Trend

| Cycle | Time (UTC) | P1 15m Range | Events |
|-------|------------|-------------|--------|
| Start | 19:42 | **0.46%** | 0 |
| Cycle 2 | 20:55 | 0.21% | 0 |
| Cycle 3 | 21:00 | 0.17% | 0 |

---

## Host Reboot Interruption

### Reboot Timeline

| Event | Timestamp (UTC) | Source |
|-------|-----------------|--------|
| Campaign #2 start | 2026-06-09T19:42:00Z | Evidence doc |
| Last documented monitoring | 2026-06-09T21:00 UTC | Cycle 3 (this doc) |
| Last candle before gap | 2026-06-09T22:56 UTC | ts_ms 1781045760000 |
| **Host reboot** | **2026-06-09T22:59:30 UTC** | `Get-CimInstance Win32_OperatingSystem.LastBootUpTime` |
| Planned campaign timeout | 2026-06-10T03:42:00Z | Campaign parameters |
| Host down period | ~22:59 UTC to ~11:22 UTC next day | Candle gap evidence |
| First candle after gap | 2026-06-10T11:22 UTC | ts_ms 1781090520000 |
| Reconciliation | 2026-06-10T13:30 UTC | Current session |

### Campaign Window Coverage

| Metric | Value |
|--------|-------|
| Campaign window (planned) | 8h (19:42 → 03:42 UTC) |
| **Observed duration** | **3h 14min** (19:42 → 22:56 UTC) |
| Unobserved duration | ~4h 46min (22:56 → 03:42 UTC) |
| Expected candles in window | 480 (8h × 60min) |
| Actual candles in window | **195** (DB-verified) |
| Candle gap length | ~12h 26min (22:56 UTC → 11:22 UTC next day) |

### Candle Data within Campaign Window

| Metric | Value |
|--------|-------|
| First candle | ts_ms 1781034120000 (19:42 UTC) |
| Last candle | ts_ms 1781045760000 (22:56 UTC) |
| Total candles | 195 |
| Peak high | 62272.10 at ts_ms 1781036100000 (20:15 UTC) |
| Candle gap | 1781045760000 → 1781090520000 (~747 min) |

### Host Forensics

| Check | Method | Result |
|-------|--------|--------|
| Current boot time | `Win32_OperatingSystem.LastBootUpTime` | 2026-06-09T22:59:30 UTC |
| Prior boot duration | Boot 10:00 UTC → reboot 22:59 UTC | ~12h 59min |
| Sleep/wake events (current boot) | `powercfg /lastwake` | 0 |
| Docker uptime (current boot) | `docker ps` | ~9-12 min |
| Docker uptime (prior boot) | Cycle 1–3 evidence | 9h+ through ~21:00 UTC |

### Reboot Classification

The host reboot at 22:59 UTC occurred **3h 17min after campaign start** and **4h 43min before the planned timeout**. The remaining campaign window (22:56 → 03:42 UTC) is a data black box — no DB evidence, monitoring, or Docker access exists for this period.

---

## Campaign #2 Verdict: HOLD_INTERRUPTED_CAMPAIGN_2

### Why This Is NOT a Market Failure

| Fact | Evidence |
|------|----------|
| Campaign ran only 3h 14min of the 8h window | Host reboot at 22:59 UTC, 195/480 candles |
| Host was not continuously available | Boot at 10:00 UTC, reboot at 22:59 UTC |
| Last monitoring at 21:00 UTC — 0 events | Cycle 3 evidence |
| Last candle at 22:56 UTC | DB-verified |
| Campaign window (up to 03:42 UTC) not covered | ~4h 46min unobserved |
| correlation_ledger events (observed period): 0 | DB-verified throughout |
| Chain produced (observed period): no | 3 monitoring cycles + 195 candles |
| Safety flags unchanged (observed period) | MOCK=true, DRY=true, TESTNET=true, REAL_BALANCE=false |

### Why No 8h Statement Is Possible

The host became unavailable at ~22:59 UTC, ~4h 46min before the planned 03:42 UTC timeout. During the host-down period, it is impossible to determine:

- Whether a SIGNAL fired (candles could have been delivered post-reboot by the market/candles pipeline)
- Whether a DECISION, paper ORDER, or FILL occurred
- Whether correlation_ledger events were recorded before the Docker shutdown
- Whether regime state changed

However, no events exist in correlation_ledger for timestamp_ms >= 1781034120000 (campaign start). The candle gap (22:56 → 11:22 UTC) spans the full unobserved window. This strongly suggests Docker was fully shut down during this period and no trading pipeline operated.

### What Actually Happened to BTCUSDT

During the observed window (19:42 → ~21:00 UTC), BTCUSDT moved from ~61850 to a peak of 62272.10 at 20:15 UTC (+0.68%), then consolidated at ~62100. The 15m range compressed from 0.46% at start to 0.17% by Cycle 3. No 0.5% breakout within 15 minutes was observed — `primary_breakout_v1` did not trigger.

Post-reboot candles (11:22 UTC onward) show BTCUSDT dropped significantly to ~60900-61200 range, but this occurred well past the campaign timeout (03:42 UTC) and is outside scope.

### Classification

This campaign **is**:
- An interrupted campaign (host reboot before timeout)
- An `interruption_record` — not `natural_paper_evidence`
- Observed for 3h 14min with 0 events / 0 chain

This campaign **is not**:
- A completed 8h campaign (insufficient observation)
- A market failure (infrastructure interruption, not market verdict)
- Comparison-grade (no window to extract)
- Natural paper evidence (interruption record only)

### Impact on Campaign Limits

| Slot | Status | Counts as Failure? |
|------|--------|---------------------|
| Campaign #1 | HOLD_INTERRUPTED_BY_HOST_SHUTDOWN | No (interruption) |
| Campaign #1R | HOLD_NO_CHAIN_CAMPAIGN_1R | **Yes** — Slot #1 consumed |
| Campaign #2 | HOLD_INTERRUPTED_CAMPAIGN_2 | **No** — infrastructure interruption |
| Campaign #3 | Available | — |

**Effective slot count: 1 of max 3 consumed.** Campaign #2 does NOT consume a slot — it is an interruption, not a market failure. The remaining campaign capacity is **2 slots** (Campaign #2R or direct #3).

### Impact on #3087

| Gate | Status | Reason |
|------|--------|--------|
| §5.2.4 — at least one window with non-empty `regime_segments` | **BLOCKED** | Campaign #2 interrupted — 0 chain in observed window; no window to extract |

### Recommendation

**Campaign #2R** — restart as replacement with fresh start-criteria evaluation:
1. Re-evaluate P1 (15m range ≥0.35%), P2 (60m range ≥0.75%), P3 (TREND or HIGH_VOL_CHAOTIC)
2. Prefer TREND regime per original Campaign #2 policy
3. Do NOT lower breakout threshold (0.5% unchanged)
4. Include host-availability preflight
5. Document #3103 limitation if HIGH_VOL_CHAOTIC is the only available regime

After 2 more campaign failures (or 2 more interruptions), escalate to Option E (waiver/split) per #3094.

---

## Safety Boundaries

| Boundary | Status |
|----------|--------|
| LR remains NO-GO | Confirmed |
| No Live-Go / Echtgeld-Go | Confirmed |
| No stack start/stop/restart | Confirmed — stack already running |
| No Docker/compose changes | Confirmed |
| No env/config changes | Confirmed |
| No strategy/risk/execution changes | Confirmed |
| No stimulus runner | Confirmed |
| No synthetic market movement | Confirmed |
| No productive DB writes | Confirmed — SELECT only |
| No secrets in outputs | Confirmed |

---

## Limitations

1. **HIGH_VOL_CHAOTIC in blocked_regimes** — #3103 remains open. A SIGNAL may fire but DECISION may block. Documented as accepted risk for Campaign #2.
2. **DRY_RUN + MEXC_TESTNET are code defaults** — not explicit in docker env, but verified against source code defaults.
3. **Venue mismatch** — Current candles are MEXC (from `cdb_market` → `cdb_candles` → `cdb_db_writer`). Same-venue MEXC replay may not exist yet (#3091).
4. **Single strategy, single symbol** — Only `primary_breakout_v1` / BTCUSDT.
5. **Host-availability preflight is advisory** — No automated guard against future shutdowns (#3102).

---

## References

- #3095 — Campaign execution issue (OPEN)
- #3087 — Product-complete gate (OPEN, BLOCKED)
- #3094 — Design issue (CLOSED)
- #3103 — blocked_regimes policy clarification (OPEN)
- `docs/evidence/arvp_deterministic_window_production_3094.md` — Campaign policy design
- `docs/evidence/arvp_volatility_window_campaign_3095_1r.md` — Campaign #1R evidence
- `docs/evidence/arvp_volatility_window_campaign_3095_interruption.md` — Campaign #1 interruption record
- `docs/evidence/arvp_volatility_window_campaign_3095_2.md` — Campaign #2 evidence (this document)
- `docs/runbooks/CONTROL_REGISTER.md` — Board stage, LR NO-GO
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — LR verdict NO-GO

---

## Stop Condition Assessment (at Host Reboot Reconciliation)

| Condition | Met? | Detail |
|-----------|------|--------|
| Early stop (chain found) | ❌ | No chain in observed window |
| 8h timeout | ❌ | Host rebooted at 22:59 UTC — timeout at 03:42 UTC not reached under observation |
| Host shutdown/reboot | ✅ | Reboot at 2026-06-09T22:59:30 UTC — 4h 46min before timeout |
| Safety flag change | ❌ | All unchanged in observed window |
| Stack/health degradation | ❌ | All healthy through last observation at 21:00 UTC |

---

## Status

**HOLD_INTERRUPTED_CAMPAIGN_2**

Campaign #2 started at 2026-06-09T19:42:00Z. Three monitoring cycles (19:42, 20:55, 21:00 UTC) documented 0 events and 0 chain. BTCUSDT showed an initial +0.68% move (61850→62272 peak), but no 0.5% breakout within a single 15m window — `primary_breakout_v1` did not trigger. Volatility compressed from 0.46% to 0.17%. Host rebooted at 2026-06-09T22:59 UTC, interrupting the campaign ~3h 14min into the 8h window (~4h 46min before timeout). 195 of 480 expected candles in the campaign window are present; the remaining period is an unobservable black box. 0 correlation_ledger events throughout the entire observable campaign window. Slot #2 does not count as a market failure — this is an infrastructure interruption. Recommendation: start Campaign #2R with fresh start-criteria evaluation.
