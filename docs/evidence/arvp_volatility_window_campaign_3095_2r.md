# ARVP Volatility-Window Campaign #2R — #3095

**Campaign ID:** `arvp_3095_vol_window_2r_20260610_1111`
**Start UTC:** 2026-06-10T11:11:00Z
**Planned Duration:** max 8h (until ~2026-06-10T19:11:00Z)
**Status:** CAMPAIGN_2R_RUNNING
**Campaign #:** 2R of max 3 (replaces interrupted Campaign #2; does not consume a new slot)

---

## Campaign History

| Slot | ID | Status | Chain |
|------|-----|--------|-------|
| Campaign #1 | `arvp_3095_vol_window_20260608_2341` | HOLD_INTERRUPTED_BY_HOST_SHUTDOWN | No |
| Campaign #1R | `arvp_3095_vol_window_1r_20260609_1109` | HOLD_NO_CHAIN_CAMPAIGN_1R — Slot #1 consumed | No |
| Campaign #2 | `arvp_3095_vol_window_2_20260609_1942` | HOLD_INTERRUPTED_CAMPAIGN_2 | No (observed 3h 14min) |
| Campaign #2R | `arvp_3095_vol_window_2r_20260610_1111` | **CAMPAIGN_2R_RUNNING** | — |

**Slot #1 consumed** (Campaign #1R failure). Slot #2 does NOT count (interruption). **Campaign #2R is a replacement for the interrupted #2 — does NOT consume a new slot.**

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

### Live Data (2026-06-10T11:11 UTC)

**Candle source:** `public.candles_1m` via `docker exec cdb_postgres psql -U claire_user`
**Regime source:** `docker logs cdb_regime --tail 5`

| # | Criterion | Threshold | Actual | Met? | Source |
|---|-----------|-----------|--------|------|--------|
| P1 | BTCUSDT rolling 15m high-low range | ≥0.35% | **0.307%** | ❌ | 15 most recent 1m candles |
| P2 | BTCUSDT rolling 60m high-low range | ≥0.75% | **1.474%** | ✅ | 61 candles available |
| P3 | Regime TREND or HIGH_VOL_CHAOTIC | TREND preferred | **HIGH_VOL_CHAOTIC** | ✅ | `cdb_regime` logs (13:10:05 CEST) |

**Start criterion: P2 (60m range 1.474%) + P3 (HIGH_VOL_CHAOTIC)**

### Range Computation Detail

**15-minute window** (last 15 candles):
- Max high: 61692.60 (ts_ms 1781096220000)
- Min low: 61503.64 (ts_ms 1781097000000)
- Range: (61692.60 − 61503.64) ÷ 61503.64 × 100 ≈ **0.307%**

**60-minute window** (61 candles available):
- Max high: 61952.30
- Min low: 61051.98
- Range: (61952.30 − 61051.98) ÷ 61051.98 × 100 ≈ **1.474%**

**Regime:**
```
2026-06-10 13:10:05,738 [INFO] regime_service: Regime-Signal: BTCUSDT 60s HIGH_VOL_CHAOTIC
```

### #3103 Limitation

HIGH_VOL_CHAOTIC (regime_id=2) is in `blocked_regimes` per the decision contract. A SIGNAL that fires during this regime may have its DECISION gate reject entry. Campaign #2R accepts this risk with explicit documentation. TREND is unavailable — accepting HIGH_VOL_CHAOTIC as the best available regime with P2 met as secondary validation.

---

## Campaign Parameters

| Parameter | Value |
|-----------|-------|
| Campaign ID | `arvp_3095_vol_window_2r_20260610_1111` |
| Campaign # | 2R of max 3 (replaces interrupted #2) |
| Start UTC | 2026-06-10T11:11:00Z |
| Planned timeout UTC | ~2026-06-10T19:11:00Z (max 8h) |
| Strategy | `primary_breakout_v1` |
| Symbol | BTCUSDT |
| Safety flags | MOCK_TRADING=true, DRY_RUN=true, MEXC_TESTNET=true, USE_REAL_BALANCE=false |
| Start criteria met | P2 (60m range 1.474%) + P3 (HIGH_VOL_CHAOTIC) |
| Early stop condition | First complete SIGNAL → DECISION → ORDER(paper_) → FILL chain |
| Monitoring interval | ~20-30 minutes |

---

## Anti-Cherry-Pick Compliance

| Rule | Status | Evidence |
|------|--------|----------|
| Campaign-ID documented before start | ✅ | `arvp_3095_vol_window_2r_20260610_1111` |
| Start criteria documented before start | ✅ | P2 1.474%, P3 HIGH_VOL_CHAOTIC |
| Planned duration documented before start | ✅ | max 8h, until ~2026-06-10T19:11 UTC |
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
| Host uptime | `Get-CimInstance Win32_OperatingSystem` | Since 2026-06-09T22:59:30 UTC — ~12h uptime |
| Power sleep risk | `powercfg /lastwake` | 0 wake events — no sleep recorded since boot |
| Docker running | `docker ps` — all core BLUE services healthy | ✅ Core BLUE all healthy (2h uptime) |
| Runtime continuity | Docker uptime 2h+ | Stable |

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
| Most recent event | 2026-06-06T03:31:54Z (ts_ms 1780716714105) |
| Events since campaign start | 0 (baseline) |

---

## Monitoring Log

### Cycle 1 — 2026-06-10T11:11 UTC (Start)

| Metric | Value |
|--------|-------|
| Core BLUE services | All healthy (2h uptime) |
| Host continuity | ✅ Continuous since boot 22:59 UTC (12h+) |
| Safety flags | All confirmed |
| Regime | HIGH_VOL_CHAOTIC (13:10:05 CEST) |
| BTCUSDT 15m range | 0.307% (61503.64 − 61692.60) |
| BTCUSDT 60m range | 1.474% (61051.98 − 61952.30) |
| BTCUSDT latest | ~61503 (consolidating after upward move) |
| correlation_ledger events since start | 0 |
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
| No stimulus runner | Confirmed |
| No synthetic market movement | Confirmed |
| No productive DB writes | Confirmed — SELECT only |
| No secrets in outputs | Confirmed |

---

## Limitations

1. **HIGH_VOL_CHAOTIC in blocked_regimes** — #3103 remains open. A SIGNAL may fire but DECISION may block. Documented as accepted risk for Campaign #2R.
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
- #3102 — Campaign watchdog / host-availability guard (OPEN)
- `docs/evidence/arvp_deterministic_window_production_3094.md` — Campaign policy design
- `docs/evidence/arvp_volatility_window_campaign_3095_2.md` — Campaign #2 evidence
- `docs/runbooks/CONTROL_REGISTER.md` — Board stage, LR NO-GO
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — LR verdict NO-GO

---

## Status

**CAMPAIGN_2R_RUNNING**

Campaign #2R started at 2026-06-10T11:11:00Z with start criterion P2 (BTCUSDT 60m range 1.474% ≥ 0.75%) + P3 (HIGH_VOL_CHAOTIC). P1 (15m range 0.307%) did not individually meet the 0.35% threshold. Safety flags confirmed. Host uptime 12h+ continuous. Docker core BLUE healthy (2h). Timeout at ~2026-06-10T19:11:00Z. Monitoring active.
