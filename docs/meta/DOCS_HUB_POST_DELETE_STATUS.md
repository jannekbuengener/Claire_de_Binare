# Docs Hub Post-Delete Status

Status: post-retirement
Related issue: #1140
Recorded: 2026-03-11

## Current State

- Issue #1140 is complete.
- The local consolidation into `Claire_de_Binare` is complete.
- The separate docs-hub repository has been retired from productive use.
- The working repo is the only productive documentation, governance, knowledge,
  agent, template, and navigation source.

## Local Provenance

The old docs-hub content remains preserved locally as provenance only:

- `docs/archive/docs_hub_snapshot/`

This snapshot is intentional and should not be cosmetically rewritten.

## What Still Mentions The Old Docs Hub

Remaining mentions of the old docs hub in the working repo are now limited to
these categories:

- closeout documentation under `docs/meta/`
- legacy-note files that explain the retired split-repo model
- guard patterns that detect stale split-repo references
- compatibility names such as `DOCS_HUB_PATH` that still exist in code or CLI
  surfaces
- historical reports or evidence that describe past states

These mentions are not productive dependencies.

## Operational Status

- no active standard path requires the deleted docs-hub repo
- no active resolver requires the deleted docs-hub repo
- the working repo functions as the sole productive docs source

## Snapshot Retention Policy (#1146)

The local archive at `docs/archive/docs_hub_snapshot/` is classified into three
retention buckets:

1. **Provenance / narrow compatibility core** — audit-relevant material and
   specific `knowledge/` subtrees still referenced by archive-aware tooling.
   Intentionally kept.
2. **Later review target** — low-signal or redundant areas such as historical
   navpacks (`mcp_navpack_docs_hub*`), deprecated pipeline archives, quarantined
   legacy content, and duplicate agent/knowledge mirrors. Retained but not
   active input for any current workflow.
3. **Not changed in #1146** — no archive content is deleted, moved, or
   reorganized as part of this retention clarification.

## Optional Maintainer Follow-Up

If the remote docs-hub repository still exists, it should be treated as
redundant history only. Remaining manual checks, if desired:

- remove stale IDE workspaces or bookmarks
- remove personal shell aliases or scripts that point to the old repo
- check external automation or local task runners for dead path assumptions
- archive or delete the remote repo according to maintainer policy

## Conclusion

The system now operates fully without a separate docs-hub repository.
