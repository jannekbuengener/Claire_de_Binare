# ARVP June 6 1h Replay Report Generation — #3221

Status Class: Scoped evidence / replay input readiness assessment
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
  - read: docs/evidence/arvp_three_window_replay_vs_paper_calibration_3219.md
  - read: docs/evidence/arvp_guarded_natural_paper_window_execution_3217.md
  - read: docs/evidence/obsolete_gordon_gate_residue_cleanup_3222.md
  - read: artifacts/paper_reference_windows/paper_reference_window_june6_1h.json
  - read: docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md
  - read: services/validation/strategy_replay_runner.py (entrypoint)
  - read: Makefile replay-shadow-run target
  - read: artifacts/candles/mexc_strict_window_3091/dataset_spec.json
  - bash: git status, gh issue/pr checks, dataset artifact inventory
  - bash: rg -n replay-shadow-run Makefile core services docs artifacts tests
  - bash: find artifacts for june6/BTCUSDT/candles/dataset/replay_report matches
records_or_results:
  - HEAD == origin/main (clean checkout, branch data/june6-1h-replay-report-3221)
  - #3221 OPEN; #3222 CLOSED; #3223 MERGED at f1d2c25d
  - #3219 CLOSED; #3220 MERGED at c004473b; #3217 CLOSED; #3218 MERGED at d2ba9b8b
  - #2985 OPEN; #1900 OPEN; #2977 OPEN (LR-050 refresh BLOCKED)
  - Gordon cleanup confirmed: PR #3223 merged, evidence doc committed
  - No repo-backed MEXC BTCUSDT 1m candle dataset exists for 2026-06-05T23:30:00Z to 2026-06-06T00:30:00Z
  - Nearest dataset: mexc_strict_window_3091 starts at 2026-06-06T13:43:00Z (13h13m too late)
  - Replay entrypoint: python -m services.validation.strategy_replay_runner --dataset-source file --input-candles <path>
  - Makefile target: make replay-shadow-run REPLAY_INPUT_CANDLES=<path> [REPLAY_OUTPUT_DIR=<dir>]
  - No runtime/Docker/backfill/replay executed
  - No explicit Jannek Human-GO for Runtime/Docker/Backfill/Replay present in this agent run
repo_crosscheck:
  - arvp_three_window_replay_vs_paper_calibration_3219.md (3-window assessment, A2 WARN A3 WARN A4 FAIL)
  - arvp_guarded_natural_paper_window_execution_3217.md (window extraction)
  - obsolete_gordon_gate_residue_cleanup_3222.md (Gordon cleanup confirmed)
  - services/validation/strategy_replay_runner.py (entrypoint code)
  - core/replay/dataset_spec.py, core/replay/dataset_provider.py (dataset layer)
  - core/replay/replay_contracts.py, core/replay/replay_vs_paper_compare.py
  - core/replay/simulator_calibration_report.py, core/replay/arvp_regime_scorecards.py
impact_on_plan:
  - June 6 1h replay_report.v1 cannot be generated without: (a) explicit Jannek Human-GO for Runtime/Docker/Backfill/Replay AND (b) a MEXC BTCUSDT 1m candle dataset for the window
  - Dataset must be backfilled from MEXC API or DB; neither is available in this slice
  - Decision: BLOCKED_HUMAN_GO_REQUIRED — no runtime action taken
limitations:
  - No explicit Jannek Human-GO for runtime present in this agent run
  - No repo-backed candle dataset exists for the window
  - No Docker/DB/backfill/replay executed
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

- `CURRENT_STATUS.md` treated as ledger, not live truth.
- LR SSOT remains `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` (NO-GO).
- Board stage `trade-capable` is not Live-Go.
- Gordon gate is obsolete; cleanup confirmed via #3222/PR #3223.
- No secret values printed, committed, or inspected.
- No stop condition triggered: read order aufloesbar, LR status klar, GitHub live state konsistent, kein Gordon-Gate.

---

## 3. Live-Lage

