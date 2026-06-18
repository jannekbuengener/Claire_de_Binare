# ARVP Window Bank Inventory — #3212

Status Class: Scoped evidence / control inventory
Issue: #3212
Parent: #1900
Control Refs: #2985, #2977, #3210, #3211
Live-Readiness: NO-GO
Echtgeld: not authorized

---

## 1. Brain Evidence Block

```text
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - read: AGENTS.md, agents/AGENTS.md, canonical read-order files
  - read: docs/governance/arvp_paper_reference_contract.md
  - read: docs/evidence/arvp_tri_candidate_scenario_evidence_rollup_after_3208.md
  - read: docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md
  - read: knowledge/governance/ARVP_PRODUCT_INTENT.md
  - read: docs/evidence/arvp_window_bank_2961_extraction_2026-06-04.md
  - read: docs/evidence/arvp_calibration_batch_2961_2026-06-04.md
  - read: docs/evidence/arvp_batch_compare_2971_after_2961.md
  - read: docs/evidence/arvp_regime_scorecards_2975_after_2973.md
  - read: docs/evidence/arvp_calibration_pilot_1932_2026-04-26.md
  - read: docs/evidence/arvp_readonly_preflight_2967_closeout.md
  - read: docs/evidence/arvp_2961_paper_window_runtime_preflight_2026-06-04.md
  - read: committed artifact JSON/summary surfaces under artifacts/
  - grep/glob: paper_reference_window, calibration, comparison, regime_segments, correlation_ledger
  - bash: git fetch origin --prune; git status -sb; git rev-parse HEAD; git rev-parse origin/main; gh issue/pr views
records_or_results:
  - HEAD == origin/main == 2ddb67a6687a08bc860c3553a01950ebf0fd6467 at session start
  - #3212 OPEN; #2985 OPEN; #1900 OPEN; #2977 OPEN; #3210 CLOSED; #3211 MERGED
  - Open PRs are Dependabot-only
  - Committed window-bank surfaces found under artifacts/ and docs/evidence/
  - No DB-/MCP-/SurrealDB-backed read executed in this slice
repo_crosscheck:
  - docs/governance/arvp_paper_reference_contract.md
  - core/replay/paper_reference_window_export.py
  - core/replay/replay_vs_paper_compare.py
  - services/validation/paper_reference_window_runner.py
  - artifacts/arvp_replay_paper_pilot/1909_smoke_20260424/paper_reference_window.json
  - artifacts/paper_reference_windows/paper_reference_window.json
  - artifacts/batch_compare/2971/window_bank_2/batch_compare_summary.json
  - artifacts/regime_scorecards/2975/window_bank_2/regime_scorecard_summary.json
impact_on_plan:
  - The inventory is resolved from repo-backed evidence only
  - No new export is attempted because readonly correlation_ledger access in this session would require secrets/DB access
  - The strongest repo-backed conclusion is insufficient window-bank readiness, not Product-Complete
limitations:
  - No live readonly correlation_ledger session in this slice
  - Contract shape on main is not perfectly aligned across doc, exporter output, and consumer expectations
  - No runtime, Docker, workflow_dispatch, DB mutation, or secrets access performed
```

---

## 2. Bootloader-/Read-Order-Evidence

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

Verified guardrails:

