# ARVP Tri-Candidate Scenario Evidence Rollup after #3208

**Issue:** [#3210](https://github.com/jannekbuengener/Claire_de_Binare/issues/3210)
**Parent:** [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
**Refs:** [#3208](https://github.com/jannekbuengener/Claire_de_Binare/issues/3208), [#3202](https://github.com/jannekbuengener/Claire_de_Binare/issues/3202), [#3200](https://github.com/jannekbuengener/Claire_de_Binare/issues/3200), [#3198](https://github.com/jannekbuengener/Claire_de_Binare/issues/3198), [#3196](https://github.com/jannekbuengener/Claire_de_Binare/issues/3196), [#3194](https://github.com/jannekbuengener/Claire_de_Binare/issues/3194), [#3191](https://github.com/jannekbuengener/Claire_de_Binare/issues/3191), [#3188](https://github.com/jannekbuengener/Claire_de_Binare/issues/3188), [#3186](https://github.com/jannekbuengener/Claire_de_Binare/issues/3186), [#3183](https://github.com/jannekbuengener/Claire_de_Binare/issues/3183), [#3170](https://github.com/jannekbuengener/Claire_de_Binare/issues/3170)
**Execution date:** 2026-06-15
**Status:** DONE_EVIDENCE_ROLLUP_CREATED
**Target Befund:** HOLD_NO_PROMOTABLE_CANDIDATE

---

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - read: canonical read-order (AGENTS.md, agents/AGENTS.md, governance, WORKING_REPO_CANON.md, CURRENT_STATUS ledger, LR-AUDIT-STATUS, CONTROL_REGISTER, OPEN_CODE_AGENTS)
  - bash: git fetch origin --prune; git status -sb; git rev-parse HEAD; git rev-parse origin/main
  - bash/gh: gh pr list --state open; gh issue view 3210, 1900, 2985, 2977, 1445
  - read: docs/evidence/arvp_momentum_capture_scenario_group_evidence_3208.md
  - read: docs/evidence/arvp_momentum_capture_replay_adapter_evidence_3202.md
  - read: docs/evidence/arvp_rmr_scenario_1_record_suite_3200.md
  - read: docs/evidence/arvp_rmr_single_run_provenance_bundle_path_3198.md
  - read: docs/evidence/arvp_range_mean_reversion_replay_adapter_evidence_3196.md
  - read: docs/evidence/arvp_first_economics_gated_scenario_inventory_3191.md
  - read: docs/evidence/arvp_post_tri_regime_candidate_discovery_axis_3188.md
  - read: docs/evidence/arvp_next_candidate_selection_after_primary_breakout_park_3186.md
  - read: docs/evidence/arvp_exit_regime_decay_diagnosis_3183.md
  - read: docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md
  - read: docs/evidence/arvp_roadmap_reconcile_after_primary_breakout_park_2985_1900.md
  - read: docs/live-readiness/LR-050-FINAL-RECONCILE.md
  - task: explore subagent for evidence-doc summaries
records_or_results:
  - Git: HEAD == origin/main == 4f34d09a707b603c9cf24d1115aeecf5ab1500cc at start (unchanged from plan)
  - GitHub: #3210 OPEN, #1900 OPEN, #2985 OPEN, #2977 OPEN, #1445 OPEN
  - Open PRs: Dependabot only (#3204-#3207)
  - All required evidence docs present (11/11)
  - Target artifact does not exist yet; branch docs/tri-candidate-rollup-3210 not created yet
repo_crosscheck:
  - All ARVP evidence docs from #3170-#3208 exist on main
  - Economics gate map from #3191 shows G7 FAIL for all three candidates
  - #3208 momentum scenario-group: 3/3 succeeded but 0 signals/0 trades across all packs
  - #3200 RMR scenario run: 0 trades / 0.0R
  - LR-050-FINAL-RECONCILE.md: 7 open blocker_before_live rows, NO-GO verdict
impact_on_plan:
  - This rollup consolidates all tri-candidate scenario/adapter evidence into one control document
  - No replay rerun is justified; all three candidates remain PARKED
  - #2977 LR-050 refresh remains BLOCKED
limitations:
  - repo-only; no SurrealDB/MCP/DB-backed evidence
  - git fetch origin --prune was executed at start; remote state is fresh
  - Foreign untracked surfaces (.opencode/plans/, docs/decisions/) exist but are outside scope
```

---

## Bootloader-/Read-Order-Evidence

Canonical read-order executed according to `agents/AGENTS.md`:

1. `knowledge/governance/CDB_CONSTITUTION.md` — oberste Autoritaet: deterministisches, reproduzierbares System.
2. `knowledge/governance/CDB_GOVERNANCE.md` — Rollenmodell, Betriebsmodi, Change-Control.
3. `knowledge/governance/CDB_AGENT_POLICY.md` §4 — Write-Gates, Single-Writer Lock, HARD STOP.
4. `knowledge/governance/SYSTEM_INVARIANTS.md` — INV-001 bis INV-020: Fail-Closed, Determinismus, Contract Drift Protection.
5. `knowledge/CDB_KNOWLEDGE_HUB.md` — Shared Decisions & Agent Handoffs.
6. `docs/meta/WORKING_REPO_CANON.md` — Working Repo ist produktiver Canon; Status-SSOT-Rules.
7. `CURRENT_STATUS.md` — als Ledger behandelt, nicht als Live-Wahrheit.
8. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — LR remains NO-GO.
9. `docs/runbooks/CONTROL_REGISTER.md` — Stage `trade-capable` nicht Live-Go.
10. `agents/OPEN_CODE_AGENTS.md` — Brain Evidence Gate, Skill Routing.

**Operative Grenzen bestaetigt:**
- LR remains NO-GO. Keine Echtgeld-Freigabe.
- Board-Stage `trade-capable` orthogonal zu LR; autorisiert kein Live-Kapital.
- `DELIVERY_APPROVED.yaml` bleibt human-only.
- `CURRENT_STATUS.md` ist Ledger, nicht Live-Truth.

---

## Live-Lage

Stand: 2026-06-15 nach `git fetch origin --prune` und GH-Live-Pruefung:

| Item | Status | Ref |
|------|--------|-----|
| HEAD / origin/main | `4f34d09a707b603c9cf24d1115aeecf5ab1500cc` | equal |
| Dirty foreign surfaces | `.opencode/plans/`, `docs/decisions/` | untouched |
| `#3210` | **OPEN** | target issue |
| `#1900` | **OPEN** | parent epic |
| `#2985` | **OPEN** | live-roadmap meta |
| `#2977` | **OPEN** | LR-050 refresh |
| `#1445` | **OPEN** | control board verdict |
| Open PRs | Dependabot only: `#3204`-`#3207` | non-blocking queue noise |
| LR verdict | **NO-GO** | unchanged |
| Board stage | `trade-capable` | not Live-Go |

---

## Candidate Evidence Inventory

### primary_breakout_v1

| Surface | Status | Evidence |
|---------|--------|----------|
| Controlled-lab chain (`#3172`-`#3184`) | DONE | `docs/evidence/arvp_roadmap_reconcile_after_primary_breakout_park_2985_1900.md` |
| Exit regime decay diagnosis | DONE | `docs/evidence/arvp_exit_regime_decay_diagnosis_3183.md` |
| Break-even / fee-free proxy | `R=-0.075` (negative) | `docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md` |
| **Status** | **PARKED** | Structural regime-instability + regime-unaware exit; no tuning allowed per `#3181` |
| Remaining scenario gap | Stress comparison (baseline vs pessimistic) not executed | Known gap from `docs/evidence/arvp_first_economics_gated_scenario_inventory_3191.md` |

### range_mean_reversion_v1

| Surface | Status | Evidence |
|---------|--------|----------|
| Replay adapter wired | DONE | `docs/evidence/arvp_range_mean_reversion_replay_adapter_evidence_3196.md` |
| Single-run provenance bundle | DONE | `docs/evidence/arvp_rmr_single_run_provenance_bundle_path_3198.md` |
| Scenario 1-record suite | DONE (0 trades) | `docs/evidence/arvp_rmr_scenario_1_record_suite_3200.md` |
| Fee-free proxy | `R=-0.347` (negative) | `docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md` |
| Scenario-group execution | NOT_EXECUTED | No candidate-specific run; execution coverage was proved via PB1 dataset |
| **Status** | **PARKED** | Economics deeply negative; no promotion path |
| Remaining scenario gap | Full scenario-group execution | Not justified while economics negative |

### momentum_capture_v1

| Surface | Status | Evidence |
|---------|--------|----------|
| Replay adapter wired | DONE | `docs/evidence/arvp_momentum_capture_replay_adapter_evidence_3202.md` |
| Scenario-group execution | DONE (3/3, 0 trades) | `docs/evidence/arvp_momentum_capture_scenario_group_evidence_3208.md` |
| Fee-free proxy | `R=-0.206` (negative) | `docs/evidence/profitability_break_even_boundary_cost_slippage_sensitivity_3170.md` |
| **Status** | **PARKED** | Execution coverage proven but economically non-viable |
| Remaining scenario gap | Stress delta undifferentiated (0 trades in all packs) | Not a blocker for closure |

---

## Scenario / Adapter Coverage Matrix

| Scenario Pack | PB1 | RMR | MC1 |
|---------------|-----|-----|-----|
| baseline | REPLAYABLE (run_003/004/005) | REPLAYABLE (#3200) | REPLAYABLE (#3208, 0 trades) |
| pessimistic_execution | NOT_TESTED (gap) | NOT_TESTED | REPLAYABLE (#3208, 0 trades) |
| delayed_execution | NOT_TESTED | NOT_TESTED | NOT_TESTED |
| low_liquidity | NOT_TESTED | NOT_TESTED | NOT_TESTED |
| feed_gap | NOT_TESTED | NOT_TESTED | REPLAYABLE (#3208, 0 trades) |

**Befund:** Momentum capture has the fullest scenario coverage (3/5 packs executed), but all produced 0 signals / 0 trades. PB1 and RMR lack any scenario-group execution. The shared scenario-pack infrastructure (`scenario_packs.py`, `strategy_replay_runner.py`) is confirmed working for all three candidates. No execution blocker exists; the gap is in execution breadth, not technical feasibility.

---

## Economics Gate Impact

| Gate | Condition | Status | Evidence |
|------|-----------|--------|----------|
| G1 | No stale PARK promotion | **PASS** — all 3 PARKED | Issue state + evidence docs |
| G2 | No same-loop Candidate #4 | **PASS** — FULL_STOP_ON_THIS_LOOP | `#3170` |
| G3 | Economics before implementation | **BLOCKED** — gate exists, never applied | `#3039` Economics Model |
| G5 | ranking_ready=false without full inputs | **PASS** — all 3 have `ranking_ready=false` | Seed JSONs on main |
| G7 | Fee-Free Proxy >= 0.0R | **FAIL** — all 3 negative | `#3170` boundary table |
| G8 | Stress comparison baseline vs pessimistic | **MISSING** — never executed | `scenario_packs.py` exists, no run |

**Key result:** G7 remains decisive. All three candidates remain negative at the fee-free proxy:
- `primary_breakout_v1`: `R=-0.075` (needs +0.075R uplift)
- `range_mean_reversion_v1`: `R=-0.347` (needs +0.347R uplift)
- `momentum_capture_v1`: `R=-0.206` (needs +0.206R uplift)

The scenario/adapter work after `#3191` (issues `#3194`-`#3208`) closed bounded evidence-run gaps but did not change any economics gate status. No candidate moved closer to G7 PASS.

---

## Final Candidate Status

- `primary_breakout_v1 remains PARKED.`
- `range_mean_reversion_v1 remains PARKED.`
- `momentum_capture_v1 remains PARKED.`
- `BTCUSDT/MEXC/1m long-only loop remains FULL_STOP_ON_THIS_LOOP unless new evidence says otherwise.`
- `No candidate is promotable.`
- `LR remains NO-GO.`
- `Board stage trade-capable is not Live-Go.`
- `No Product-Complete claim.`
- `No natural_paper_evidence claim.`
- `No Live-Go / Echtgeld-Go.`

---

## #2977 LR-050 Refresh Decision

**Target Issue:** `#2977` — `[LR-050][REFRESH] Re-evaluate LR-050 blockers with ARVP evidence`

**Verdict: BLOCKED**

**Begruendung:**

1. **ARVP Phase A is not Product-Complete.** The `#3172-#3184` controlled-lab chain produced bounded evidence about regime attribution and failure mode but did not clear the Product-Complete gate. `natural_paper_evidence` (Roadmap §5.2.4) remains absent.

2. **No promotable candidate exists.** All three ARVP candidates (PB1, RMR, MC1) remain PARKED. No candidate satisfies the economics gate G7 (Fee-Free Proxy >= 0.0R). A refresh without a promotable candidate cannot change the LR-050 blocker state.

3. **LR-050-FINAL-RECONCILE.md lists 7 open `blocker_before_live` items.** None of these have been closed by the ARVP scenario/adapter evidence chain (#3191-#3208). Specifically:
   - Runtime dry-run evidence: not executed
   - Operator Receiver Proof: missing
   - Concrete canary values: TBD
   - Venue/endpoint semantics: externally unverified
   - Exact Human Approval: absent
   - Secret/permission readiness: open where not proven

4. **The admissible evidence from this tri-candidate rollup is negative closure, not positive refresh material.** The strongest finding is that all three candidates are unpromotable. That does not unlock any LR-050 gate.

5. **Consistent with #3170 FULL_STOP_ON_THIS_LOOP and #3188 scenario-pack-first axis.** Until the next axis produces a candidate that passes G7 (or a different economics gate), LR-050 stays NO-GO.

**Consequence:** `#2977` remains OPEN. No LR-050 refresh execution is justified. The next legitimate path to LR-050 reconsideration is a successful scenario-pack-first candidate that passes economics and reaches paper-mode evidence.

---

## Remaining Blockers

| Blocker | Scope | Status | Source |
|---------|-------|--------|--------|
| G7 Fee-Free Proxy < 0.0R | All 3 candidates | **OPEN** — negative | `#3170` |
| G3 Economics before implementation | Cross-candidate | **OPEN** — gate exists, never applied | `#3191` gate map |
| Stress comparison not executed | PB1, RMR | **OPEN** — missing evidence | `#3191` |
| LR-050 runtime dry-run evidence | LR-050 | **OPEN** — not executed | `LR-050-FINAL-RECONCILE.md` |
| LR-050 Operator Receiver Proof | LR-050 | **OPEN** — missing | `LR-050-FINAL-RECONCILE.md` |
| LR-050 Concrete canary values | LR-050 | **OPEN** — TBD | `LR-050-FINAL-RECONCILE.md` |
| LR-050 Venue/endpoint semantics | LR-050 | **OPEN** — unverified | `LR-050-FINAL-RECONCILE.md` |
| LR-050 Human Approval | LR-050 | **OPEN** — absent | `LR-050-FINAL-RECONCILE.md` |
| natural_paper_evidence | ARVP Phase A | **OPEN** — absent | `#2974`, `#3087` |
| Product-Complete gate | ARVP Phase A | **OPEN** — blocked | `#2974` |
| #1905 unpark | Governance | **BLOCKED** — must not be unparked from this rollup | `#3186` |

**Key blocker pattern:** The remaining blockers are structural (economics, LR-050 infrastructure, product-complete gate), not evidence-run gaps. The scenario/adapter work (#3194-#3208) closed bounded execution-coverage gaps but left all structural blockers untouched.

---

## Next Bounded Slice Recommendation

**Recommendation: HOLD_NO_PROMOTABLE_CANDIDATE**

**Begruendung:**

1. **No promotable candidate exists** after exhaustive tri-candidate evidence chain (#3170-#3208). All three PARKED candidates remain negative at the fee-free proxy.

2. **The scenario/adapter axis is exhausted for this loop.** All three candidates have proven replay adapter coverage. Momentum has full scenario-group execution. RMR has single-run provenance. PB1 has the deepest controlled-lab chain. No remaining evidence-run gap changes the economics verdict.

3. **#3188 already identified the next axis: scenario-pack-first (economics-gated).** That axis was exercised (#3189 spec, #3191 inventory, #3194-#3208 evidence closure). The scenario-pack-first spec is delivered. The next legitimate move would be a new research-axis issue — outside the exhausted BTCUSDT/MEXC/1m long-only loop.

4. **No same-loop Candidate #4 is justified.** `#3170` FULL_STOP_ON_THIS_LOOP remains the binding authority. A fourth candidate on the same symbol/venue/timeframe/direction axis would repeat the failure pattern.

5. **#2977 LR-050 refresh remains BLOCKED.** The refresh question is answered by this rollup's consolidated evidence: no promotable candidate, no ARVP Phase A product-complete claim, no LR-050 blocker closure. Refreshing without a successful candidate would be an empty exercise.

**Falls spaeter weitergearbeitet wird:**
- Der naechste legitime Schritt ist ein neuer, separat begruendeter Research-Axis-Issue ausserhalb der erschöpften BTCUSDT/MEXC/1m long-only-Schleife.
- Voraussetzung: ein Kandidat, der die Economics Gate G7 (Fee-Free Proxy >= 0.0R) passiert.
- Kein Replay, keine Code-Aenderung, keine Optimierung, keine Candidate-Promotion aus diesem Rollup.

---

## Safety Boundaries

- LR remains NO-GO.
- Board stage trade-capable is not Live-Go.
- No Product-Complete claim.
- No natural_paper_evidence claim.
- No Live-Go / Echtgeld-Go.
- No candidate promotion.
- No strategy implementation or signal changes.
- No optimization.
- No runtime services, Docker, DB, or MCP work.
- No same-loop Candidate #4 on BTCUSDT/MEXC/1m long-only.
- No #1905 unpark.
- No primary_breakout_v1 rescue or tuning path is opened.
- #2977 LR-050 refresh remains BLOCKED; no refresh execution is authorized.

---

## Restunsicherheiten

1. All three candidates remain PARKED after exhaustive scenario/adapter evidence. No hidden economics-positive signal was found in any of the scenario-group runs.
2. The scenario-pack-first axis (#3188) was exercised through spec, inventory, and evidence closure. Whether a future candidate on a different axis can pass G7 remains unknown and cannot be inferred from this rollup.
3. The stress comparison gap (baseline vs pessimistic_execution) for PB1 and RMR remains unfilled. Closing it would confirm execution coverage but is not expected to change the economics verdict given the fee-free proxy results.
4. Momentum capture's zero-signal outcome across all three scenario packs is a data point about this dataset under this strategy — not proof that momentum capture cannot work in any configuration on any axis.
5. Dependabot PRs #3204-#3207 remain open as queue noise. If any introduces a breaking change, it would block this PR's merge path but does not change the evidence findings.
6. A future research-axis candidate would need to pass G7 before any path to paper-mode, LR-050, or promotion becomes legitimate. This rollup does not pre-judge which axis or candidate that would be.
