---
name: cdb-ci-cd-guard
description: CDB CI/CD governance audit and hardening for the working repo. Use when GitHub Actions, rulesets, required checks, secret guards, or fake-green behavior need to be verified or fixed. Derive protected refs, required checks, and enforcement behavior from current repo evidence and GitHub state instead of assuming old branch patterns or legacy docs-hub paths.
---

# CI/CD Guard

## Canon first
- Use the working repo as the only default source.
- Start control-first:
  1. GitHub control issue `#1445`
  2. newest weekly comment on `#1445`
  3. stage-ratification issue `#1492` as Board context only
  4. `docs/runbooks/CONTROL_REGISTER.md`
  5. `CURRENT_STATUS.md`
  6. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
  7. only then inspect rulesets, issues, PRs, and workflows
- Read `docs/index.md` and `docs/runbooks/merge_policy_ci_gate.md` for local CI canon after the control-first chain.
- Treat GitHub rulesets and required checks as evidence-bearing runtime state. If they are not observable, report the gap instead of inventing a result.
- Treat `#1492` only as current Board context, not as any CI or LR override.

## Use this when
- a run is green but hidden stub, mock, skip, or fallback behavior is suspected
- required checks, branch protection, secret guards, or delivery gates look inconsistent
- workflow behavior changes by branch or secret availability

## Hard rules
- Do not assume protected branch patterns. Derive them from current rulesets, workflows, or explicit user input.
- No silent stub or mock path on protected refs.
- Missing critical secrets on protected refs must fail closed.
- Without explicit approval, default to audit plus fix plan rather than mutation.

## Workflow
1. Inventory active workflows and identify gate-bearing jobs.
2. Derive protected refs, required checks, and enforcement scope from repo evidence plus GitHub state.
3. Search for fake-green vectors: stub, mock, fallback, skipped gates, soft-fail secret handling.
4. Verify that guard decisions are visible in logs and outputs.
5. Produce deterministic evidence per workflow: protected behavior, unprotected behavior, secret handling, merge-blocking effect.
6. If fixes are needed, propose the smallest reversible patchset first.

## Output
- PASS or FAIL
- concrete enforcement gaps, grouped by workflow or ruleset
- mapping table: workflow -> trigger/ref scope -> secret behavior -> merge effect
- minimal fix plan, or patchset if explicit approval exists