- `CURRENT_STATUS.md` treated as ledger, not live truth.
- LR SSOT remains `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
- Board stage `trade-capable` is not Live-Go.
- LR remains NO-GO.

---

## 3. Live-Lage

Live state after `git fetch origin --prune` and GitHub checks:

| Item | Status |
|---|---|
| Branch at session start | `main` |
| HEAD / origin/main | `2ddb67a6687a08bc860c3553a01950ebf0fd6467` / equal |
| Working tree | dirty by foreign untracked surfaces `.opencode/plans/`, `docs/decisions/` only; untouched |
| #3212 | OPEN |
| #2985 | OPEN, reconciled to #3210/#3211 truth |
| #1900 | OPEN |
| #2977 | OPEN / BLOCKED |
| #3210 | CLOSED |
| #3211 | MERGED |
| Open PRs | Dependabot-only |
| LR verdict | NO-GO |
| Board stage | `trade-capable` (not Live-Go) |

No live-truth conflict was found between GitHub and repo-backed ARVP evidence.

---

## 4. Scope Boundary

In scope:

- Read-only inventory of repo-backed paper-reference, compare, calibration, and regime evidence surfaces.
- Contract check against `paper_reference_window.v1` as documented and implemented on main.
- Per-window suitability assessment.
- Explicit A2/A3/A4 readiness decision.

Out of scope:

- No new strategy candidate.
- No Candidate #4.
- No 5m/15m discovery.
- No PB1/RMR/Momentum rescue.
- No runtime start.
- No Docker/Compose orchestration.
- No workflow dispatch.
- No DB mutation.
- No MCP mutation.
- No secrets/env dump.
- No Live-Go / Echtgeld-Go.

---

## 5. Source Inventory

| Surface | Class | Repo-backed | Notes |
|---|---|---:|---|
| `docs/governance/arvp_paper_reference_contract.md` | normative contract doc | yes | Canonical contract text for `paper_reference_window.v1` |
| `core/replay/paper_reference_window_export.py` | implementation/exporter | yes | Current exporter enforces SIGNAL-anchor chain integrity and emits flattened extraction metadata |
| `core/replay/replay_vs_paper_compare.py` | implementation/consumer | yes | Current consumer accepts `events` + metadata and does not require `paper_selector` |
| `services/validation/paper_reference_window_runner.py` | readonly runner | yes | Requires `POSTGRES_READONLY_PASSWORD_DSN` + `cdb_readonly`; not exercised in this slice |
| `artifacts/arvp_replay_paper_pilot/1909_smoke_20260424/paper_reference_window.json` | pilot paper window artifact | yes | Legacy inline export shape; ORDER/FILL only |
| `artifacts/paper_reference_windows/paper_reference_window.json` | committed paper window artifact | yes | Strongest repo-backed current window artifact; complete SIGNAL/DECISION/ORDER/FILL chain |
| `docs/evidence/arvp_paper_reference_window_2968_after_3026.json` | evidence copy of #3028 window | yes | Mirrors committed artifact shape |
| `docs/evidence/arvp_calibration_pilot_1932_2026-04-26.md` | pilot evidence summary | yes | Explicitly states local source artifacts and unavailable `regime_segments` |
| `docs/evidence/arvp_calibration_batch_2961_2026-06-04.md` | 2-window bank seed summary | yes | States current bank = pilot + #3028; 3+ target unmet |
| `docs/evidence/arvp_batch_compare_2971_after_2961.md` | batch compare summary | yes | 2-window compare delivered; batch partial only |
| `artifacts/batch_compare/2971/window_bank_2/batch_compare_summary.json` | machine-readable compare summary | yes | Per-window fingerprints and cross-window deltas |
| `docs/evidence/arvp_drift_classification_2973_after_2971.md` | drift summary | yes | Aggregate certainty limited |
| `docs/evidence/arvp_regime_scorecards_2975_after_2973.md` | regime summary | yes | Both windows `unavailable` for regime scorecards |
| `artifacts/regime_scorecards/2975/window_bank_2/regime_scorecard_summary.json` | machine-readable regime summary | yes | `any_regime_segments_available=false` |
| `docs/evidence/arvp_window_bank_2961_extraction_2026-06-04.md` | prior readonly extraction audit | yes | Historic readonly DB findings; not re-executed here |
| `docs/evidence/arvp_readonly_preflight_2967_closeout.md` | readonly preflight closeout | yes | Infra/runner validated historically; no direct DB verification in this slice |

Key inventory result:

- Repo-backed surfaces prove a usable 2-window bank exists.
- Repo-backed surfaces do not prove a regime-capable window bank.
- Readonly correlation_ledger extraction is not re-run in this slice because it would require secret-backed DSN access not granted here.

---

## 6. paper_reference_window.v1 Contract Check

### 6.1 Normative vs implemented contract on main

The repo contains three relevant contract surfaces:

| Surface | Current behavior |
|---|---|
| `docs/governance/arvp_paper_reference_contract.md` | Requires explicit `paper_selector`; requires comparison-grade `correlation_ledger` provenance; describes fail-closed window semantics |
| `core/replay/paper_reference_window_export.py` | Enforces SIGNAL-anchor chain integrity, paper-prefixed ORDER/FILL, homogeneity guards, flattened extraction metadata fields (`source_table`, `source_query_intent`, `extracted_at_utc`, `extracted_by`), optional `causal_context_events` |
| `core/replay/replay_vs_paper_compare.py` | Accepts `arvp_paper_reference_window.v1` JSON with non-empty `events`; validates symbol/strategy/timestamp consistency; counts SIGNAL/ORDER/FILL; does not require `paper_selector` |

### 6.2 Contract finding

There is repo-backed contract-shape drift on main:

- The contract doc still describes a `paper_selector` object as required.
- The current exporter does **not** emit `paper_selector`; it emits flattened extraction metadata instead.
- The current consumer accepts the exporter shape.
- The pilot artifact uses yet another shape: nested `provenance` + `paper_selector`, but only ORDER/FILL events.

### 6.3 Implication for this inventory

This slice therefore uses a conservative rating model:

- `PASS`: not assigned unless a window clearly satisfies both the repo-backed evidence purpose and the documented contract without material shape or chain ambiguity.
- `WARN`: assigned where evidence is usable and replay/calibration surfaces already rely on it, but the contract shape or completeness is materially ambiguous.
- `FAIL`: assigned where a window would not support bounded A2/A3/A4 progression.

Given the current repo state, both committed windows are **usable**, but neither is clean enough to rate as unqualified `PASS` against the documented contract text.

---

## 7. Window Suitability Matrix

| source_path_or_record | evidence_class | symbol | venue | start_ts | end_ts | width | provenance_present | fingerprint_present | paper_replay_comparable | regime_segments_status | contract_result | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `artifacts/arvp_replay_paper_pilot/1909_smoke_20260424/paper_reference_window.json` + `docs/evidence/arvp_calibration_pilot_1932_2026-04-26.md` | pilot evidence summary + legacy inline paper window artifact + committed compare/calibration/regime follow-up artifacts | BTCUSDT | MEXC paper / same-venue replay evidence path | 2026-04-24T00:42:00Z | 2026-04-24T00:43:00Z | 1m | yes (`provenance` block) | yes (`comparison`, `calibration`, `scorecard` fingerprints repo-backed) | yes, bounded; replay compare/calibration already demonstrated | unavailable (0 segments; scorecard `unavailable`) | WARN | Artifact uses `paper_selector` + nested `provenance`, but contains only ORDER/FILL events and no SIGNAL/DECISION chain; pilot source artifacts were originally local-only and later summarized repo-backed |
| `artifacts/paper_reference_windows/paper_reference_window.json` + `docs/evidence/arvp_paper_reference_window_2968_after_3026.json` | committed exporter-backed paper window + committed compare/calibration/regime bundle | BTCUSDT | MEXC paper side; compare/calibration executed against Binance replay dataset (`venue_mismatch=true`) | 2026-06-06T00:28:12.551Z | 2026-06-06T00:30:12.814Z | 2m0.263s | yes (flattened extraction metadata fields present) | yes (`comparison`, `calibration`, `scorecard` fingerprints repo-backed) | yes, but compare certainty limited by venue/regime confounds | unavailable (0 segments; scorecard `unavailable`) | WARN | Strongest current repo-backed window: full SIGNAL/DECISION/ORDER/FILL chain present; exporter/consumer shape matches runtime reality, but deviates from contract doc (`paper_selector` absent, metadata flattened) |

Matrix interpretation:

- Both windows are usable for bounded replay-vs-paper comparison and calibration history.
- Neither window yields regime-capable evidence.
- The strongest current bank is 2 windows, both narrow, both with `regime_segments` unavailable.

---

## 8. regime_segments Assessment

Repo-backed regime evidence is explicit and consistent:

| Window | Regime artifact | Status | Evidence |
|---|---|---|---|
| Pilot | `artifacts/regime_scorecards/2975/window_bank_2/replay-16a0a8f6d92f-0001/arvp_regime_scorecard.json` | `unavailable` | `segments=[]`; note: `comparison input has no regime_segments` |
| #3028 | `artifacts/regime_scorecards/2975/window_bank_2/replay-577c2f83ac91-0001/arvp_regime_scorecard.json` | `unavailable` | `segments=[]`; note: `comparison input has no regime_segments` |

Aggregate regime finding from `artifacts/regime_scorecards/2975/window_bank_2/regime_scorecard_summary.json`:

- `any_regime_segments_available=false`
- `windows_with_regime_context=0`
- `aggregate_scorecard_status=unavailable`

Assessment:

- `regime_segments` are not populated for any currently evidenced window.
- This is an honest data/evidence limitation, not a place for inference.
- A4 readiness is therefore not cleared by the current bank.

---

## 9. A2/A3/A4 Readiness Decision

| Workstream | Readiness | Why |
|---|---|---|
| A2 Replay-vs-Paper Batch Compare | PASS | Existing repo-backed bank already supports bounded compare on 2 windows; compare artifacts and fingerprints exist |
| A3 Calibration + Drift Classification | WARN | Existing repo-backed bank supports calibration history, but certainty is limited and one window is venue/regime confounded |
| A4 Regime Interpretation | FAIL | No window has populated `regime_segments`; both scorecards are `unavailable` |

Overall A2/A3/A4 readiness: **WARN**

Reason:

- A2 can proceed on the current bank.
- A3 can proceed only with explicit caveats.
- A4 cannot honestly proceed as a regime-capable window-bank step until a longer comparison-grade natural-paper window exists with populated `regime_segments`.

---

## 10. Decision

**Decision:** `WINDOW_BANK_INSUFFICIENT_NEEDS_BOUNDED_DATA_ACQUISITION`

Why this is the correct status:

1. **Some usable repo-backed evidence exists.** The repo contains a usable 2-window bank and committed compare/calibration/regime artifacts.
2. **The evidence is insufficient for honest A4 progression.** Both windows have `regime_segments` unavailable.
3. **Additional extraction/acquisition is still needed.** The next useful bank increment is a longer comparison-grade natural-paper window, not a new candidate family.
4. **This is not a full block.** There is enough evidence to avoid `BLOCKED_NO_COMPARISON_GRADE_NATURAL_PAPER_WINDOWS`.
5. **This is not ready.** The bank does not satisfy the regime-capable condition needed for clean A2/A3/A4 readiness.

Explicitly not concluded here:

- No Product-Complete claim.
- No Live-Go / Echtgeld-Go.
- No Candidate #4.
- No PB1/RMR/Momentum rescue.

---

## 11. Required Follow-up

Recommended bounded follow-up title per issue logic:

- `[ARVP][DATA] Extract bounded natural-paper reference windows for #3212`

