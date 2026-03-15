# Evidence for Issue #778 — Kill-Switch + Limit Controls (Parent Gate)

Gate-Verdict: **OPEN/PARTIAL**

Purpose:
- Primary repo-backed evidence anchor for `#778` as a parent governance gate.
- Documents the current proof state for fail-closed kill-switch behavior and deterministic limit-control outcomes.
- Clearly separates what is repo-backed today from what remains open or delegated to child issues.

## Drift note (LR-003 naming)

- `docs/live-readiness/ISSUES.md` names `LR-003` as "Kill-Switch + Limit Controls Drill Test" (this issue's scope).
- Legacy `docs/live-readiness/LR-003-STATE.yaml` and `docs/live-readiness/LR-003-EVIDENCE.md` document a different historical control ("P0 Contract Drift Guard").
- **This issue deliberately uses issue-specific evidence instead of rewriting the historical live-readiness record set.** The `LR-003-*` SSOT files are not modified, reconciled, or superseded by this issue.
- This drift is a known, tolerated state. Reconciliation of the historical `LR-003` naming is out of scope for `#778`.

## Repo-backed evidence (confirmed)

The following is implemented and testable in the repository today:

### Kill-switch mechanics
- Risk-side kill-switch gate: `services/risk/service.py::_kill_switch_gate()`
- Execution-side defense-in-depth kill-switch block: `services/execution/service.py::process_order()`

### Deterministic limit controls
- Limit-control logic: `core/contracts/decision_contract_v1.py`
- Golden vector fixtures: `tests/fixtures/decision_contract_v1/golden_vectors.json`

### Drill runner and tests (non-live, repo-local)
- Drill runner: `scripts/drills/lr003_kill_switch_limit_controls_runner.py`
- Unit tests: `tests/unit/scripts/test_lr003_kill_switch_limit_controls_runner.py`

### Verified scenarios
- Risk kill-switch active -> block with `KILL_SWITCH_ACTIVE`
- Risk kill-switch evaluation error -> fail closed with `KILL_SWITCH_UNEVALUABLE`
- Execution kill-switch active -> reject before executor call
- Limit controls stay deterministic for: `deny_max_notional`, `deny_max_exposure`, `deny_max_drawdown`, `allow_reduce_only_sell`

### Other repo-backed artifacts
- Operator checklist anchor: `tools/test_pack/runbooks/kill_switch_checklist.md`
- Governance evidence (this file): `docs/governance/evidence/ISSUE-778-governance-gate-human-recovery-limits.md`
- PR: https://github.com/jannekbuengener/Claire_de_Binare/pull/921

### Local drill artifacts (non-canonical)
The workspace contains local drill outputs under `reports/drills/lr003/` (`lr003_summary.json`, `lr003_report.md`). These are **untracked and not committed** — they are not canonical repo evidence and must not be cited as proof of gate passage. They serve as local supporting material only.

## Open evidence gaps

The following claims from the original issue scope have **no repo-backed evidence today**:

| Claim | Status | Notes |
|---|---|---|
| Kill-switch stops orders within <5 seconds | **OPEN** | No timed live or shadow drill evidence exists |
| Drill test documented with timestamps | **OPEN** | Delegated to #661 (operator drill) |
| Recovery procedure tested | **OPEN** | No repo-backed recovery evidence |
| Human-gate process defined | **OPEN** | No formal human-gate definition in repo |
| Canonical run URL / CI evidence | **OPEN** | Parent has PR 1 / Doc 1 / Run 0 |

These gaps are the reason the gate verdict remains **OPEN/PARTIAL**.

## Child issue mapping

| Issue | Role | Status |
|---|---|---|
| #661 | **Active child** — operator drill with real alert trigger, kill-switch/order-flow verification, timeline/evidence pack | Open, in progress |

### Explicitly not children of #778
- **#658** — Branch protection reapply; not a kill-switch/limit-control deliverable.
- **#762, #748** — Policy/contract-related, both closed. Historical/related context only, not active child work for this parent.

## Verification commands

```bash
pytest -q tests/unit/scripts/test_lr003_kill_switch_limit_controls_runner.py
pytest -q tests/unit/risk/test_contract_enforcement.py
pytest -q tests/unit/services/test_execution_shadow_gate.py
python scripts/drills/lr003_kill_switch_limit_controls_runner.py --output-dir reports/drills/lr003
```

## Gate closure conditions

This parent gate can move to PASS when:
1. #661 delivers repo-backed operator drill evidence (run URL, timestamps, evidence pack)
2. All open evidence gaps in the table above are addressed with concrete artifacts
3. No unbacked claims remain in the parent issue text

Until then, the verdict remains **OPEN/PARTIAL**.

---

Implementation date: 2026-03-10 (initial), 2026-03-15 (parent gate tightening)
Scope: evidence documentation only — no safety-platform redesign, no live-operation automation, no historical LR-003 SSOT rewrite.
