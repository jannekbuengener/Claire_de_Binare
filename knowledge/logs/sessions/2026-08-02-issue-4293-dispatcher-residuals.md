# Session 2026-08-02 — Issue #4293 ACP dispatcher residuals

## Goal
Fix four post-merge P2 residuals from PR #4286 on the Agent Control Plane
dispatcher before #4257 implementation.

## Live truth
- `origin/main` @ `fca8ad09`
- Issue #4293 OPEN; no prior open PR
- PR #4286 MERGED; four unresolved P2 threads confirmed as R1–R4
- Router: `CREATE_NEW_BATCH_PR` → `batch/agent-skills-issue-4293`
- Anti-repush: did not reuse `batch/agent-skills-issue-4250`

## Brain Evidence
- brain_source: repo-only
- brain_status: not-used
- context_tool_status: available
- context_trust_level: none
- repo_fallback_reason: insufficient_evidence
- Plan-GO + implementation_go from operator prompt contract

## Delivered
- R1: `DISPATCH_DELIVERY_TARGET_CONFLICT` before provider call
- R2: effective attenuated `wall_time_seconds` on run + ProviderRequest + timeout
- R3: CREATE observed targets on run.route + evidence provenance
- R4: verify_store uniqueness `(run_id, attempt, lifecycle.state)`

## Validation
- pytest 105 targeted governance tests PASS
- ruff + black --check PASS on scope
- git diff --check PASS
- No Full Fast-CI / no cdb-local-ci / no merge / issue left open

## Boundaries
- LR NO-GO unchanged; no BLUE/RED, secrets, DB/MCP mutation, live dispatch
