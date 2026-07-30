<!--
Canonical Skill Source: docs/skills/cdb-operator/SKILL.md
Surface: codex
Sync Status: mirrored-from-canon
Last Verified: 2026-07-30
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-operator
description: Enforces Claire de Binare operator workflow with router-first slice delivery as the default. Merge is a separate mode only for a frozen merge_candidate after the final integrated head/base capability gate is proven; otherwise honest DONE_PR_OPEN_MERGE_HANDOFF, never --admin.
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
9. Delivery is the default after Plan-GO: route first, deliver the scoped slice,
   update ledger and Issue handoff, then stop without merge or Issue closure.
   A squash merge (`gh pr merge <PR> --squash --delete-branch`) is considered
   only in a separately authorized Merge Mode after the PR is frozen as
   `merge_candidate` and every capability gate in
   `docs/runbooks/merge_policy_ci_gate.md` § Capability-based autonomous
   merge is proven for the exact final PR head (task explicitly allows merge, PR
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

Stop immediately on missing bootloader, unclear scope, unexpected diff, failed
targeted slice validation, or scope growth. In Merge Mode also stop on red
`cdb-local-ci` for the exact final head (the sole required merge context;
Hosted Actions red is advisory) or any unproven merge capability. Also stop on
live-readiness/echtgeld implication, or a cleanup request that would
discard unsaved/unmerged local work.

## Delivery Mode versus Merge Mode

- **Delivery Mode:** Router ausführen, Slice in den zugewiesenen PR liefern,
  targeted Validation, Ledger-/Issue-Handoff, kein Merge.
- **Merge Mode:** nur für `merge_candidate`; Intake einfrieren, Base integrieren,
  kombinierten Diff reviewen, Full Fast-CI und exact-SHA `cdb-local-ci`.

Ein Merge-Trigger ist kein Human-GO und keine Merge-Autorisierung. Head- oder
Base-Drift invalidiert die Final-Evidence.

