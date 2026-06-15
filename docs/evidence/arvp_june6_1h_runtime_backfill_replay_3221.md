# ARVP June 6 1h Runtime Backfill + Replay — #3221

Status Class: Runtime evidence / backfill + replay execution
Issue: #3221
Parent: #1900
Control Refs: #2985, #3219, #3220, #3217, #3218, #3222, #3223, #2977
Live-Readiness: NO-GO
Echtgeld: not authorized

---

## 1. Brain Evidence Block

```
brain_source: repo-only
brain_status: used
tools_or_queries:
  - read: canonical read-order per AGENTS.md
  - read: docs/evidence/arvp_june6_1h_replay_report_generation_3221.md (previous blocked)
  - read: docs/evidence/arvp_three_window_replay_vs_paper_calibration_3219.md
  - read: docs/runbooks/CONTROL_REGISTER.md
  - read: knowledge/runbooks/CDB_CONTROL_BOARD_RUNBOOK.md
  - read: CURRENT_STATUS.md
  - read: docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md
  - read: scripts/replay/candle_continuity.py
  - read: services/validation/strategy_replay_runner.py
  - read: core/replay/dataset_provider.py
  - read: core/replay/historical_bridge.py
  - read: Makefile replay-shadow-run target
  - bash: git status, gh issue/pr checks, MEXC API test call
  - bash: python scripts/_3221_backfill_candles.py
  - bash: make replay-shadow-run
records_or_results:
  - HEAD == origin/main (clean checkout, on branch data/june6-1h-replay-3221)
  - #3221 OPEN; #3222 CLOSED; #3223 MERGED
  - #3219 CLOSED; #3220 MERGED; #3217 CLOSED; #3218 MERGED
  - #2985 OPEN; #1900 OPEN; #2977 OPEN (LR-050 refresh BLOCKED)
  - Gordon gate confirmed obsolete (#3222/PR #3223)
  - Jannek Human-GO: EXPLICITLY GRANTED (first prompt line: "Jannek Human-GO for Runtime/Docker/Backfill/Replay for #3221 June 6 1h replay slice")
  - MEXC BTCUSDT 1m candles backfilled: 300 total (240 warmup + 60 window)
  - Dataset: artifacts/datasets/3221_june6_1h/
  - Replay executed: run_id=replay-60eb0ceca464-0001, status=completed, gate=FAIL
  - No paper reference exists for runtime-only slice
repo_crosscheck:
  - arvp_june6_1h_replay_report_generation_3221.md (previous blocked evidence — superseded)
  - arvp_three_window_replay_vs_paper_calibration_3219.md (3-window assessment, A2 WARN A3 WARN A4 FAIL)
  - scripts/replay/candle_continuity.py (MEXC backfill tool, endTime bug fixed)
impact_on_plan:
  - BLOCKED_HUMAN_GO resolved: runtime slice executed
  - Dataset gap closed: MEXC BTCUSDT 1m candles for 2026-06-05T23:30 to 2026-06-06T00:30 now exist
  - Replay report generated: gate=FAIL (0 trades, no breakout triggers)
  - Compare/calibration/regime: N/A (no paper reference for runtime-only slice; 0 trades)
limitations:
  - Runtime-only slice — no paper reference window exists for compare
  - 0 trades → regime scorecard genuinely unavailable (no trace produced)
  - LR remains NO-GO
  - No Product-Complete claim
```

---

## 2. Bootloader / Read-Order-Evidence

Canonical read-order executed per `agents/AGENTS.md`:

1. `knowledge/governance/CDB_CONSTITUTION.md`
2. `knowledge/governance/CDB_GOVERNANCE.md`
3. `knowledge/governance/CDB_AGENT_POLICY.md`
4. `knowledge/governance/SYSTEM_INVARIANTS.md`
5. `knowledge/CDB_KNOWLEDGE_HUB.md`
6. `docs/meta/WORKING_REPO_CANON.md`
7. `CURRENT_STATUS.md`
8. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
9. `docs/runbooks/CONTROL_REGISTER.md`
10. `agents/OPEN_CODE_AGENTS.md`

