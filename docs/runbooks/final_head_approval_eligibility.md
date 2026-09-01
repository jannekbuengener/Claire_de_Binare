# Final-Head Approval Eligibility Runbook

Status: Operator + Provider handoff  
Issue: `#4505`  
Related: `docs/contracts/final_head_merge_pipeline.v1.md`

## Purpose

Machine-readable eligibility for M6 GitHub APPROVE. Repo chain:

`Policy → Live Snapshot → Approval Context → Eligibility → Approve Body → Provider`

## CLI (read-only except approve-body emission)

```bash
# Live snapshot (read-only gh)
python -m tools.agent_control approval snapshot --pr <N>

# Eligibility verdict (exit code = recommendation class)
python -m tools.agent_control approval eligibility --pr <N>

# Contract APPROVE body (only when APPROVE_RECOMMENDED)
python -m tools.agent_control approval approve-body --pr <N>
```

Exit codes: `0`=APPROVE_RECOMMENDED, `2`=BLOCKED, `3`=HOLD, `4`=UNKNOWN.

## Final-Head provenance (fail-closed)

`FINAL_HEAD_READY_FOR_APPROVAL` is trusted only when:

1. PR comment contains `<!-- cdb-pr-acceptance:v1 -->` + schema-valid JSON
2. Envelope validates as `BatchMergeConductorEnvelope`
3. `run_status=COMPLETE`, `lifecycle.state=FINAL_HEAD_READY_FOR_APPROVAL`
4. `result.phase=HANDOFF_APPROVAL`, `success_decision` + `handoff_role` match canon
5. `subject.head_sha` == live PR HEAD
6. Upstream schema-valid `CompletenessReviewEnvelope` with `MERGE_CANDIDATE` on same HEAD
7. `steward_state` not `accepting_slices`

Self-declared `producer` strings without schema validation do **not** authorize approval.

## Provider boundary (#4505)

Cursor Cloud / Plaketten-Ingo automation YAML is **outside this repo**.

Repo eligibility correctness alone does **not** close `#4505`.

Provider trigger MUST:

1. Call `approval eligibility --pr N` before APPROVE
2. APPROVE only on exit `0` with contract body from `approve-body`
3. Exclude draft, `accepting_slices`, Dependabot auto-approve paths without Final-Head pipeline

Until provider automation stops premature APPROVEs:

**Status:** `REPO_4505_FIX_READY_NEEDS_CURSOR_PROVIDER_BINDING`

## Live proof split

| Layer | Proves | Closes #4505 |
|-------|--------|--------------|
| Repo (CLI + tests) | Deterministic eligibility | No |
| Provider (automation) | No premature APPROVE; positive M6 path | Yes |

Manual subagent APPROVE after eligibility proves repo chain only — not provider remediation.
