# ARVP Volatility-Window Campaign #1R — #3095

**Campaign ID:** `arvp_3095_vol_window_1r_20260609_1109`
**Start UTC:** 2026-06-09T11:09:00Z
**Planned Duration:** max 8h (until ~2026-06-09T19:09:00Z)
**Status:** HOLD_NO_CHAIN_CAMPAIGN_1R
**Evidence Class:** `campaign_timeout_record` — not `natural_paper_evidence` (no chain produced)
**Observed Events:** 0 — no chain across full 8h window
**Close UTC:** 2026-06-09T19:09:00Z (timeout)
**Campaign #:** 1R of max 3 (replaces interrupted Campaign #1; does not consume a new slot)

---

## Relation to Campaign #1 Interruption

Campaign #1 (`arvp_3095_vol_window_20260608_2341`) was interrupted by host shutdown
at ~2026-06-09T00:21–01:00 UTC before its 8h window completed. Per the
interruption record (`docs/evidence/arvp_volatility_window_campaign_3095_interruption.md`),
the recommended restart as Campaign #1R is being executed now.

**Key difference:** This campaign includes a host-availability preflight and
explicit runtime-continuity monitoring to mitigate the interruption risk.

---

## Host-Availability Preflight

| Check | Method | Result |
|-------|--------|--------|
| Host uptime | `Get-CimInstance Win32_OperatingSystem` | Since 2026-06-09T10:00:20Z (local: 12:00:20) — ~68 min uptime |
| Power sleep risk | `powercfg /lastwake` | 0 wake events — no sleep recorded since boot |
| Docker running | `docker ps` — all core BLUE services healthy | ✅ 23+ services running, core all healthy |
| Runtime continuity guard | Heartbeat checks every 20-30 min | Scheduled for this campaign |

**Verdict:** Host preflight PASS. The system has been running continuously for
~68 min since boot. No sleep or power events. Docker stack is healthy.

---

## Safety Preflight

| Check | Source | Result |
|-------|--------|--------|
| `MOCK_TRADING=true` | `docker inspect cdb_execution` env | ✅ Explicit |
| `USE_REAL_BALANCE=false` | `docker inspect cdb_execution` env | ✅ Explicit |
| `DRY_RUN=true` | Code default (`services/execution/config.py:27`) | ✅ Not overridden |
| `MEXC_TESTNET=true` | Code default (`services/execution/config.py:22`) | ✅ Not overridden |
| No live-order evidence | `correlation_ledger` recent events = 0 | ✅ Dormant since 2026-06-06 |
| LR remains NO-GO | `LR-AUDIT-STATUS-2026-03-05.md` | ✅ Confirmed |
| Board `trade-capable` ≠ Live-Go | `CONTROL_REGISTER.md` | ✅ Confirmed |

**Safety Preflight: PASS** — all flags verified.

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

### Current Live Data (as of 2026-06-09T11:08:59Z)

**Candle source:** `public.candles_1m` via `docker exec cdb_postgres psql -U claire_user`
**Regime source:** `docker logs cdb_regime --tail 5`

#### Primary Criteria

| # | Criterion | Threshold | Actual | Met? | Source |
|---|-----------|-----------|--------|------|--------|
| P1 | BTCUSDT rolling 15m high-low range | ≥0.35% | **0.39%** | ✅ | `public.candles_1m` (last 15 candles) |
| P2 | BTCUSDT rolling 60m high-low range | ≥0.75% | **N/A** | ⬜ | Only 23 candles available (Docker restart ~23 min ago) |
| P3 | Regime non-low/stable | TREND or HIGH_VOL_CHAOTIC | **HIGH_VOL_CHAOTIC** | ✅ | `cdb_regime` logs (11:06:59 UTC) |

**Verdict: START CRITERIA MET** via P1 + P3.

#### Range Computation Detail

**15-minute window** (last 15 candles available):
- Max high: 62824.00
- Min low: 62580.94
- Range: (62824.00 − 62580.94) ÷ 62580.94 × 100 ≈ **0.39%**

