# Session Log — Issue 4229 Evidence Harvester Test Isolation

Date: 2026-07-31
Agent: Cursor Cloud
Branch: cloud-cursor/evidence-harvester-test-isolation-222f
PR: 4238
Head: 61c148d66e950e1050cc997dcd48ae48f4e6a0fb
Base: origin/main @ e96f724c6a6615fea8bda8adc707b51fbd6bcf84

## Scope

Isolate test_install_path_is_patchable so it cannot write run_task.cmd
into the repo worktree. Delivery slice only; no merge, no issue close.

## Brain Evidence

- brain_source=repo-only, brain_status=not-used
- Context MCP absent (repo_fallback_reason=unavailable)
- PR-Router: CREATE_NEW_BATCH_PR / lane ci-tooling / unlock

## Root Cause

Install unit test omitted --output-dir; productive default
artifacts/evidence_harvester/scheduled/ received run_task.cmd.

## Delivered

- tests/unit/tools/evidence_harvester/test_scheduler.py
  - inject --output-dir under tmp_path
  - regression test_install_run_task_cmd_stays_under_injected_output_dir
- No productive scheduler/boot/collector/supervisor changes
- No .gitignore change

## Validation

| Check | Result |
|---|---|
| pytest isolated install-path test | PASS |
| git status before/after that test | identical (empty) |
| artifacts scheduled run_task.cmd after test | absent |
| pytest -q tests/unit/tools/evidence_harvester | 286 passed |
| ruff check / black --check (changed file) | PASS |
| git diff --check | PASS |
| gitleaks protect --staged | no leaks |

## Status

DONE_SLICE_ADDED_TO_BATCH_PR

## Boundaries

LR NO-GO; no productive runtime/DB/MCP/merge.
