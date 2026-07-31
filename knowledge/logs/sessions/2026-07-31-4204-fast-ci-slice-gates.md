# Session 2026-07-31 — #4204 Fast-CI Slice Gates + Timing Evidence

## Scope

Delivery slice for Issue #4204: deterministic fail-closed slice validation policy,
path/lane/profile selection, `merge_evidence=false`, timing evidence; Final-Head
Fast-CI selector unchanged. Merge/Issue-close/publish out of scope.

## Brain Evidence

- brain_source: repo-only
- brain_status: not-used
- context_tool_status: absent
- context_trust_level: none
- records_found: none
- repo_fallback_reason: unavailable
- context_brain_attempted: true
- context_brain_used: false
- context_available: false
- repo_fallback_used: true

## Router

- decision: CREATE_NEW_BATCH_PR
- target_branch: batch/ci-tooling-issue-4204
- lane: ci-tooling
- validation_profile: ci-tooling-v1
- lock_state: UNLOCKED

## Delivered

- `ci/config/slice_validation_policy.v1.yaml`
- `ci/lib/slice_selection.py` + unit stage durations + report stage timing
- Orchestrator `--profile slice` / `--slice` inputs
- Publisher rejects `merge_evidence=false` / `profile=slice`
- Docs: merge_policy_ci_gate, cdb-ci-cd-guard (surfaces synced), ci/README
- Tests: `tests/unit/ci/test_slice_selection_policy.py`

## Validation

- Final-Head collect-only: before 8957/8958 → after 8970/8971 (+13 new slice tests)
- Slice case + unknown-path fallback exercised
- 170 CI/tools unit tests PASS with `--durations=20`
- ruff/black/readme-links/git diff --check/gitleaks protect --staged PASS

## Status

DONE_SLICE_ADDED_TO_BATCH_PR

LR remains NO-GO.