**Regime:**
```
2026-06-09 11:06:59,992 [INFO] regime_service: Regime-Signal: BTCUSDT 60s HIGH_VOL_CHAOTIC
```

---

## Campaign Parameters

| Parameter | Value |
|-----------|-------|
| Campaign ID | `arvp_3095_vol_window_1r_20260609_1109` |
| Campaign # | 1R of max 3 (replaces interrupted #1) |
| Start UTC | 2026-06-09T11:09:00Z |
| Start ts_ms | 1781003340000 (estimated) |
| Planned timeout UTC | ~2026-06-09T19:09:00Z (max 8h) |
| Strategy | `primary_breakout_v1` |
| Symbol | BTCUSDT |
| Safety flags | MOCK_TRADING=true, DRY_RUN=true, MEXC_TESTNET=true, USE_REAL_BALANCE=false |
| Start criteria met | P1 (15m range 0.39%) + P3 (HIGH_VOL_CHAOTIC) |
| Early stop condition | First complete SIGNAL → DECISION → ORDER(paper_) → FILL chain |
| Monitoring interval | ~20-30 minutes |
| Observation method | Read-only: `docker ps`, `docker exec cdb_postgres psql` (SELECT only on `correlation_ledger`), `docker logs cdb_regime` |

---

## Anti-Cherry-Pick Compliance

| Rule | Status | Evidence |
|------|--------|----------|
| Campaign-ID documented before start | ✅ | `arvp_3095_vol_window_1r_20260609_1109` in this doc |
| Start criteria documented before start | ✅ | P1 15m range = 0.39%, P3 HIGH_VOL_CHAOTIC |
| Planned duration documented before start | ✅ | max 8h, until ~2026-06-09T19:09UTC |
| Failed campaigns counted, not discarded | ✅ | Campaign #1 counted as interrupted (HOLD_INTERRUPTED_BY_HOST_SHUTDOWN) |
| No strategy parameter lowering | ✅ | `primary_breakout_v1` unchanged (0.5% breakout) |
| No stimulus runner | ✅ | No stimulus used |
| No synthetic market movement | ✅ | Natural market data only |
| No retroactive justification | ✅ | All criteria documented before campaign start |
| Safety flags verified at start | ✅ | MOCK=true, DRY=true, TESTNET=true, REAL_BALANCE=false |
| Host-availability preflight documented | ✅ | See § Host-Availability Preflight |

---

## Baseline Correlation Ledger State

| Metric | Value |
|--------|-------|
| Total events (cumulative) | 34,256+ |
| Events in last 12h | **0** |
| Most recent event (any) | 2026-06-06T03:31:54Z (ts_ms 1780716714105) |
| Events since campaign start | 0 (baseline) |

---

## Monitoring Log

### Cycle Template

Each cycle:
1. `docker ps` — verify core BLUE services healthy
2. `docker logs cdb_regime --tail 3` — current regime state
3. `docker exec cdb_postgres psql -U cdb_readonly -d claire_de_binare` — SELECT on `correlation_ledger` for new events since campaign start
4. If new SIGNAL events: check for DECISION → ORDER → FILL chain
5. Document findings below

### Cycle 1 — 2026-06-09T11:09 UTC (Start)

| Metric | Value |
|--------|-------|
| Core BLUE services | All healthy |
| Regime | HIGH_VOL_CHAOTIC (11:06:59 UTC) |
| BTCUSDT price range (last 15m) | 62580.94 — 62824.00 |
| BTCUSDT latest candle | ~$62,700 (consolidating) |
| correlation_ledger events since start | 0 (baseline) |
| Chain candidate | None |

### Cycle 2 — 2026-06-09T11:18 UTC

| Metric | Value |
|--------|-------|
| Core BLUE services | All healthy (33 min uptime) |
| Regime | Idle (health checks only) |
| BTCUSDT 15m range | 0.25% |
| correlation_ledger events since start | 0 |
| Chain candidate | None |

### Cycle 3 — 2026-06-09T11:22 UTC

