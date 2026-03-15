# Docs Hub Retirement Handoff

Status: maintainer handoff
Issue: #1140
Prepared: 2026-03-11

## Purpose

This handoff covers the operational retirement of the separate
`Claire_de_Binare_Docs` repository after the completed consolidation into
`Claire_de_Binare`.

Use this document to decide whether the old repo can be deleted locally and
remotely, and to perform that deletion in a controlled order.

## Already Completed

The following work is already done:

- productive docs-hub content was migrated into the working repo
- migration inventory was documented in `docs/meta/DOCS_HUB_MIGRATION_MATRIX.md`
- delete readiness was documented in `docs/meta/DOCS_HUB_DELETE_READINESS.md`
- the old docs-hub repo was snapshotted into
  `docs/archive/docs_hub_snapshot/`
- active guards, resolvers, navpacks, pointers, and templates were switched to
  local-first behavior
- final active-path leak scan was completed and productive leaks were fixed

## Why The Old Repo Is Redundant

`Claire_de_Binare_Docs` is no longer needed for:

- agent startup or canonical read order
- governance or knowledge lookup
- issue-template or GitHub-community files
- docs RAG adapter default resolution
- navigation from the working repo

All productively relevant material now exists in `Claire_de_Binare`.

## Local Archive That Must Remain

The following local archive content is intentionally retained:

- `docs/archive/docs_hub_snapshot/`
- targeted local archive copies such as `docs/archive/github/`
- closeout docs under `docs/meta/`

This archive is provenance only. Do not cosmetically rewrite it.

## What Was Not Promoted As Active Canon

These classes remain historical only:

- split-repo migration plans
- retired pointer texts
- historical reviews, audits, reports, and logs
- docs-hub navpacks preserved for provenance
- docs-hub git internals and machine-local folders

## Manual Pre-Delete Checks

- [ ] Confirm the working repo is on the intended merge-ready revision.
- [ ] Confirm `docs/meta/DOCS_HUB_MIGRATION_MATRIX.md` exists and reflects the migration scope.
- [ ] Confirm `docs/meta/DOCS_HUB_DELETE_READINESS.md` exists and states delete readiness.
- [ ] Confirm `docs/archive/docs_hub_snapshot/` exists and is readable.
- [ ] Confirm no teammate or automation still works directly in `Claire_de_Binare_Docs`.
- [ ] Confirm no active standard path in the working repo depends on the old repo.
- [ ] Confirm local validation still passes on the merge-ready working repo.

Recommended spot checks:

- `pwsh -File tools/enforce-root-baseline.ps1 -DryRun`
- `python scripts/governance/check_risk_events_schema_contract.py`

## Optional Backup Step

Optional, but reasonable before destructive cleanup:

- create a final zip or filesystem copy of `Claire_de_Binare_Docs`
- mark the remote repo read-only or archived before hard deletion
- capture repo settings or metadata if the hosting platform does not preserve
  them after deletion

These are optional because the working repo already contains the local snapshot.

## Actual Deletion Steps

### Local Delete

1. Ensure no shell, IDE, or tool is still rooted in `Claire_de_Binare_Docs`.
2. Delete the local repo directory `D:\Dev\Workspaces\Repos\Claire_de_Binare_Docs`.
3. Re-open the working repo alone and verify no tool complains about missing
   docs-hub paths.

### Remote Retirement

Choose one of these:

1. Archive the remote repo first if you want a reversible safety period.
2. Delete the remote repo directly if policy allows and no team workflow still
   references it.

If archived first:

- update the description to indicate retired/redundant status
- freeze writes
- delete later after the waiting period if desired

If deleted directly:

- ensure the working repo merge containing #1140 is already in the protected
  default branch
- ensure collaborators know the old repo is gone and the working repo is the
  only productive target

## Optional Post-Delete Cleanup

- remove stale local IDE workspace entries that point at `Claire_de_Binare_Docs`
- remove pinned terminals, shortcuts, or favorite paths to the old repo
- archive or remove any CI/ops notes outside the repo that still mention the old
  repo as active
- update external repo descriptions or team onboarding notes if they still list
  the docs repo as a standard workspace

## Decision Gate

If the pre-delete checklist is satisfied, the separate docs repo may be retired.

Operational decision:

- #1140 may be closed after merge
- `Claire_de_Binare_Docs` may be deleted after the maintainer completes the
  manual delete sequence
