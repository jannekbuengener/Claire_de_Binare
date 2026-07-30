---
name: cdb-operator
description: Enforces Claire de Binare operator workflow: bootloader first, live GitHub truth, dry-run planning, strict GO gates. Autonomous squash-merge is allowed only when the full capability gate (docs/runbooks/merge_policy_ci_gate.md) is proven for the exact PR head; otherwise honest DONE_PR_OPEN_MERGE_HANDOFF, never --admin.
compatibility: opencode
metadata:
  project: claire-de-binare
  workflow: operator
disable-model-invocation: true
---

# CDB Operator Skill

## Purpose

Use this skill when working on Claire_de_Binare with OpenCode.

## Required workflow

1. Read `AGENTS.md` in the repo root.
2. Follow the pointer to `agents/AGENTS.md`.
3. Read `agents/OPEN_CODE_AGENTS.md` if present.
4. Read the complete repo read order before planning.
5. Pull GitHub issue and PR state live.
6. Treat `CURRENT_STATUS.md` as ledger, not live truth.
7. Produce only Lage, Befund, Plan, Dry-Run, Validierung, Restunsicherheiten.
8. Do not write, commit, push, comment, label, or close without explicit human GO.
9. Merge is capability-based, not agent-type-based: after Plan-GO, a squash
   merge (`gh pr merge <PR> --squash --delete-branch`) is autonomous and
   allowed only when every capability gate in
   `docs/runbooks/merge_policy_ci_gate.md` § Capability-based autonomous
   merge is proven for the exact PR head (task allows autonomous merge, PR
   in scope/mergeable/no blocking reviews, local Fast-CI PASS bound to head,
   main unchanged since validation, `cdb-local-ci` SUCCESS on exact head,
   session can perform the merge). `--admin` is never a substitute for a
   missing `cdb-local-ci`. If any gate is unproven: report
   `DONE_PR_OPEN_MERGE_HANDOFF` with the exact missing capability; do not
   loop or force.
10. After a live-verified merge, local post-merge cleanup is
    evidence-based only (`cdb-session-close` § Safe Post-Merge Cleanup):
    never discard unsaved changes, never `branch -D` without tree/patch
    equivalence, never republish a deleted remote head (anti-repush),
    update local `main` with `ff-only` only.

## Stop conditions

Stop immediately on missing bootloader, unclear scope, unexpected diff, red
`cdb-local-ci` (the sole required merge context; Hosted Actions red is
advisory), a capability gate unproven for merge, scope growth, any
live-readiness/echtgeld implication, or a cleanup request that would
discard unsaved/unmerged local work.