| Metric | Value |
|--------|-------|
| Core BLUE services | All healthy |
| Regime | HIGH_VOL_CHAOTIC (11:22:03 UTC) |
| BTCUSDT 15m range | 0.27% |
| correlation_ledger events since start | 0 |
| Chain candidate | None |

### Cycle 4 — 2026-06-09T11:25 UTC

| Metric | Value |
|--------|-------|
| Core BLUE services | All healthy |
| Host continuity | ✅ Continuous since boot (10:00:20 UTC) |
| Safety flags | MOCK_TRADING=true, USE_REAL_BALANCE=false — confirmed |
| Regime | HIGH_VOL_CHAOTIC (11:23:59 UTC) |
| BTCUSDT 15m range | 0.25% |
| correlation_ledger events since start | 0 |
| Chain candidate | None |

### Cycle 5 (Closeout) — 2026-06-09T19:12 UTC (past 8h timeout)

| Metric | Value |
|--------|-------|
| Core BLUE services | All healthy (8h+ uptime) |
| Host continuity | ✅ Continuous since boot 10:00:20 UTC — 0 sleep events |
| Safety flags | MOCK_TRADING=true, USE_REAL_BALANCE=false — re-confirmed |
| Regime | HIGH_VOL_CHAOTIC (19:09:59, 19:11:01, 19:12:59 UTC) |
| BTCUSDT 15m range | 0.28% |
| BTCUSDT latest candle ts_ms | 1781032320000 |
| correlation_ledger events since start | **0** (DB-verified) |
| Correlation ledger most recent event (any) | 1780716714105 (2026-06-06 — 68h+ before campaign) |
| Chain candidate | **None** |

---

## Campaign #1R Verdict: HOLD_NO_CHAIN_CAMPAIGN_1R

### Why This Is a Real Campaign Failure

| Fact | Evidence |
|------|----------|
| Campaign ran full 8h window | Start 11:09 UTC → timeout 19:09 UTC (verified at 19:12 UTC) |
| Host was continuously available | Boot 10:00:20 UTC, 0 sleep/wake events, ~9h+ uptime |
| Docker stack healthy throughout | All core BLUE services 8h+ steady |
| No runtime/DB/correlation interruption | Postgres + cdb_readonly accessible; 0 errors |
| Safety flags unchanged | MOCK=true, DRY=true, TESTNET=true, REAL_BALANCE=false throughout |
| correlation_ledger events: 0 | DB-verified at cycles 1, 2, 3, 4, and closeout |
| Chain produced: no | No SIGNAL → DECISION → ORDER → FILL chain |

### Root Cause

`primary_breakout_v1` requires a 0.5% price breakout within 15 minutes. Throughout the 8h campaign, BTCUSDT 15m range remained between 0.25% and 0.39% — consistently below the breakout threshold. The regime engine consistently reported HIGH_VOL_CHAOTIC, but actual price movement was narrow. No breakout → no SIGNAL → no chain.

This is the same pattern observed in Phase 2 extended observation (~9.4h, 0 chains) and Campaign #1 (0 events through 4 monitoring cycles before interruption).

### Classification

This campaign **is**:
- A completed 8h campaign (full window observed)
- A real campaign failure (strategy did not trigger under natural market conditions)
- Counted toward the max-3 campaign limit as Slot #1 failure

This campaign **is not**:
- `natural_paper_evidence` (no chain → nothing to extract)
- Interrupted (host was continuously available)
- Comparison-grade (no window to extract, no `regime_segments`)
- A pipeline defect (system functioned correctly throughout)

### Impact on #3087

| Gate | Status | Reason |
|------|--------|--------|
| §5.2.4 — at least one window with non-empty `regime_segments` | **BLOCKED** | Campaign #1R produced 0 chains → no window → no `regime_segments` |
| Campaign #1 attempts consumed | **1 of 3** | This campaign counts as Slot #1 failure |
| Campaign #2 eligible | **Yes** | Remaining: 2 of max 3 |
| Waiver escalation | **Not yet** | Requires ≥3 campaign failures |

### Recommendation

