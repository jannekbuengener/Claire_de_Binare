# Evidence Note for Issue #708 — Jules / Six-Eyes Review + Merge

Purpose:
- Verify the current repo state for Jules/AI review, branch protection, required checks, and merge governance.
- Record the smallest repo fix needed to make the issue closeable without reworking reviewer/merge automation.

Current verdict:
- Jules/AI review is present only as advisory signal. It is not a required merge check on `main`.
- Six-Eyes is not technically enforced by the current PR template or branch protection configuration.
- The live merge contract on `main` is `ci (Unit/Integration + Lint gesammelt)` + `policy-gate`, plus the branch protection safety settings returned by `gh api`.

Claims checked:
- Workflow-level AI review artifacts: `.github/workflows/ai-review-router.yml`, `.github/workflows/claude-code-review.yml`, `.github/workflows/gemini-review.yml`
- Merge-relevant workflows: `.github/workflows/ci.yml`, `.github/workflows/policy-gate.yml`, `.github/workflows/required-checks-audit.yml`
- Branch protection snapshots and drift guards: `reports/BRANCH_PROTECTION_BASELINE_main.json`, `reports/REQUIRED_CHECK_CONTEXTS_BASELINE_main.json`, `scripts/governance/check_branch_protection_drift.py`, `scripts/governance/check_required_check_contexts.py`
- Governance / merge docs: `docs/governance/no_human_review_policy.md`, `docs/runbooks/merge_policy_ci_gate.md`, `.github/pull_request_template.md`, `docs/operations/branch_protection_policy.md`

What was true at the start of this issue pass:
- Saved branch protection baseline drifted from live GitHub state.
- Saved required-context baseline drifted from the live required checks on `main`.
- Active docs did not clearly separate AI review signal from merge authority.
- `docs/operations/branch_protection_policy.md` still described an older blueprint with different review and required-check expectations.

Repo fix applied:
- Refreshed the saved branch protection baseline to the live GitHub state.
- Refreshed the saved required-check baseline so drift checks cover both live required contexts.
- Clarified in the PR template and merge-policy docs that AI/Jules review output is advisory only and does not grant approval or merge rights.
- Marked the stale branch-protection blueprint doc as superseded.

Verification used:
- `gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection`
- `python scripts/governance/check_branch_protection_drift.py --repo jannekbuengener/Claire_de_Binare --branch main --baseline reports/BRANCH_PROTECTION_BASELINE_main.json`
- `python scripts/governance/check_required_check_contexts.py --baseline reports/REQUIRED_CHECK_CONTEXTS_BASELINE_main.json --workflows-dir .github/workflows`

Remaining limits / follow-ups:
- If the repo wants enforceable Six-Eyes, that is a separate policy and platform change. It is not implemented by this issue pass.
- Workspace-local Jules contract checks that expect a PR-triggered comment-only reviewer are not part of the current tracked merge contract.