| Item | Status |
|---|---|
| Branch at session start | `main` (clean) |
| Working branch | `data/june6-1h-replay-report-3221` (from origin/main) |
| HEAD / origin/main | `f1d2c25d` (PR #3223) |
| Working tree | clean (except untracked `.opencode/plans/`, `docs/decisions/`) |
| #3221 | OPEN |
| #3222 | CLOSED |
| #3223 | MERGED (f1d2c25d) |
| #3219 | CLOSED |
| #3220 | MERGED (c004473b) |
| #3217 | CLOSED |
| #3218 | MERGED (d2ba9b8b) |
| #2985 | OPEN |
| #1900 | OPEN |
| #2977 | OPEN / BLOCKED (LR-050 refresh) |
| Open PRs | Dependabot-only (3207, 3206, 3205, 3204) |
| LR verdict | NO-GO |
| Board stage | `trade-capable` (not Live-Go) |

No live-truth conflict found.

---

## 4. Active Gate Policy

Per issue #3221 comments (Gate Policy Correction at 2026-06-15T21:09:58Z) and cleanup #3222/PR #3223:

- **Runtime/Docker/Backfill/Replay/Infra actions require explicit Jannek Human-GO.**
- No Gordon gate — Gordon is obsolete and must not be used as gate, blocker, advisor requirement, or bootloader step.
- This issue grants: read-only inspection, branch creation, evidence artifact creation, commit, PR creation, merge after green required checks.
- This issue does NOT grant: Docker/Compose runtime, candle dataset backfill, replay execution, replay report generation, workflow dispatch, DB mutation, MCP mutation, secrets/env reads, Live-Go or Echtgeld-Go.

---

## 5. #3221 Scope

Per issue body:

- Identify existing replay entrypoint/tooling for `replay_report.v1`. — **DONE**
- Identify exact candle dataset requirement. — **DONE**
- Identify whether a MEXC BTCUSDT candle dataset exists. — **NONE EXISTS**
- Define exact replay command/config shape. — **DONE**
- Before any Docker/Runtime/Infra action, explicit Jannek Human-GO is required. — **ENFORCED**
- Replay execution may happen only in a later execution slice. — **BLOCKED until GO**

**Out of scope per issue:** no actual replay execution, no Docker/Compose, no runtime start, no workflow dispatch, no DB mutation, no MCP mutation, no secrets, no new extraction, no new strategy, no Candidate #4, no 5m/15m discovery, no PB1/RMR/Momentum rescue, no Product-Complete claim, no Live-Go/Echtgeld-Go.

---

## 6. Runtime-GO Assessment

### Detection

```
valid_only_if:
  - "Jannek Human-GO for Runtime/Docker/Backfill/Replay" or equivalent
invalid_if:
  - GO implied by previous cleanup
  - GO ambiguous
  - GO mentions Live-Go or Echtgeld-Go
```

**Finding: No explicit Jannek Human-GO for Runtime/Docker/Backfill/Replay is present.**

- The prompt `human_go.granted_by_this_prompt` explicitly lists write/doc/commit/PR operations, but `runtime_actions_allowed_only_if_explicit_jannek_runtime_go_present` requires separate explicit wording.
- Issue #3221 comments state the policy (Jannek Human-GO required) but do not grant it.
- No incoming issue comment or prompt text contains "Jannek Human-GO for Runtime/Docker/Backfill/Replay" or equivalent.

### Result

**BLOCKED_HUMAN_GO_REQUIRED**

No runtime/Docker/backfill/replay/report-generation action was executed.

---

## 7. Candle Dataset Inventory / Backfill Result

### Requirement

- Window: 2026-06-05T23:30:00Z to 2026-06-06T00:30:00Z (1 hour)
- Symbol: BTCUSDT
- Cadence: 1m
- Venue: MEXC
- Expected candles: 60 (1m cadence, full coverage)

### Inventory of repo-backed candle datasets

| Dataset | Window | Symbol | Venue | Covers June 6 1h? |
|---|---|---|---|---|
| `artifacts/candles/3028_window/` | #3028 pilot (May 2026) | BTCUSDT | Binance | ❌ different venue + window |
| `artifacts/candles/mexc_strict_window_3091/` | 2026-06-06T13:43 to 2026-06-08T23:58 | BTCUSDT | MEXC | ❌ starts 13h13m too late |
| `artifacts/candles/mexc_multi_window_3032/` | 20 windows, none June 5-6 | BTCUSDT | MEXC | ❌ not covering period |
| `artifacts/candles/mexc_sample_expansion_3032*/` | Various | BTCUSDT | MEXC | ❌ not covering period |
| `artifacts/backtests/primary_breakout_v1/*/` | April 2026 | BTCUSDT | MEXC | ❌ different date range |

**Finding: No repo-backed MEXC BTCUSDT 1m candle dataset exists for the June 6 1h window.**

### Backfill Required

Backfill would require one of:

1. **MEXC REST API backfill** — needs MEXC API keys (secrets), dockerized runner or script, network access. Requires Docker/infra start.
2. **DB-backed path** (`--dataset-source db --db-dataset-window START_TS_MS:END_TS_MS`) — needs running Postgres with `candles_1m` table populated. Requires Docker stack start.

Both paths require explicit Jannek Human-GO for Runtime/Docker/Backfill.

---

## 8. Replay Command / Execution Result

### Replay Entrypoint

```
python -m services.validation.strategy_replay_runner \
    --dataset-source file \
    --input-candles <candles.jsonl> \
    --output-dir artifacts/replay_reports/3221_june6_1h \
    --strategy-id primary_breakout_v1 \
    --symbol BTCUSDT \
    --adapter-id primary_breakout_runner_v1 \
    --speedup-profile instant \
    --deterministic-verify
```

### Makefile target

```
make replay-shadow-run REPLAY_INPUT_CANDLES=<candles.jsonl> \
    REPLAY_OUTPUT_DIR=artifacts/replay_reports/3221_june6_1h
```

### Execution

**Not executed.** Candle dataset does not exist and explicit Jannek Runtime-GO is absent.

---

## 9. replay_report.v1 Validation

Not applicable — no replay report was generated.

Expected output path: `artifacts/replay_reports/3221_june6_1h/replay_report.json`

Expected validation criteria:
- Valid JSON, schema conformant to ReplayReportInput/ReplayReportContract
- strategy_id = primary_breakout_v1, symbol = BTCUSDT
- timestamps within 2026-06-05T23:30:00Z to 2026-06-06T00:30:00Z
- deterministic metadata present
- no secrets in output

---

## 10. Downstream Compare / Calibration / Regime Result

Not applicable — no replay report was generated.

Expected downstream tooling:

| Step | Tool | Input | Output |
|---|---|---|---|
| 2 | replay_vs_paper_compare.py | replay_report.v1 + paper_reference_window_june6_1h.json | shadow_comparison.json |
| 3 | simulator_calibration_report.py | shadow_comparison.json | simulator_calibration_report.json |
| 4 | arvp_regime_scorecards.py | shadow_comparison.json | arvp_regime_scorecard.json |

These remain blocked until the replay report exists.

### A2/A3/A4 Implication

Per #3219 (3-window assessment):

- **A2** was WARN (2 of 3 windows comparable). June 6 1h would move A2 toward PASS if replay report + compare succeed.
- **A3** was WARN (2 of 3 windows calibratable). Same path.
- **A4** remains FAIL regardless — `regime_segments` are unavailable for ALL windows. The June 6 1h replay report would not change this.

Even with a successful replay run, `regime_segments` would remain `unavailable` because the replay engine does not emit step-level regime data for these windows (established in #3219 §9).

---

## 11. Decision

**Decision: BLOCKED_HUMAN_GO_REQUIRED**

Runtime/Docker/Backfill/Replay actions require explicit Jannek Human-GO. No such GO is present in this agent run or in issue #3221 comments.

This evidence doc captures:
1. The exact dataset gap (no MEXC BTCUSDT 1m candles for 2026-06-05T23:30 to 2026-06-06T00:30)
2. The exact replay command shape
3. The exact downstream compare/calibration/regime path
4. The explicit GO wording required for the next slice

This is not:
- A Product-Complete claim
- A Live-Go / Echtgeld-Go step
- A new candidate-family opening
- A strategy rescue path

---

## 12. Required Follow-up

1. **Explicit Jannek Human-GO for Runtime/Docker/Backfill/Replay** — required before any runtime action. Recommended wording: "Jannek Human-GO for Runtime/Docker/Backfill/Replay for #3221 June 6 1h replay slice".
2. **Candle dataset backfill** — MEXC BTCUSDT 1m candles for 2026-06-05T23:30:00Z to 2026-06-06T00:30:00Z must be produced or extracted via approved path.
3. **Replay execution** — run the existing entrypoint with the validated dataset.
4. **Downstream compare/calibration** — run replay_vs_paper_compare.py, simulator_calibration_report.py against paper_reference_window_june6_1h.json.
5. **Regime scorecard** — run arvp_regime_scorecards.py (expected: unavailable, per #3219 §9).

---

## 13. Stop Rules / Safety

| Rule | Status |
|---|---|
| No Live-Go | Enforced — LR remains NO-GO |
| No Real-Money-Go | Enforced |
| No Runtime/Docker/Compose | Enforced |
| No DB mutation | Enforced |
| No workflow_dispatch | Enforced |
| No secrets exposed | Enforced |
| No Product-Complete claim | Enforced |
| No Candidate #4 | Enforced |
| No PB1/RMR/Momentum rescue | Enforced |
| No Gordon gate reintroduced | Enforced — confirmed obsolete via #3222 |
| No regime_segments inference | Enforced — not inferred, reported as unavailable |

---

## 14. Restunsicherheiten

1. Even with explicit Jannek Runtime-GO, a MEXC BTCUSDT 1m candle dataset for the June 6 1h window may not be available via any existing backfill path if the MEXC API does not serve data that far back or if the DB was not capturing candles for that exact period.
2. Even with a replay report, A4 (regime_segments) would remain FAIL for this window — the replay engine does not emit step-level regime data for this strategy/symbol pair.
3. The exact dataset size is unknown without a backfill attempt; the window requires ~60 candles at 1m cadence.

---

## 15. Status

`BLOCKED_HUMAN_GO_REQUIRED`

- Dataset: MISSING (no MEXC BTCUSDT 1m candles for window)
- Replay report: NOT GENERATED (blocked by GO + dataset)
- A2/A3/A4: unchanged from #3219 (A2 WARN, A3 WARN, A4 FAIL)
- Runtime/Docker/Backfill: NOT EXECUTED
- Next GO wording required: "Jannek Human-GO for Runtime/Docker/Backfill/Replay for #3221 June 6 1h replay slice"
