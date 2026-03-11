# Docs Hub Delete Readiness

Status: ready for closeout
Issue: #1140
Last verified: 2026-03-11

## Goal

Issue #1140 retires the separate `Claire_de_Binare_Docs` repository as a
productive dependency. The working repo must contain all productively relevant
documentation, knowledge, governance, agent, navigation, and template assets so
that the old docs repo can be deleted without harming current or future work.

## What Was Moved Or Merged Into The Working Repo

- active agent registry and agent-role material under `agents/`
- active knowledge and governance material under `knowledge/`
- local navigation, runbooks, templates, and archive structure under `docs/`
- GitHub community and issue-template artifacts under `.github/`
- local-first resolver and guard updates in `tools/`, `scripts/`,
  `infrastructure/scripts/`, and `mcp_navpack_working_repo/`

Physical migration summary:

- `agents/`: 67 docs-hub files copied into the working repo and merged with the
  existing local canon
- `knowledge/`: 426 docs-hub files copied into the working repo and merged with
  existing local files
- targeted root/meta/github artifacts were merged into active local paths where
  they still had operational value

## What Was Archived Locally

The old docs-hub repository was snapshotted into:

- `docs/archive/docs_hub_snapshot/`

Snapshot scope:

- root files such as `DOCS_HUB_INDEX.md`, `index.yaml`, `issues.md`
- `.github/`, `agents/`, `knowledge/`, `meta/`, `scripts/`, `tools/`
- `_archive/`, `_legacy_quarantine/`, `mcp_navpack_docs_hub*`, `verlosung/`

Snapshot size at final verification:

- 635 files preserved locally

## What Was Not Promoted As Productive Canon

These remain only as historical or redundant material:

- split-repo migration plans and retired pointer texts
- historical reviews, audits, reports, logs, and quarantined legacy artifacts
- docs-hub-only navpacks preserved for provenance
- docs-hub git internals and machine-local state such as `.git/`, `.worktrees/`,
  `.local/`, `.cdb_local/`

Where old files still exist at active local paths, they were turned into local
legacy notes that point to the current canon or to the local archive snapshot.

## Final Rest Scan

A final search was run across active working-repo paths for:

- `Claire_de_Binare_Docs`
- `../Claire_de_Binare_Docs`
- `Docs Hub`
- `docs hub`
- `DOCS_HUB`
- `Moved: Canon liegt im Docs Hub`

Result:

- no active default path requires the separate `Claire_de_Binare_Docs` repo
- remaining hits in active files are either:
  - explicit legacy notes
  - guard patterns that detect stale split-repo references
  - compatibility names such as `DOCS_HUB_PATH` that now resolve to local canon
    or the local archive snapshot
  - historical workflow/check names kept for continuity

Productive leaks fixed during this finalization step:

- `tools/install-git-hooks.ps1` now points legacy guidance at
  `docs/archive/docs_hub_snapshot/`
- `tools/enforce-root-baseline.README.md` now describes the local archive
  snapshot instead of the old sibling repo

## Verification

Verified locally:

- `pwsh -File tools/enforce-root-baseline.ps1 -DryRun`
- `python scripts/governance/check_risk_events_schema_contract.py`
- `pytest -q tests/unit/scripts/test_docs_hub_rag_adapter.py`
- `python -c "from infrastructure.scripts.discussion_pipeline.utils.config_loader import ConfigLoader; ..."`
- `python infrastructure/scripts/docs_hub_rag_adapter.py preview --limit 1`

All checks passed with the working repo as the active docs source.

## Delete Readiness Decision

`Claire_de_Binare_Docs` is now redundant.

Deletion is acceptable because:

- all productively relevant content now exists in the working repo
- the old docs-hub content is preserved locally as a snapshot
- no active standard path requires the separate repo
- deleting the old repo does not remove information needed for current or future
  operation of the consolidated system

## Release Decision

Delete-readiness for `Claire_de_Binare_Docs`: YES

Operator handoff:

- `docs/meta/DOCS_HUB_RETIREMENT_HANDOFF.md`
