# ARVP Deterministic Paper-Window Production Strategy — #3094

**Decision Date:** 2026-06-09
**Decision:** **DONE_DESIGN_COMPLETED**
**Scope:** Design / Policy / Evidence Classification — no code changes, no runtime
**Parent:** #3094 — [ARVP][WINDOW][DESIGN]

---

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `gh issue view` (x7), `gh pr list`, `git fetch/status/rev-parse`, `rg` across `docs/artifacts/services/core/tools/tests` (200+ matches), file reads (x14) |
| `records_or_results` | 7 live GitHub issue queries; 21 evidence docs identified in `docs/evidence/`; stimulus runner (`paper_runtime_stimulus_runner.py`, 789 lines); paper-reference runner (`paper_reference_window_runner.py`, 294 lines); regime scorecard runner; roadmap §5/§6/§8 |
| `repo_crosscheck` | All claims verified against repo files and GitHub live state. Regime enums confirmed from `services/regime/service.py` and `core/replay/regime_analytics.py`. Stimulus runner classification confirmed from #2974 product-complete review. |
| `impact_on_plan` | No DB/MCP/brain claims used; all evidence is GitHub+repo backed. Existing stimulus runner is classified pipeline-test-only per #2974 — this decision enforces that boundary. Roadmap §6 A4 proven probabilistic, not deterministic, by #3087 evidence. |
| `limitations` | No SurrealDB, no Context Brain, no DB-backed memory. Market conditions are probabilistic, not deterministic — this is the core tension the design must resolve. |

---

## Bootloader / Read-Order Evidence

