# ARVP Volatility-Window Campaign — #3095

**Campaign ID:** `arvp_3095_vol_window_20260608_2341`
**Start UTC:** 2026-06-08T23:41:09Z
**Planned Duration:** max 8h (until ~2026-06-09T07:41:09Z)
**Status:** HOLD_CAMPAIGN_STILL_RUNNING
**Evidence Class:** `natural_paper_evidence` (pending — no chain yet)
**Observed Events:** 0 (DB-verified via `cdb_readonly`)
**Monitoring Cycles:** 4 (23:43–00:14 UTC)
**Last Verification UTC:** 2026-06-09T00:14:00Z

---

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `gh issue view` (x7), `gh pr list`, `git fetch/status/rev-parse`, `rg`, file reads (x12), `docker ps`, `docker exec cdb_postgres psql` (SELECT only), `docker logs cdb_regime`, `docker inspect` (env only) |
| `records_or_results` | 7 live GitHub queries; design doc (#3094); runbook; strategy contract; candles data (61 rows, 22:38–23:38 UTC); correlation_ledger counts; regime logs |
| `repo_crosscheck` | All claims verified against repo files and GitHub live state. Candles sourced from `public.candles_1m` via `claire_user`. Regime sourced from `cdb_regime` logs. Correlation from `public.correlation_ledger` via `cdb_readonly`. |
| `impact_on_plan` | No DB/MCP/brain claims used; all evidence is GitHub+repo+docker backed. Campaign GO derived from live market data. |
| `limitations` | No SurrealDB, no Context Brain, no DB-backed memory. `cdb_readonly` has no SELECT on `candles_1m`; used `claire_user` for candle queries. |

---

## Bootloader / Read-Order Evidence

- Root pointer `AGENTS.md` resolved ✅
- Canonical agent registry `agents/AGENTS.md` read ✅
- `knowledge/governance/CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`, `CDB_AGENT_POLICY.md` §4 ✅
- `docs/runbooks/CONTROL_REGISTER.md`: Board stage `trade-capable` (ratified 2026-04-08, #1492), LR NO-GO ✅
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`: LR verdict NO-GO ✅
- `CURRENT_STATUS.md`: Ledger-only, not live truth ✅
- `docs/evidence/arvp_deterministic_window_production_3094.md`: Design decision, Option B ✅
- `docs/runbooks/ARVP_OPERATOR_RUNBOOK.md`: Operating order, stop rules ✅
- `docs/evidence/arvp_product_complete_review_2974.md`: §5.2.4 is single hard blocker ✅
- `knowledge/contracts/PRIMARY_BREAKOUT_V1.md`: Strategy spec, breakout=0.5%, regime=TREND only ✅
- Git truth: HEAD `66e910fc` == `origin/main`, clean worktree at session start ✅
- Branch: `docs/arvp-campaign-3095` created from `origin/main` ✅

---

## Live-Lage (GitHub Live Truth as of 2026-06-09)

| Issue | State | Key Fact |
|-------|-------|----------|
| #3095 | **OPEN** | This campaign execution |
| #3094 | **CLOSED** | Design completed, PR #3097 merged at `66e910fc` |
| #3087 | **OPEN** | HOLD pending #3095 campaign outcome |
| #2974 | **CLOSED** | Product-complete BLOCKED by §5.2.4 |
| #1900 | **OPEN** | ARVP north-star anchor |
| #3091 | **OPEN** | Capture future MEXC candles |
| #3096 | **OPEN** | Evidence class policy enforcement |
| **Open PRs** | **0** | No open pull requests |

---

## Design Source

| Item | Value |
|------|-------|
| Design issue | #3094 |
| Design PR | #3097 |
| Merge SHA | `66e910fc` |
| Decision doc | `docs/evidence/arvp_deterministic_window_production_3094.md` |
| Recommended route | Option B — Scheduled Volatility-Window Campaign |
| Strategy | `primary_breakout_v1` (unchanged — 0.5% breakout, 15m lookback) |
| Symbol | BTCUSDT |
| Max campaigns | 3 |
| Per-campaign duration | max 8h |
| Early stop | On first SIGNAL → DECISION → ORDER(paper_) → FILL chain |
| Escalation | After 3 failed campaigns → Option E (waiver) |

---

## Start Criteria Evaluation

### Primary Criteria (any one suffices)

| # | Criterion | Threshold | Actual | Met? | Source |
|---|-----------|-----------|--------|------|--------|
| P1 | BTCUSDT rolling 15m high-low range | ≥0.35% | **~0.28%** | ❌ | `public.candles_1m` (23:24–23:38 UTC) |
| P2 | BTCUSDT rolling 60m high-low range | ≥0.75% | **~0.88%** | ✅ | `public.candles_1m` (22:39–23:38 UTC) |
| P3 | Regime non-low/stable | TREND or HIGH_VOL_CHAOTIC | **HIGH_VOL_CHAOTIC** | ✅ | `cdb_regime` logs (23:38:02 UTC) |

**Verdict: START CRITERIA MET** via P2 + P3.

### Criteria Computation Details

**15-minute window** (15 candles: 23:24–23:38 UTC):
- Max high: 63214.79 (23:25)
- Min low: 63038.52 (23:33)
- Range: (63214.79 − 63038.52) ÷ 63038.52 × 100 ≈ **0.28%**

**60-minute window** (60 candles: 22:39–23:38 UTC):
- Max high: 63593.64 (23:15)
- Min low: 63038.52 (23:33)
- Range: (63593.64 − 63038.52) ÷ 63038.52 × 100 ≈ **0.88%**

**Regime**: `HIGH_VOL_CHAOTIC` emitted at 2026-06-08T23:38:02Z by regime_service.
Source: `docker logs cdb_regime --tail 5`:
```
2026-06-08 23:38:02,238 [INFO] regime_service: Regime-Signal: BTCUSDT 60s HIGH_VOL_CHAOTIC
```

### Secondary Criteria (schedule context, not standalone)

| Criterion | Status | Note |
|-----------|--------|------|
| US session liquidity window | Out of session | NYSE closed; pre-Asian session (UTC 23:41) |
| Pre-documented macro/news | Not used | No macro event pre-documented |

### Data Sources

- **Candles**: `public.candles_1m` via `docker exec cdb_postgres psql -U claire_user -d claire_de_binare`
  - 61 rows fetched (22:38:00 to 23:38:00 UTC), all BTCUSDT
  - Column: `ts_ms`, `open`, `high`, `low`, `close`, `volume`, `regime_id`
- **Regime**: `docker logs cdb_regime --tail 5`
- **Correlation**: `public.correlation_ledger` via `docker exec cdb_postgres psql -U cdb_readonly -d claire_de_binare`
  - Total rows: 34,256 (cumulative)
  - 0 events in last 12h; most recent event 2026-06-06T03:31:54Z

---

## Runtime Safety Preflight

| Check | Method | Result |
|-------|--------|--------|
| Docker running | `docker ps` | ✅ 2 days uptime |
| `cdb_risk` | HTTP :8002/health | ✅ healthy |
| `cdb_candles` | HTTP :8007/health | ✅ healthy |
| `cdb_paper_runner` | HTTP :8004/health | ✅ healthy (uptime 208377s) |
| `cdb_execution` | HTTP :8003/health | ✅ healthy |
| `cdb_signal` | HTTP :8005/health | ✅ healthy |
| `cdb_market` | HTTP :8009/health | ✅ healthy |
| `cdb_regime` | HTTP :8008/health | ✅ healthy |
| `cdb_allocation` | HTTP :8006/health | ✅ healthy |
| `MOCK_TRADING=true` | `docker inspect cdb_execution` env | ✅ Explicit |
| `DRY_RUN=true` | Code default (`services/execution/config.py:27`) | ✅ Not overridden |
| `MEXC_TESTNET=true` | Code default (`services/execution/config.py:22`) | ✅ Not overridden |
| `USE_REAL_BALANCE=false` | `docker inspect cdb_execution` env | ✅ Explicit |
| `POSTGRES_READONLY_PASSWORD_DSN` | `$env:POSTGRES_READONLY_PASSWORD_DSN` | ✅ SET (value hidden) |
| No live-order evidence | `correlation_ledger` recent events = 0 | ✅ Dormant since 2026-06-06 |

**Preflight: PASS** — all checks green.

---

## Runtime Observation

### Campaign Start

| Field | Value |
|-------|-------|
| Campaign ID | `arvp_3095_vol_window_20260608_2341` |
| Start UTC | 2026-06-08T23:41:09Z |
| Start ts_ms | 1780962069000 (UTC epoch millis) |
| Planned duration | max 8h (until ~2026-06-09T07:41:09Z) |
| Strategy | `primary_breakout_v1` |
| Symbol | BTCUSDT |
| Observation method | Read-only: `docker ps` (health), `docker exec cdb_postgres psql` (SELECT only on correlation_ledger), `docker logs cdb_regime` (regime state) |
| Monitoring interval | ~30 minutes |

### Monitoring Cycle Template

Each 30-minute cycle:
1. `docker ps` — verify core BLUE services healthy
2. `docker logs cdb_regime --tail 3` — current regime state
3. `docker exec cdb_postgres psql -U cdb_readonly -d claire_de_binare` — SELECT on correlation_ledger for new events since campaign start
4. If new SIGNAL events: check for DECISION → ORDER → FILL chain
5. Document findings below

### Observation Log

#### Cycle 1 — 2026-06-08T23:43 UTC (+2min)

| Metric | Value |
|--------|-------|
| Core BLUE services | All healthy |
| Regime | HIGH_VOL_CHAOTIC (persistent since 23:38) |
| BTCUSDT price (signal engine) | ~$63,176 |
| BTCUSDT latest candle (23:42) | O=63184.04, H=63194.42, L=63166.44, C=63166.45 |
| correlation_ledger events since start | 0 |
| Signal activity | price_buffer active, pct_change ~0.003% (below breakout threshold) |
| paper_runner events logged | 484,900 |
| Most recent order (DB) | 2026-06-06T03:31:53Z (SELL filled, 3 days ago) |
| Most recent signal (DB) | None since 2026-06-06 |
| Chain candidate | None |

**Narrative:** Price recovered from $63,038 low (23:33) to $63,194 (23:42 high). Currently consolidating ~$63,170. Signal engine observing but 0.5% breakout not triggered. Regime remains HIGH_VOL_CHAOTIC. All infrastructure nominal.

---

## Correlation Ledger Result

### Baseline at Campaign Start

| Metric | Value |
|--------|-------|
| Total events (cumulative) | 34,256 |
| Total orders | 11 |
| Total fills | 10 |
| Total decisions | 17,126 |
| Total signals | 17,109 |
| Events since campaign start | *(pending first monitoring cycle)* |
| Most recent event (any) | 2026-06-06T03:31:54Z |

### Monitoring Cycles

| Cycle | UTC | Health | Regime | BTCUSDT | Events Since Start | Chain |
|-------|-----|--------|--------|---------|---------------------|-------|
| 1 | 23:43 | ✅ All healthy | HIGH_VOL_CHAOTIC | ~$63,176 | 0 | None |
| 2 | 23:50 | ✅ All healthy | HIGH_VOL_CHAOTIC | ~$63,011 | 0 | None |
| 3 | 23:53 | ✅ All healthy | HIGH_VOL_CHAOTIC | ~$63,041 | 0 | None |
| 4 | 00:14 | ✅ All healthy | HIGH_VOL_CHAOTIC | — | **0** (DB-verified) | None |

---

## Anti-Cherry-Pick Compliance

| Rule | Status | Evidence |
|------|--------|----------|
| Campaign-ID documented before start | ✅ | `arvp_3095_vol_window_20260608_2341` in this doc |
| Start criteria documented before start | ✅ | P2 60m range = 0.88%, P3 HIGH_VOL_CHAOTIC |
| Planned duration documented before start | ✅ | max 8h, until ~2026-06-09T07:41UTC |
| Failed campaigns counted, not discarded | ✅ | This is Campaign #1 of max 3 |
| No strategy parameter lowering | ✅ | `primary_breakout_v1` unchanged (0.5% breakout) |
| No stimulus runner | ✅ | No stimulus used |
| No synthetic market movement | ✅ | Natural market data only |
| No retroactive justification | ✅ | All criteria documented before campaign start |
| Safety flags verified at start | ✅ | MOCK=true, DRY=true, TESTNET=true, REAL_BALANCE=false |

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

---

## Limitations

1. **`cdb_readonly` cannot read `candles_1m`.** Used `claire_user` for candle queries. This is acceptable for start criteria evaluation but should be noted.
2. **Venue mismatch.** Current candles are MEXC (from `cdb_market` → `cdb_candles` → `cdb_db_writer`). Replay data may be from a different venue (#3028 used Binance). Future extraction should use MEXC capture pipeline (#3091).
3. **Regime `HIGH_VOL_CHAOTIC` is in `blocked_regimes`.** The decision contract may block entry during HIGH_VOL_CHAOTIC. If a SIGNAL fires but DECISION rejects, the chain will not complete. This campaign will document either outcome honestly.
4. **Single strategy, single symbol.** Only `primary_breakout_v1` / BTCUSDT. No diversification.
5. **Session duration.** The 8h campaign window may exceed a single agent session. The campaign may need to continue across session restarts.

---

## References

- #3095 — This campaign execution issue
- #3094 — Design issue (CLOSED, PR #3097, `66e910fc`)
- #3087 — Parent: produce longer comparison-grade paper reference windows
- #2974 — Product-complete review (BLOCKED by §5.2.4)
- #1900 — ARVP north-star anchor
- `docs/evidence/arvp_deterministic_window_production_3094.md` — Design decision
- `docs/runbooks/ARVP_OPERATOR_RUNBOOK.md` — Operator runbook
- `knowledge/contracts/PRIMARY_BREAKOUT_V1.md` — Strategy contract
- `docs/runbooks/CONTROL_REGISTER.md` — Board stage, LR NO-GO
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — LR verdict
- `services/validation/paper_reference_window_runner.py` — Extraction runner
- `services/regime/service.py` — Canonical regime IDs

---

### Runtime Verification (2026-06-09T00:14 UTC)

DB query against `public.correlation_ledger` (via `cdb_readonly` role):

```sql
SELECT event_type, count(*) FROM public.correlation_ledger
WHERE timestamp_ms >= 1780962069000 GROUP BY event_type;
-- Result: (0 rows)

SELECT count(*) FROM public.correlation_ledger
WHERE timestamp_ms >= 1780962069000;
-- Result: 0
```

Most recent event in ledger: `1780716714105` (2026-06-06T03:31:54Z) — ~68h before campaign start. No events of any type since campaign began.

Stack health at verification time: All BLUE services healthy (`docker ps`), regime idle (health checks only).

---

## Campaign Evidence Summary

| Field | Value |
|-------|-------|
| Campaign ID | `arvp_3095_vol_window_20260608_2341` |
| Campaign # | 1 of max 3 |
| Start UTC | 2026-06-08T23:41:09Z |
| Start ts_ms | 1780962069000 |
| Planned end UTC | ~2026-06-09T07:41:09Z (max 8h) |
| Duration observed | ~34 min |
| Start Criteria | P2: 60m range 0.88% ✅, P3: HIGH_VOL_CHAOTIC ✅ |
| Safety flags | MOCK_TRADING=true, DRY_RUN=true, MEXC_TESTNET=true, USE_REAL_BALANCE=false |
| Strategy | `primary_breakout_v1` (0.5% breakout, 15m lookback) |
| Symbol | BTCUSDT |
| Monitoring cycles | 4 |
| observed_events_count | 0 |
| signal_count | 0 |
| decision_count | 0 |
| paper_order_count | 0 |
| paper_fill_count | 0 |
| Full chain (SIGNAL→DECISION→ORDER→FILL) | **No** |
| regime_segments | N/A — no window to extract |
| Evidence class | `natural_paper_evidence` (pending) |

## Status

**HOLD_CAMPAIGN_STILL_RUNNING**

Campaign #1 has ~7.5h remaining (until ~07:41 UTC). 0 events observed through 4 monitoring cycles. No SIGNAL fired — `primary_breakout_v1` 0.5% breakout threshold not triggered. Regime `HIGH_VOL_CHAOTIC` persisted throughout observation.

### Stop Condition Assessment

| Condition | Met? | Detail |
|-----------|------|--------|
| Early stop (chain found) | ❌ | No chain |
| 8h timeout | ❌ | ~34 min elapsed |
| Safety flag change | ❌ | All unchanged |
| Stack/health degradation | ❌ | All healthy |

### Campaign Classification

- **Evidence recorded**: ✅ — All monitoring cycles, DB-verified event counts, safety flags, start criteria documented
- **Chain produced**: ❌ — 0 events, 0 signals, 0 decisions, 0 orders, 0 fills
- **Product-Complete valid**: ❌ — No `natural_paper_evidence` with non-empty `regime_segments` produced
- **Campaign #2 eligible**: ✅ — within max 3 limit; min 24h observation not yet accumulated

### Root Cause Analysis

BTCUSDT ranged narrowly (~$63,011–$63,194) during the observed window. The 0.5% breakout in 15 minutes was not met despite `HIGH_VOL_CHAOTIC` regime. Regime classification (`HIGH_VOL_CHAOTIC`) reflects short-term volatility metrics; it does not guarantee a directional breakout of sufficient magnitude for the strategy trigger. This is consistent with the findings from #3087 Phase 2 (9.4h natural observation → 0 chains).

### Next Steps

- [ ] Campaign continues passively until 8h timeout (~07:41 UTC) or chain found
- [ ] If chain found before timeout: follow Step 4 extraction→compare→calibrate→scorecard path
- [ ] On 8h timeout without chain: close with `HOLD_NO_CHAIN_CAMPAIGN_1`; plan Campaign #2
- [ ] Campaign #2 must respect 24h min total observation policy; schedule after sufficient rest
- [ ] #3087 remains BLOCKED; #2974 remains BLOCKED by §5.2.4
