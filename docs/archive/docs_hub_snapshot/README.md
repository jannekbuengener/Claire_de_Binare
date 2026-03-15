# Docs Hub Snapshot (Local Archive)

Status: read-only archive
Related issue: #1140

## What this is

This directory contains a local snapshot of the former standalone `Claire_de_Binare_Docs` repository.
The split-repo model was retired in #1140. All active documentation now lives in the working repo.

This snapshot is preserved as:
- **provenance** — audit trail for historical content and decisions
- **narrow compatibility core** — specific files under `knowledge/` that are still referenced by archive-aware tooling (e.g., `docs_hub_rag_adapter.py`)

## Usage

- This is **not** the default edit target. Active canon lives at the working-repo paths listed in `docs/meta/WORKING_REPO_CANON.md`.
- Read-only. Do not modify archive content for active work.
- Historical lookup and audit provenance only.

## Contents

- `DOCS_HUB_INDEX.md` — historical navigation index (archived)
- `agents/`, `knowledge/`, `meta/`, `scripts/`, `tools/` — snapshotted docs-hub content
- `_archive/`, `_legacy_quarantine/` — material that was already deprecated in the old docs hub
- `mcp_navpack_docs_hub*/` — historical navigation packs from the old repo
- `verlosung/` — experimental migration artifacts

## Retention note

Content in this snapshot is retained pending explicit review decisions.
No archive content is deleted or reorganized as part of the initial retention policy (#1146).
See `docs/meta/DOCS_HUB_DELETE_READINESS.md` for the full retention assessment.