Verified boundaries:

- Board stage `trade-capable` is not Live-Go.
- LR SSOT remains `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` (NO-GO).
- Gordon gate is obsolete; confirmed via #3222/PR #3223.
- System stage per CONTROL_REGISTER (2026-04-08): `stage:trade-capable` (ratified via #1492).
- No secret values printed, committed, or inspected.

---

## 3. Live-Lage (Session Start)

| Item | Status |
|---|---|
| HEAD / origin/main | `eb5eccff` |
| Working branch | `data/june6-1h-replay-3221` (from origin/main) |
| Working tree | clean |
| #3221 | OPEN (#3224 PR merged, issue body updated) |
| #3222 | CLOSED |
| #3223 | MERGED |
| #3219 | CLOSED |
| #3220 | MERGED |
| #3217 | CLOSED |
| #3218 | MERGED |
| #2985 | OPEN |
| #1900 | OPEN |
| #2977 | OPEN / BLOCKED (LR-050 refresh) |
| LR verdict | NO-GO |
| Board stage | `trade-capable` (not Live-Go) |

---

## 4. Human-GO Gate

**Jannek Human-GO: GRANTED**

Prompt: `Jannek Human-GO for Runtime/Docker/Backfill/Replay for #3221 June 6 1h replay slice`

This explicit GO authorizes:
- ✅ Candle dataset backfill from MEXC public API (no auth required)
- ✅ Deterministic replay execution (offline, no Docker)
- ✅ Downstream compare/calibration/regime (if inputs available)
- ✅ Evidence artifact write + commit + PR

This GO does NOT authorize:
- ❌ Live trading, Echtgeld, or Live-Go
- ❌ DB mutation, Docker stack start, workflow dispatch
- ❌ Secrets access, Tresor access, live credentials
- ❌ New strategy candidates, Candidate #4, PB1/RMR/Momentum rescue
- ❌ Product-Complete claim

---

## 5. Candle Dataset Backfill

### Requirement

- Window: 2026-06-05T23:30:00Z to 2026-06-06T00:30:00Z (60 minutes)
- Symbol: BTCUSDT
- Cadence: 1m
- Venue: MEXC (Spot V3 API, public klines endpoint, no auth required)
- Total candles needed: 300 (240 warmup + 60 window)

### Backfill Tool

Tool: `scripts/replay/candle_continuity.py` — `fetch_mexc_klines()`
Wrapper: `scripts/_3221_backfill_candles.py`

**Bug fix applied**: `fetch_mexc_klines()` was missing `endTime` parameter in API call params dict. Without `endTime`, the MEXC API ignores `startTime` and returns recent 500 candles. Fix: added `endTime: end_ts_ms + 60000 - 1` to params (inclusive endTime in ms).

### Result

| Metric | Value |
|---|---|
| Venue | MEXC (api.mexc.com/api/v3/klines) |
| API calls | 1 |
| Total candles fetched | 300 |
| Warmup candles | 240 (2026-06-05T19:30 to 2026-06-05T23:29) |
| Window candles | 60 (2026-06-05T23:30 to 2026-06-06T00:29) |
| Cadence | 60000ms (perfect, no gaps) |
| Coverage | 100% |
| Dataset fingerprint | `6e8c693de89f6815363949d2f33ebf6841e72e5d32b4dc0f2a460977e8ed433c` |
| Candles SHA256 | `d2608cb775b38eeac7c8697c23d763e29964503aab5aa5cdd9d3ae2b1e5b0f74` |

Final values (after adding `regime_id: 0`):
- Dataset fingerprint: `71d0bf3f117c76177b7a8d479fc7153c091692e19bbb20ab6240b22e71a99c68`
- Candles SHA256: `7c4d6ea8c9c550c69108bde78fda5628d1d17c604135ef30e03985cfde75fe3a`

### Output Artifacts

| Artifact | Path |
|---|---|
| Dataset JSONL | `artifacts/datasets/3221_june6_1h/mexc_btcusdt_1m_2026-06-05T2330_2026-06-06T0030.jsonl` |
| Dataset spec | `artifacts/datasets/3221_june6_1h/dataset_spec.json` |

### Validation

- ✅ 300 rows, all with `regime_id=0`
- ✅ Perfect 60000ms cadence across all rows
- ✅ No missing candles
- ✅ No secrets in output
- ✅ Monotonic strictly increasing ts_ms
- ✅ All required fields present: ts_ms, open, high, low, close, volume, trade_count, regime_id

---

## 6. Replay Execution

### Command

```bash
make replay-shadow-run \
    REPLAY_INPUT_CANDLES=artifacts/datasets/3221_june6_1h/mexc_btcusdt_1m_2026-06-05T2330_2026-06-06T0030.jsonl \
    REPLAY_OUTPUT_DIR=artifacts/replay_reports/3221_june6_1h
```

Delegates to:
```
python -m services.validation.strategy_replay_runner \
    --dataset-source file --input-candles <path> \
    --strategy-id primary_breakout_v1 --symbol BTCUSDT \
    --adapter-id primary_breakout_runner_v1 \
    --speedup-profile instant --deterministic-verify \
    --output-dir artifacts/replay_reports/3221_june6_1h
```

### Result

| Field | Value |
|---|---|
| run_id | `replay-60eb0ceca464-0001` |
| status | `completed` |
| mode | `baseline` |
| execution_provenance_id | `bt-9db78768f998e8a4` |
| scheduler_profile | `instant` |
| deterministic_replay_ok | `True` |
| gate_result | `FAIL` |
| failed_criteria | `min_closed_trades_total`, `min_profit_factor` |
| events_processed | 300 |
| decisions_made | 0 |
| orders_placed | 0 |
| fills_recorded | 0 |
| closed_trades_total | 0 |
| buy_signals_total | 0 |
| market_state_fresh_ratio | 1.0 |
| data_integrity_ok | True |
| gross_pnl_quote | 0 |
| envelope_log_uri | `none` (0 envelopes) |

### Interpretation

Gate FAIL is the expected outcome for this 60-minute window on June 6, 2026: the `primary_breakout_v1` strategy's long-only breakout conditions (highest_high over 240-minute entry lookback within 0.05% buffer) were not triggered. The market during this window moved from ~60800 to ~61300, but the 240-minute lookback window contained higher highs that prevented the breakout threshold from being crossed.

No adapter issues: market_state_fresh_ratio = 1.0, data_integrity_ok = True.

The deterministic replay verified correctly (deterministic_replay_ok = True), confirming the pipeline is deterministic and reproducible.

### Output Artifacts (replay bundle)

| Artifact | Path |
|---|---|
| report.json | `artifacts/replay_reports/3221_june6_1h/replay-60eb0ceca464-0001/report.json` |
| operator_summary.json | `artifacts/replay_reports/3221_june6_1h/replay-60eb0ceca464-0001/operator_summary.json` |
| config.resolved.json | `artifacts/replay_reports/3221_june6_1h/replay-60eb0ceca464-0001/config.resolved.json` |
| manifest.json | `artifacts/replay_reports/3221_june6_1h/replay-60eb0ceca464-0001/manifest.json` |
| audit.log | `artifacts/replay_reports/3221_june6_1h/replay-60eb0ceca464-0001/audit.log` |
| env_redacted.txt | `artifacts/replay_reports/3221_june6_1h/replay-60eb0ceca464-0001/env_redacted.txt` |
| run_registry.jsonl | `artifacts/replay_reports/3221_june6_1h/run_registry.jsonl` |

---

## 7. Downstream Compare / Calibration / Regime

### Compare (replay_vs_paper_compare)

**N/A** — No paper reference window exists for this runtime-only slice. The June 6 1h window was not a controlled paper window; it was a runtime backfill for deterministic replay coverage.

Paper reference windows exist for the 3-window bank (#3219) and for later windows. Extracting a paper reference requires the `paper_reference_window_runner` with DB access to the `paper_events` table, which is out of scope for this runtime slice.

### Calibration (simulator_calibration_report)

**N/A** — Depends on `shadow_comparison.json` output from compare step. No compare → no calibration.

### Regime Scorecard (arvp_regime_scorecards)

**Unavailable** — The regime scorecard runner requires either `--replay-trace` or `--comparison`. With 0 trades and 0 signals, no trace was produced by the replay runner. No comparison exists. Regime scorecard is genuinely unobtainable for this window.

Per #3219 §9: "regime_segments are unavailable for ALL windows. The replay engine does not emit step-level regime data for this strategy/symbol pair."

### A2/A3/A4 Impact

Per #3219 (3-window assessment):
- **A2** remains WARN — June 6 1h replay exists but cannot be compared (no paper reference). Does not change A2.
- **A3** remains WARN — June 6 1h replay exists but cannot be calibrated (no comparison). Does not change A3.
- **A4** remains FAIL — regime_segments unavailable for this window (0 trades, no trace). Per #3219, regime_segments would remain unavailable for ALL primary_breakout_v1 windows until the adapter emits per-step regime context.

---

## 8. Git Operations

### Staged Changes

| File | Purpose |
|---|---|
| `scripts/replay/candle_continuity.py` | Bug fix: add `endTime` param to `fetch_mexc_klines()` for MEXC API |
| `scripts/_3221_backfill_candles.py` | New: backfill wrapper script for #3221 |
| `scripts/_3221_validate_dataset.py` | New: dataset validation helper |
| `docs/evidence/arvp_june6_1h_runtime_backfill_replay_3221.md` | This evidence artifact (supersedes previous blocked doc) |

Note: `artifacts/` output is gitignored; dataset JSONL, dataset_spec.json, and replay reports remain local only.

### Unstaged / Excluded

- Previous evidence `docs/evidence/arvp_june6_1h_replay_report_generation_3221.md` (superseded — kept for record, not in PR)

---

## 9. Restunsicherheiten

1. MEXC klines API `endTime` semantics: the `endTime` parameter is documented as inclusive. Testing confirmed that with `endTime = end_ts_ms + 60000 - 1`, the API returns candles with `open_time` up to `end_ts_ms`. Verified: 60 window candles (not 61), correct window alignment.

2. The `regime_id=0` value used for all candles is a placeholder. For runtime backfills where no Regime Service produced per-candle regime assignments, this is the correct fallback. Real regime data would require the Regime Service running with live market data.

3. Downstream tooling (compare, calibration, regime scorecard) remains blocked for runtime-only slices without paper references. This is an architectural limitation, not a gap in execution.

---

## 10. Stop Rules / Safety

| Rule | Status |
|---|---|
| No Live-Go | Enforced — LR remains NO-GO |
| No Real-Money-Go | Enforced |
| No DB mutation | Enforced |
| No workflow_dispatch | Enforced |
| No secrets exposed | Enforced |
| No Product-Complete claim | Enforced |
| No Candidate #4 | Enforced |
| No PB1/RMR/Momentum rescue | Enforced |
| No Gordon gate reintroduced | Enforced |
| No regime_segments inference | Enforced — reported as unavailable |

---

## 11. Status

`EXECUTED`

- ✅ Jannek Human-GO: granted
- ✅ Dataset: 300 MEXC BTCUSDT 1m candles (240 warmup + 60 window), 100% coverage
- ✅ Replay: completed, deterministic OK, gate FAIL (0 trades, valid state)
- ❌ Compare: N/A — no paper reference for runtime-only slice
- ❌ Calibration: N/A — no comparison available
- ❌ Regime scorecard: unavailable — 0 trades, no trace produced
- ✅ A2/A3/A4: unchanged from #3219 (A2 WARN, A3 WARN, A4 FAIL)
- ✅ LR: NO-GO (unchanged)
