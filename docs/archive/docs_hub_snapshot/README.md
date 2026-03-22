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

## Search and Navigation Disambiguation

File names inside this snapshot overlap with active working-repo files.
Searches by file name will surface stale archive hits alongside live results.

**Navpack files** (`ENTRYPOINTS.yaml`, `NAVPACK.manifest.json`,
`QUERIES.snippets.yaml`, `DOCS.taxonomy.json`, `INDEX.high_signal.json`,
`LINKS.graph.json`):
- Active version: `mcp_navpack_working_repo/` (repo root).
- The five `mcp_navpack_docs_hub*/` directories here are frozen historical
  navpacks generated from the retired docs-hub topology. They reference
  dead paths (`.worktrees/`, the retired sibling repo) and must not be used
  as a navigation baseline.

**Domain mirror files** (`AGENTS.md`, `CLAUDE.md`, `CODEX.md`,
`CURRENT_STATUS.md`, `SYSTEM.CONTEXT.md`, `CDB_KNOWLEDGE_HUB.md`, etc.):
- Active versions: `agents/` and `knowledge/` at working-repo root.
- The mirrors under `docs/archive/docs_hub_snapshot/agents/` and
  `docs/archive/docs_hub_snapshot/knowledge/` are frozen snapshots from the
  pre-`#1140` split-repo era.

Rule: always resolve navigation through `mcp_navpack_working_repo/`,
`agents/AGENTS.md`, or `docs/meta/WORKING_REPO_CANON.md` — never through
this snapshot.

## Snapshot Classification

The names inside this snapshot intentionally mirror the retired docs-hub
topology. That makes some paths look active even though the whole tree is
frozen.

| Class | Examples in this snapshot | Maintainer rule |
| --- | --- | --- |
| Frozen snapshot mirrors | `agents/`, `knowledge/`, `meta/`, `scripts/`, `tools/` | These are historical mirrors of formerly active areas. Do not treat them as the current source of truth, even if individual files still say "canonical" or "write here". |
| Historical/quarantined content | `_archive/`, `_legacy_quarantine/`, `verlosung/`, `meta/legacy/`, `meta/migrations/` | Provenance only. Keep for audit/history; do not reactivate by accident. |
| Generated historical navigation artifacts | `mcp_navpack_docs_hub*/`, `DOCS.taxonomy.json`, `LINKS.graph.json`, `NAVPACK.manifest.json`, `ENTRYPOINTS.yaml`, `QUERIES.snippets.yaml` | Generated from the retired docs-hub structure. They may mention `.worktrees/` and other dead paths. Never use them as the current navigation baseline. Active navpack: `mcp_navpack_working_repo/` (repo root). These five directories are candidates for deletion in a future explicit prune decision — see `docs/meta/DOCS_HUB_DELETE_READINESS.md`. |
| Compatibility/provenance root files | `DOCS_HUB_INDEX.md`, `index.yaml`, `cdb_docs_index.yaml`, `issues.md`, `README.md` | Retained for comparison, adapter compatibility, or audit trace. Not default edit targets. |

## Maintainer Guardrail

If a file under this snapshot claims to be canonical, authoritative, or the
place to write, read that as historical wording from the pre-`#1140` split-repo
state.

For active canon, use the working-repo entrypoints instead:
- `docs/meta/WORKING_REPO_CANON.md`
- `agents/AGENTS.md`
- `knowledge/`
- `docs/`
- `.github/`
- `mcp_navpack_working_repo/`

## Retention note

Content in this snapshot is retained pending explicit review decisions.
No archive content is deleted or reorganized as part of the initial retention policy (#1146).
See `docs/meta/DOCS_HUB_DELETE_READINESS.md` for the full retention assessment.
