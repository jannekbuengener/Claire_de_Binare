# Deprecation Note: Discussion Pipeline

Date: 2026-02-17
Updated: 2026-03-15
Status: Removed from working repo (#1157)

What happened:
- Discussion Pipeline documentation, config, and generated artifacts were moved to `_archive/discussion_pipeline/`.

Why:
- The feature was decommissioned and references were removed from active indexes/backlog docs.

Where archived:
- `_archive/discussion_pipeline/`

Working Repo context:
- Initial deprecation commit: `04da60e`
- Full removal from working repo: #1157

Removed paths:
- `infrastructure/scripts/discussion_pipeline/` (31 files)
- `knowledge/discussions/` (21 files)
- `knowledge/DISCUSSION_PROPOSALS.md`

Snapshot retained at:
- `docs/archive/docs_hub_snapshot/_archive/discussion_pipeline/`

Rollback:
- Revert #1157 merge commit to restore working-repo paths.
- Docs-hub snapshot remains at `docs/archive/docs_hub_snapshot/` for provenance.
