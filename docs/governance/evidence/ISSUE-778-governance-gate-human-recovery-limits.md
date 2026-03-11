# Evidence for Issue #778 — Kill-Switch + Limit Controls Drill

Purpose:
- Record the smallest repo-backed implementation slice for `#778`.
- Prove fail-closed kill-switch behavior and deterministic limit-control outcomes without changing live routing.

Drift note:
- `docs/live-readiness/ISSUES.md` names `LR-003` as "Kill-Switch + Limit Controls Drill Test".
- Legacy `docs/live-readiness/LR-003-*` files already document a different historical control.
- This issue therefore uses issue-specific evidence instead of rewriting the old live-readiness record set.

What exists now:
- Risk-side kill-switch gate: `services/risk/service.py::_kill_switch_gate()`
- Execution-side defense-in-depth kill-switch block: `services/execution/service.py::process_order()`
- Deterministic limit controls: `core/contracts/decision_contract_v1.py`
- Existing exact vector fixtures: `tests/fixtures/decision_contract_v1/golden_vectors.json`
- Operator checklist anchor: `tools/test_pack/runbooks/kill_switch_checklist.md`

Implementation added for this issue:
- Drill runner: `scripts/drills/lr003_kill_switch_limit_controls_runner.py`
- Drill tests: `tests/unit/scripts/test_lr003_kill_switch_limit_controls_runner.py`
- Generated evidence:
  - `reports/drills/lr003/lr003_summary.json`
  - `reports/drills/lr003/lr003_report.md`

Verified scenarios:
- Risk kill-switch active -> block with `KILL_SWITCH_ACTIVE`
- Risk kill-switch evaluation error -> fail closed with `KILL_SWITCH_UNEVALUABLE`
- Execution kill-switch active -> reject before executor call
- Limit controls stay deterministic for:
  - `deny_max_notional`
  - `deny_max_exposure`
  - `deny_max_drawdown`
  - `allow_reduce_only_sell`

Verification commands:
- `pytest -q tests/unit/scripts/test_lr003_kill_switch_limit_controls_runner.py`
- `pytest -q tests/unit/risk/test_contract_enforcement.py`
- `pytest -q tests/unit/services/test_execution_shadow_gate.py`
- `python scripts/drills/lr003_kill_switch_limit_controls_runner.py --output-dir reports/drills/lr003`

Current status:
- Implemented on 2026-03-10.
- Scope intentionally small: drill/test/evidence only, no safety-platform redesign, no live-operation automation.