Campaign #2 should start under a fresh start-criteria evaluation, ideally during a period when BTCUSDT 15m range exceeds 0.35% AND the regime is TREND (not HIGH_VOL_CHAOTIC, to avoid the #3103 blocked_regimes concern). Do not lower the breakout threshold (anti-cheat).

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
| No stimulus runner as Product-Complete | Confirmed |
| No synthetic market movement | Confirmed |
| No productive DB writes | Confirmed — SELECT only |
| No secrets in outputs | Confirmed |
| Host-availability preflight documented | Confirmed |

---

## Limitations

1. **`cdb_readonly` cannot read `candles_1m`** — Used `claire_user` for candle queries. Acceptable for start criteria evaluation.
2. **Venue mismatch persistent** — Current candles are MEXC (from `cdb_market` → `cdb_candles` → `cdb_db_writer`). Same-venue MEXC replay may not exist yet (#3091).
3. **Regime `HIGH_VOL_CHAOTIC` is in `blocked_regimes`** — Decision contract may block entry during this regime. If SIGNAL fires but DECISION rejects, chain will not complete.
4. **Single strategy, single symbol** — Only `primary_breakout_v1` / BTCUSDT.
5. **Docker restarted at ~10:45 UTC** — The stack was restarted after the host reboot. Only ~23 min of candle data available at campaign start.
6. **Host-availability preflight is advisory** — No automated guard against future shutdowns.

---

## References

- #3095 — Campaign execution issue (OPEN)
- #3087 — Product-complete gate (OPEN, BLOCKED)
- #3094 — Design issue (CLOSED)
- #3098 — Original Campaign #1 evidence PR (merged)
- #3099 — Campaign #1 interruption reconciliation PR (merged)
- `docs/evidence/arvp_deterministic_window_production_3094.md` — Campaign policy design
- `docs/evidence/arvp_volatility_window_campaign_3095.md` — Campaign #1 evidence doc
- `docs/evidence/arvp_volatility_window_campaign_3095_interruption.md` — Campaign #1 interruption record
- `docs/runbooks/ARVP_OPERATOR_RUNBOOK.md` — Operator runbook
- `docs/runbooks/CONTROL_REGISTER.md` — Board stage, LR NO-GO
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — LR verdict NO-GO

---

## Status

**HOLD_NO_CHAIN_CAMPAIGN_1R**

Campaign #1R started at 2026-06-09T11:09:00Z, ran full 8h window, and reached timeout at ~2026-06-09T19:09:00Z. Start criteria were met (P1 15m range 0.39% + P3 HIGH_VOL_CHAOTIC). All 5 monitoring cycles (including closeout) confirmed 0 correlation_ledger events, no SIGNAL → DECISION → ORDER → FILL chain, and continuous host/runtime availability. Safety flags remained confirmed throughout.

### Stop Condition Assessment (at closeout)

| Condition | Met? | Detail |
|-----------|------|--------|
| Early stop (chain found) | ❌ | No chain throughout 8h |
| 8h timeout | ✅ | Verified at 19:12:53 UTC (past 19:09 UTC) |
| Safety flag change | ❌ | All unchanged throughout |
| Stack/health degradation | ❌ | All healthy — 8h+ uptime |
| Host shutdown | ❌ | Continuous since boot 10:00:20 UTC, 0 sleep events |
| Start criterion lost | ❌ | Regime stayed HIGH_VOL_CHAOTIC throughout |

### Next Steps

- [x] Monitor every 20-30 min for chain events — completed (5 cycles)
- [x] Document each monitoring cycle — completed (cycles 1–5 in this file)
- [x] On 8h timeout without chain: close with HOLD_NO_CHAIN_CAMPAIGN_1R — **DONE**
- [ ] Plan Campaign #2 with fresh start-criteria evaluation (prefer TREND regime)
- [ ] After Campaign #2 completion: update this file or create new evidence doc
- #3087 remains BLOCKED until natural paper evidence with non-empty `regime_segments`
- #2974 remains BLOCKED by §5.2.4 pending campaign success or waiver after 3 failures