Recommended follow-up scope:

- Produce at least one additional longer comparison-grade natural-paper window.
- Prefer a duration likely to yield non-empty `regime_segments`.
- Keep the scope on window-bank quality, not on new candidate-family discovery.
- If readonly extraction is used later, it must rely on the existing guarded runner and approved secret-managed readonly DSN outside agent-visible outputs.

Existing related historical blockers worth cross-reading:

- `#2974` Product-Complete review (blocked)
- `#3087` longer-window / `regime_segments` blocker in historical chain

---

## 12. Stop Rules / Safety

- LR remains NO-GO.
- Board stage `trade-capable` is not Live-Go.
- No Live-Go / Echtgeld-Go.
- No Product-Complete claim.
- No Candidate #4.
- No PB1/RMR/Momentum rescue.
- No runtime start.
- No Docker/Compose orchestration.
- No workflow dispatch.
- No DB mutation.
- No secrets in outputs.
- No regime inference without `regime_segments`.

---

## 13. Restunsicherheiten

1. The current repo shows contract-shape drift between the canonical doc and exporter/consumer reality on main.
2. The pilot evidence chain is historically useful but not a clean modern exporter proof.
3. The #3028 window is the strongest repo-backed artifact, but its compare/calibration path is venue/regime confounded.
4. This slice did not open a live readonly correlation_ledger session because doing so here would require secret-backed DSN access outside scope.
5. Longer windows are likely, but not guaranteed, to produce non-empty `regime_segments`.

---

## 14. Status

`WINDOW_BANK_INSUFFICIENT_NEEDS_BOUNDED_DATA_ACQUISITION`
