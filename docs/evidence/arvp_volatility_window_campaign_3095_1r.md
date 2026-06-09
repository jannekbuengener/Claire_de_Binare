# ARVP Volatility-Window Campaign #1R — #3095

**Campaign ID:** `arvp_3095_vol_window_1r_20260609_1109`
**Start UTC:** 2026-06-09T11:09:00Z
**Planned Duration:** max 8h (until ~2026-06-09T19:09:00Z)
**Status:** CAMPAIGN_1R_RUNNING
**Evidence Class:** `natural_paper_evidence` (pending — no chain yet)
**Observed Events:** 0 (baseline)
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

**CAMPAIGN_1R_RUNNING**

Campaign #1R started at 2026-06-09T11:09:00Z. Start criteria met via P1 (15m range 0.39%) + P3 (HIGH_VOL_CHAOTIC). Safety preflight and host-availability preflight both PASS. Monitoring active.

### Stop Condition Assessment (at start)

| Condition | Met? | Detail |
|-----------|------|--------|
| Early stop (chain found) | ❌ | No chain yet |
| 8h timeout | ❌ | Just started |
| Safety flag change | ❌ | All unchanged |
| Stack/health degradation | ❌ | All healthy |
| Host shutdown | ❌ | Host stable, preflight passed |
| Start criterion lost | ❌ | Criteria still met |

### Next Steps

- [ ] Monitor every 20-30 min for chain events
- [ ] Document each monitoring cycle in this file
- [ ] On chain found: stop, extract, replay, compare, calibrate, scorecard
- [ ] On 8h timeout without chain: close with HOLD_NO_CHAIN_CAMPAIGN_1R; plan Campaign #2
- [ ] On host/interruption: HOLD_INTERRUPTED_CAMPAIGN_1R; document as infrastructure failure
- [ ] #3087 remains BLOCKED; #2974 remains BLOCKED by §5.2.4