- Root pointer `AGENTS.md` resolved ✅
- Canonical agent registry `agents/AGENTS.md` read ✅
- Read order: `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`, `CDB_AGENT_POLICY.md` ✅
- `docs/runbooks/CONTROL_REGISTER.md`: Board stage `trade-capable` (ratified 2026-04-08, #1492), LR NO-GO ✅
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`: LR verdict NO-GO ✅
- `CURRENT_STATUS.md`: Ledger-only, not live truth ✅
- `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md`: §5 product-complete criteria, §6 A4 ✅
- Git truth: HEAD `76a1e92c` == `origin/main`, clean worktree at session start ✅

---

## Live-Lage (GitHub Live Truth as of 2026-06-09)

| Issue | State | Key Fact |
|-------|-------|----------|
| #3094 | **OPEN** | This design issue — read-only analysis, no code changes |
| #3087 | **OPEN** | HOLD_NO_COMPARISON_GRADE_CHAIN_EXTENDED — ~9.4h natural observation → 0 paper chains |
| #2974 | **CLOSED** | DONE_REVIEW_COMPLETED_PRODUCT_COMPLETE_BLOCKED — §5.2.4 is single hard blocker |
| #1900 | **OPEN** | ARVP north-star anchor; Phase A BLOCKED |
| #3091 | **OPEN** | Capture future MEXC candles (data acquisition, execution) |
| #3092 | **OPEN** | Research external MEXC data providers (research only) |
| #3086 | **OPEN** | Acquire MEXC same-venue candle data (documented limitation) |
| #2975 | **CLOSED** | Regime scorecards evaluated — both `unavailable` |
| #2973 | **CLOSED** | Drift classification delivered |
| #2971 | **CLOSED** | Batch compare DONE_PARTIAL_DELIVERED |
| **Open PRs** | **0** | No open pull requests |

---

## Befund

### Problem Statement

#3087 attempted to produce a longer comparison-grade paper reference window via natural runtime observation on the active BLUE stack (`primary_breakout_v1`, BTCUSDT, `MOCK_TRADING=true`). After ~9.4h of passive observation, **0 comparison-grade paper chains** were produced.

**Root cause:** `primary_breakout_v1` requires a 0.5% price breakout within 15 minutes to emit a SIGNAL. During the observation window, BTCUSDT ranged between ~$63,588 and ~$63,800 — maximum movement <0.35%. The strategy simply did not trigger. This is market conditions, not a technical defect.

**Consequence:** Roadmap §5.2.4 requires at least one window with non-empty `regime_segments`. The Product-Complete gate is blocked by a condition the system cannot control — market volatility is external and probabilistic.

### Evidence Chain

| Artifact | Window | regime_segments | Status |
|----------|--------|-----------------|--------|
| `artifacts/regime_scorecards/2975/window_bank_2/replay-16a0a8f6d92f-0001` | pilot (~1min) | `segments: []` | unavailable |
| `artifacts/regime_scorecards/2975/window_bank_2/replay-577c2f83ac91-0001` | #3028 (~2min) | `segments: []` | unavailable |
| `artifacts/regime_scorecards/2975/window_bank_2/regime_scorecard_summary.json` | — | `any_regime_segments_available: false` | unavailable |
| Phase 2 observation (92.9 min) | 0 events | — | no chain produced |
| Phase 2 extended (9.4h) | 0 events | — | HOLD_NO_COMPARISON_GRADE_CHAIN_EXTENDED |

### Core Tension

The roadmap §6 A4 claims: *"Longer windows (1h+) will naturally produce regime segments."* Evidence from #3087 proves this is **probabilistic, not deterministic**: a ~9.4h window under flat market conditions produced zero paper chains. The Product-Complete gate depends on market conditions outside system control. CDB_CONSTITUTION.md §2 requires deterministic, reproducible system state — a gate that depends on external market luck contradicts this principle.

---

## Design Options Matrix

### Option A — Passive Natural-Market Observation

| Dimension | Assessment |
|-----------|------------|
| Evidence validity | **Highest** — real market, real strategy, real execution path |
| Repeatability | **Not repeatable by design** — depends on external market conditions |
| Time-to-result | **Unbounded** — days to weeks; #3087 ran 9.4h with 0 chains |
| Operational cost | Low per run, but unbounded total cost |
| Risk of indefinite HOLD | **High** — gate stays blocked until market cooperates |
| CDB Constitution alignment | **Violates determinism principle** — external dependency as gate condition |

**Verdict:** Passive-only observation is not a legitimate design strategy for a deterministic system. It is acceptable as one campaign type within a broader strategy, but must have explicit stop conditions to prevent indefinite blocking.

### Option B — Scheduled Volatility-Window Campaign

| Dimension | Assessment |
|-----------|------------|
| Evidence validity | **High** — real market, real strategy, real execution; same as A |
| Repeatability | **Partially** — market schedule is known, volatility clusters are predictable |
| Time-to-result | Hours to days — targeted windows increase probability of trigger |
| Operational cost | Moderate — requires campaign planning, documentation, and stack uptime |
| Cherry-picking risk | **Mitigated** by pre-documented criteria and counting failed campaigns |
| CDB Constitution alignment | **Acceptable** — deterministic campaign rules, transparent documentation |

**Campaign Policy:**

| Rule | Value |
|------|-------|
| Campaigns | Maximum 3 |
| Per-campaign duration | Maximum 8 hours |
| Total documented observation | Minimum 24 hours across all campaigns |
| Early stop | On first SIGNAL → DECISION → ORDER(paper_) → FILL chain |
| Escalation | After 3 failed campaigns → escalate to Option E (waiver/split) |

**Start Criteria (pre-documented, non-cherry-pick):**

*Primary (any one suffices):*
- BTCUSDT rolling 15-minute high-low range ≥ 0.35%
- BTCUSDT rolling 60-minute high-low range ≥ 0.75%
- Regime Service reports `TREND` or `HIGH_VOL_CHAOTIC` (canonical regime IDs from `services/regime/service.py`, verified in `core/replay/regime_analytics.py`: `KNOWN_REGIME_IDS = {"TREND", "RANGE", "HIGH_VOL_CHAOTIC", "UNKNOWN"}`)

*Secondary (schedule-only, not standalone evidence):*
- Pre-documented high-liquidity time windows: US equity session open zone (13:30–15:30 UTC), London-NY overlap (12:00–16:00 UTC)
- Macro/news windows only if named in campaign plan before start; no retroactive justification

**Anti-Cherry-Pick Rules:**
- Campaign-ID assigned before start
- Start criterion documented before start
- Planned duration documented before start
- Failed campaigns counted and documented — not discarded
- No strategy parameter lowering to induce breakout
- No stimulus runner, no synthetic market movement
- MOCK_TRADING=true, DRY_RUN=true, MEXC_TESTNET=true enforced at start and verified at end

**Verdict:** Primary executable path. Combines real-market evidence quality with bounded time commitment and explicit stop conditions.

### Option C — Controlled Stimulus (`paper_runtime_stimulus_runner`)

| Dimension | Assessment |
|-----------|------------|
| Evidence validity | **Pipeline/test only** — NOT valid for Product-Complete |
| Repeatability | **Fully deterministic** — fixture-driven, reproducible |
| Time-to-result | Minutes |
| Operational cost | Very low |
| Gate impact | **Cannot satisfy §5.2.4** — explicitly classified as `pipeline_test_evidence` |

**Classification:** The `paper_runtime_stimulus_runner.py` (789 lines, #2988) publishes a canonical BTCUSDT 1m candle fixture into the Redis `market_data` input surface to produce a SIGNAL → DECISION → ORDER → FILL chain under safe flags. It is a **pipeline validation tool**, not a Product-Complete evidence generator. Per #2974 product-complete review: "stimulus runner is classified as pipeline-test-only."

**Valid uses:**
- Pre-validate the end-to-end extraction → replay → compare → calibration → regime path works before a campaign
- Prove that pipeline infrastructure is functional; only market-dependent data is missing
- CI/CD regression testing of the ARVP pipeline

**Invalid uses:**
- As Product-Complete evidence for §5.2.4
- As `natural_paper_evidence`
- As `comparison-grade` paper reference window source

**Verdict:** Pipeline pre-validation only. Must be labeled `pipeline_test_evidence` in all outputs.

### Option D — Scenario-Backed ARVP Lab Evidence

| Dimension | Assessment |
|-----------|------------|
| Evidence validity | **Contract/proof only** — NOT valid for natural paper evidence |
| Repeatability | **Fully deterministic** — scenario packs, reproducible |
| Time-to-result | Hours (build scenario pack once) |
| Gate impact | **Cannot satisfy §5.2.4 as natural evidence** — valid for pipeline/regime contract proof |

**Valid uses:**
- Prove regime scorecard mechanics produce non-empty `regime_segments` when fed valid inputs
- Validate the regime analytics pipeline (extraction → segmentation → scoring) is functional
- Demonstrate contract compliance of the regime scorecard surface

**Invalid uses:**
- As `natural_paper_evidence` for Product-Complete
- As `comparison-grade` paper reference window source

**Verdict:** Secondary validation path for pipeline/regime contract proof. Not a substitute for natural market evidence.

### Option E — Roadmap §5.2.4 Waiver or Split

| Dimension | Assessment |
|-----------|------------|
| Evidence validity | **Policy decision** — not evidence, but a legitimate governance path |
| Repeatability | N/A |
| Time-to-result | Days (decision cycle) |
| Gate impact | **Would formally resolve the blocker** — but only through explicit policy, not fake evidence |

**When a waiver is legitimate:**
- After ≥3 documented, pre-planned campaigns fail to produce a chain
- The gate criterion is proven to depend on external market conditions outside system control
- The pipeline is independently proven functional via `pipeline_test_evidence`

**When a waiver is NOT legitimate:**
- Before exhausting the campaign path
- As a shortcut to declare Product-Complete without evidence
- Without documenting remaining uncertainties and mandatory follow-ups

**Proposed split (if waiver needed):**
- **§5.2.4a:** At least one window with non-empty `regime_segments` from `natural_paper_evidence` OR accepted waiver
- **§5.2.4b:** Pipeline-proven regime scorecard capability via `controlled_lab_evidence`
- Follow-up: separate roadmap amendment issue for formal gate definition change

**Verdict:** Legitimate governance fallback, not a shortcut. Only escalated after campaign exhaustion.

---

## Evidence Classes

These classes are formalized in this decision and must be enforced in future runners, CI, and evidence documentation.

| Class ID | Label | Definition | Product-Complete Valid? | Contract/Proof Valid? | Example |
|----------|-------|-----------|------------------------|----------------------|---------|
| `natural_paper_evidence` | Real paper runtime output under natural market conditions | Paper reference windows produced via real strategy/execution path against live market data; MOCK_TRADING=true, no stimulus, no parameter hack | **Yes** | Yes | #3087 Phase 2 observation; scheduled volatility campaign output |
| `controlled_lab_evidence` | Scenario-backed deterministic evidence from historical or pre-built data packs | Regime scorecards or pipeline artifacts produced from curated scenario packs with known inputs; no real market dependency | **No** | Yes | Scenario-pack-driven regime scorecards with non-empty `regime_segments` |
| `pipeline_test_evidence` | Synthetic stimulus or fixture-driven pipeline validation | Output from `paper_runtime_stimulus_runner.py` or similar fixture-based runners; proves pipeline works, not that products are complete | **No** | Yes (for pipeline) | Stimulus runner output; CI/CD regression evidence |
| `waiver_decision` | Explicit policy decision accepting non-fulfillment of a gate criterion | Documented governance decision; must list residual uncertainties and mandatory follow-ups | N/A | N/A | Roadmap amendment; gate split; explicit waiver |

### Enforcement Rules

1. Every ARVP evidence artifact must carry exactly one evidence class label.
2. Runners that produce `pipeline_test_evidence` must emit a warning header: `"evidence_class": "pipeline_test_evidence", "product_complete_valid": false`.
3. `natural_paper_evidence` must carry provenance: campaign ID, start criterion, MOCK/DRY/TESTNET flag values at start and end.
4. `controlled_lab_evidence` must declare its scenario source and that it is not natural market evidence.
5. `waiver_decision` must reference the design doc or roadmap amendment that authorizes it.
6. No evidence class may be silently upgraded — `pipeline_test_evidence` cannot become `natural_paper_evidence` by omission of the label.

---

## Design Decision

### Recommended Route: Hybrid B + C + E with Strict Sequencing

**Primary executable path: Option B — Scheduled Volatility-Window Campaign**

| Parameter | Value |
|-----------|-------|
| Strategy | `primary_breakout_v1` (unchanged — 0.5% breakout threshold, 15-minute lookback) |
| Symbol | BTCUSDT |
| Safety flags | MOCK_TRADING=true, DRY_RUN=true, MEXC_TESTNET=true |
| Max campaigns | 3 |
| Max per-campaign duration | 8 hours |
| Min total observation | 24 hours across campaigns |
| Start criteria | Pre-documented: rolling range thresholds OR regime `TREND`/`HIGH_VOL_CHAOTIC` |
| Early stop | On first complete SIGNAL → DECISION → ORDER(paper_) → FILL chain |
| On chain produced | Extract window → replay → compare → calibrate → regime scorecard → §5.2.4 satisfied |
| On 3 campaigns fail | Escalate to Option E |

**Pre-validation: Option C — Pipeline Proof via Stimulus Runner**

Before the first campaign, run the stimulus runner to prove the end-to-end pipeline works:
- Stimulus → SIGNAL → DECISION → ORDER → FILL → extraction → replay → compare → calibration → regime scorecard
- Document result as `pipeline_test_evidence`
- This removes pipeline defects as a confound for campaign failures

**Fallback: Option E — Waiver / Roadmap Amendment**

Only escalated after ≥3 documented campaign failures:
- Document that §5.2.4 depends on market conditions outside system control
- Propose gate split: §5.2.4a (natural or waived) + §5.2.4b (pipeline-proven)
- Create separate roadmap amendment issue
- Do NOT declare Product-Complete without explicit policy acceptance

### Explicitly Forbidden

| Action | Reason |
|--------|--------|
| Passive-only observation without stop condition | Violates CDB determinism; gate becomes indefinite market-wait |
| Strategy parameter lowering (e.g. breakout threshold < 0.5%) | Parameter hack as gate cheat; invalidates evidence quality |
| Stimulus runner output as Product-Complete evidence | Violates evidence class boundary; synthetic is not natural |
| Synthetic or ersatz data as `natural_paper_evidence` | Invalidates comparison-grade contract |
| Cherry-picking successful campaigns, discarding failures | Evidence bias; must count all campaigns |
| Any Live-Go / Echtgeld implication | LR remains NO-GO; Product-Complete is NOT Live-Go |

### Why Not Option A Alone

Passive-only observation with no stop condition turns the Product-Complete gate into an indefinite market-waiting state. This violates CDB_CONSTITUTION.md §2 ("Jeder Systemzustand muss reproduzierbar sein") by making a gate criterion dependent on non-deterministic external conditions. The campaign framework (B) retains Option A's evidence quality while adding deterministic stop conditions and a bounded time commitment.

---

## Recommended Executable Route

### Step-by-Step Execution

| Step | Action | Issue | Evidence Class |
|------|--------|-------|----------------|
| 1 | Run stimulus runner → prove pipeline works end-to-end | This doc § Pre-validation | `pipeline_test_evidence` |
| 2 | Plan Campaign #1 — document start criterion, campaign ID, duration | Campaign follow-up | — |
| 3 | Execute Campaign #1 (≤8h) under safe flags | Campaign follow-up | `natural_paper_evidence` |
| 4a | **If chain produced:** Extract window → replay → compare → calibrate → regime scorecard → **§5.2.4 met** | #3087 | `natural_paper_evidence` |
| 4b | **If chain not produced:** Document failure. Plan Campaign #2 | Campaign follow-up | — |
| 5 | Repeat steps 2–4b for Campaigns #2 and #3 | Campaign follow-up | — |
| 6 | **If all 3 fail:** Escalate to waiver/split → create roadmap amendment issue | Waiver follow-up | `waiver_decision` |

### Stop Conditions

| Condition | Action |
|-----------|--------|
| Chain produced in any campaign | Stop campaigns; proceed to extraction and regime scorecard |
| 3 campaigns complete, 0 chains | Escalate to Option E; do NOT fake evidence |
| Safety flags do not verify MOCK/DRY/TESTNET at campaign start | Abort campaign; do not proceed |
| Stack unhealthy | Abort campaign; fix stack first |
| Any strategy/parameter change attempted | Reject; campaigns must use unmodified `primary_breakout_v1` |
| Stimulus or synthetic data attempted as campaign result | Reject; evidence class violation |

---

## Geänderte Dateien

| File | Action | Lines |
|------|--------|-------|
| `docs/evidence/arvp_deterministic_window_production_3094.md` | **CREATE** | This document (~300 lines) |

No other files modified. This is a design/policy document only.

---

## Validation / Checks

```bash
# Diff check
git diff --check

# Safety scan — no live/synthetic/secret boundaries touched
rg -n "Live-Go|Echtgeld|LIVE_TRADING_CONFIRMED|MEXC_TESTNET=false|MOCK_TRADING=false|DRY_RUN=false|synthetic.*Product-Complete|stimulus.*Product-Complete" docs/evidence/arvp_deterministic_window_production_3094.md
```

Expected:
- Zero matches for safety-violating patterns
- No secrets in output
- No Live-Go / Echtgeld implications
- Synthetic/stimulus evidence not presented as unlabelled Product-Complete evidence

---

## Follow-up Issues

| Issue | Title | Rationale | Deduplicated Against |
|-------|-------|-----------|---------------------|
| #3095 | `[ARVP][WINDOW][EXECUTE] Run scheduled volatility-window campaign for primary_breakout_v1` | Executable path for Option B — 3 campaigns, pre-documented criteria, bounded runtime | #3087 (parent — this is the HOW), #3091 (data acquisition — orthogonal), #3092 (research — orthogonal) |
| #3096 | `[ARVP][POLICY] Split natural-paper evidence from controlled lab evidence` | Policy enforcement — implement evidence class labels in runners/CI, ensure no silent class upgrades | #2974 (closed review — new policy scope not covered) |

**Roadmap amendment issue:** NOT created now. Escalated only after ≥3 campaign failures per Option E. Documented in this design as future escalation path.

---

## Safety Boundaries (all affirmed)

| Boundary | Status |
|----------|--------|
| LR remains **NO-GO** | Confirmed throughout document |
| Product-complete is NOT Live-Go | Confirmed |
| Board stage `trade-capable` is NOT Live-Go | Confirmed |
| No Echtgeld-Go | Confirmed |
| No runtime/stack start/stop/restart | Confirmed — design doc only |
| No Docker/compose changes | Confirmed |
| No live exchange order execution | Confirmed |
| No productive DB writes | Confirmed |
| No strategy parameter changes | Confirmed — `primary_breakout_v1` remains unchanged |
| No stimulus as Product-Complete evidence | Explicitly forbidden |
| No synthetic evidence as §5.2.4 fulfilment | Explicitly forbidden |
| No secrets in outputs | Confirmed |

---

## Restunsicherheiten

1. **Markets may stay flat for weeks.** Even 3 targeted volatility campaigns may fail to produce a chain. The waiver framework (Option E) is the legitimate governance resolution for this case — not fake evidence.
2. **Waiver legitimacy.** A roadmap amendment must be transparent, documented, and must not be used as a backdoor to skip Product-Complete. Follow-up for roadmap amendment is a mandatory escalation, not an optional shortcut.
3. **Evidence class enforcement.** The distinction between `pipeline_test_evidence` and `natural_paper_evidence` must be enforced in runners and CI, not just documentation. The follow-up policy issue must scope implementation of label enforcement.
4. **Single-strategy, single-symbol narrowness.** Only `primary_breakout_v1` / BTCUSDT is evaluated. Multi-strategy or multi-symbol coverage is a stretch goal per roadmap, not a Product-Complete blocker.
5. **High-vol regime entry blocking.** `HIGH_VOL_CHAOTIC` (regime_id=2) is in `blocked_regimes` per the decision contract. A breakout during this regime fires a SIGNAL but the DECISION gate may reject entry. Campaigns should prefer `TREND` regime windows where possible, but either regime counts for the volatility criterion.
6. **Venue mismatch remains.** Same-venue MEXC data for #3028 is unavailable (#3086, #3091, #3092). Future campaign windows should use the persistent MEXC capture pipeline (#3091) to avoid venue_mismatch confounds.

---

## References

- #3094 — This design issue
- #3087 — Parent: produce longer comparison-grade paper reference window(s)
- #2974 — Product-complete review (DONE_REVIEW_COMPLETED_PRODUCT_COMPLETE_BLOCKED)
- #1900 — ARVP north-star anchor
- #3091 — Capture future MEXC candles (data acquisition)
- #3092 — Research external MEXC data providers
- #3086 — Acquire MEXC same-venue candle data
- `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md` — §5 product-complete criteria, §6 A4, §8 sequencing
- `docs/evidence/arvp_product_complete_review_2974.md` — Gate matrix, blocker classification
- `docs/evidence/arvp_regime_scorecards_2975_after_2973.md` — Regime scorecard status (both unavailable)
- `docs/runbooks/ARVP_OPERATOR_RUNBOOK.md` — ARVP end-to-end operating order
- `docs/governance/arvp_paper_reference_contract.md` — comparison-grade window definition
- `services/validation/paper_runtime_stimulus_runner.py` — Stimulus runner (pipeline-test-only)
- `services/validation/paper_reference_window_runner.py` — Paper reference extraction runner
- `services/regime/service.py` — Canonical regime IDs: `TREND`, `RANGE`, `HIGH_VOL_CHAOTIC`, `UNKNOWN`
- `core/replay/regime_analytics.py` — `KNOWN_REGIME_IDS` frozenset
- `knowledge/governance/CDB_CONSTITUTION.md` — §2 determinism principle
- `docs/runbooks/CONTROL_REGISTER.md` — Board stage `trade-capable`, LR NO-GO
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — Canonical LR verdict

---

## Status

`DONE_DESIGN_COMPLETED`

- Design decision for #3094 is **complete**.
- Recommended executable route: Option B (scheduled volatility campaigns) with Option C (pipeline pre-validation) and Option E (waiver framework as fallback).
- Evidence classes formalized: `natural_paper_evidence`, `controlled_lab_evidence`, `pipeline_test_evidence`, `waiver_decision`.
- #3087 receives a clear executable path: 3 campaigns, pre-documented criteria, bounded time, explicit stop conditions.
- #2974 remains Product-Complete BLOCKED until natural paper evidence with non-empty `regime_segments` is produced OR a formal waiver is accepted.
- #1900 Phase A status unchanged: BLOCKED by §5.2.4.
