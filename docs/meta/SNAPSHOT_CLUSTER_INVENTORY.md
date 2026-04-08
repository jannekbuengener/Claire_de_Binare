# Snapshot Cluster Inventory

Status: active classification record
Issue: #1235
Recorded: 2026-03-28
Subject: `docs/archive/docs_hub_snapshot/` (635 files, post-#1140 retention)

## Purpose

This inventory classifies every major cluster inside the frozen snapshot.
It distinguishes frozen-provenance content (must be retained for audit or
compat) from low-visibility candidates (no active references, safe to prune
in a future explicit decision).

The snapshot as a whole is already excluded from `docs-conflict-guard.yml`
and marked `linguist-documentation=true` in the root `.gitattributes` (#1235).
No content has been deleted or reorganized as part of this inventory.

---

## Cluster Registry

### 1. `mcp_navpack_docs_hub` … `mcp_navpack_docs_hub_5` (5 directories)

| Field | Value |
|---|---|
| Files | 31 |
| Class | **low-visibility-candidate** |
| Description | Five generations of navpacks generated from the retired docs-hub topology. Contain dead paths (`.worktrees/`, sibling repo). |
| Active references outside snapshot | None (meta-docs + guard exclusion only) |
| Runtime/tool dependency | None — `docs_hub_rag_adapter.py` does not enumerate these dirs |
| Deletion readiness | **Yes — pending explicit prune decision** |
| Blocker | None identified |

### 2. `_archive/discussion_pipeline/`

| Field | Value |
|---|---|
| Files | 43 |
| Class | **low-visibility-candidate** |
| Description | Archived artifacts from the deprecated multi-LLM discussion pipeline (decommissioned, see `knowledge/logs/decisions/DEPRECATE_DISCUSSION_PIPELINE.md`). |
| Active references outside snapshot | Only in dead `.worktrees/` state and the deprecation notice itself |
| Runtime/tool dependency | None |
| Deletion readiness | **Yes — pending explicit prune decision** |
| Blocker | None identified |

### 3. `_legacy_quarantine/`

| Field | Value |
|---|---|
| Files | 10 |
| Class | **low-visibility-candidate** |
| Description | Legacy prompt and session artifacts from the pre-#1140 split-repo era. Already quarantined in the original docs-hub. |
| Active references outside snapshot | None |
| Runtime/tool dependency | None |
| Deletion readiness | **Yes — pending explicit prune decision** |
| Blocker | None identified |

### 4. `knowledge/archive/docs_legacy/`

| Field | Value |
|---|---|
| Files | 16 |
| Class | **low-visibility-candidate** |
| Description | Obvious duplicates of content migrated into active `knowledge/` paths during #1140. |
| Active references outside snapshot | None |
| Runtime/tool dependency | None |
| Deletion readiness | **Yes — pending explicit prune decision** |
| Blocker | None identified |

### 5. `agents/` (snapshot mirror)

| Field | Value |
|---|---|
| Files | ~30 |
| Class | **frozen-provenance** |
| Description | Mirror of the docs-hub `agents/` tree as it existed before #1140. Active counterparts live at `agents/` in the working-repo root. |
| Active references outside snapshot | None productive |
| Runtime/tool dependency | None |
| Deletion readiness | Deferred — provenance value; not blocking active work |
| Blocker | Provenance preference only |

### 6. `knowledge/` (snapshot mirror, ~400 files)

| Field | Value |
|---|---|
| Files | ~400 |
| Class | **frozen-provenance** |
| Description | Mirror of the docs-hub `knowledge/` tree. Also contains `knowledge/archive/docs_legacy/` (see cluster #4 above). |
| Active references outside snapshot | Scanned by `docs_hub_rag_adapter.py` **only in snapshot-fallback mode** (`DOCS_HUB_PATH` pointing at snapshot, or working-repo invalid). Normal operation uses the working-repo root; snapshot is never the primary target. |
| Runtime/tool dependency | The adapter uses `DEFAULT_INCLUDE_DIRS = ("knowledge", "agents", "meta")` — no specific subtrees are hardcoded. `cdb_docs_index.yaml` at snapshot root is referenced as a legacy index name (`ROOT_INDEX_FILES`). The named subtree list in `DOCS_HUB_DELETE_READINESS.md` describes snapshot content, not adapter code paths. |
| Deletion readiness | Deferred — provenance preference; low operational risk but prune decision requires separate review |
| Blocker | `cdb_docs_index.yaml` root file (compat name in `ROOT_INDEX_FILES`); the bulk `knowledge/` tree has no hard code dependency |

### 7. `verlosung/` (snapshot root)

| Field | Value |
|---|---|
| Files | 2 (`verlosung/README.md`, `verlosung/VERLOSUNG_SECRET_MANIFEST.md`) |
| Class | **frozen-provenance** |
| Description | Snapshot-root directory containing the secret-manifest provenance record from the split-repo era. |
| Active references outside snapshot | None |
| Runtime/tool dependency | None |
| Deletion readiness | Deferred — provenance preference; prune requires separate review |
| Blocker | Secret-manifest provenance record only |

### 8. Root index files

| Field | Value |
|---|---|
| Files | ~5 (`DOCS_HUB_INDEX.md`, `index.yaml`, `cdb_docs_index.yaml`, `issues.md`, `README.md`) |
| Class | **frozen-provenance** |
| Description | Historical navigation and index artifacts from the pre-#1140 docs hub. `cdb_docs_index.yaml` is retained as a behavior-bearing compat name in `docs_hub_rag_adapter.py`. |
| Active references outside snapshot | `docs_hub_rag_adapter.py` (compat name only) |
| Deletion readiness | Deferred — `cdb_docs_index.yaml` is a compat constraint; others are provenance-only |

---

## Low-Visibility Review Targets — Summary

The four clusters below collectively represent ~100 files with no active
references outside the snapshot. They are the strongest candidates for lower
visibility or a later explicit prune decision.

| Cluster | Files | Active references | Operational weight |
|---|---|---|---|
| `mcp_navpack_docs_hub*` (5 dirs) | 31 | None | Frozen historical navpacks; no productive navigation role |
| `_archive/discussion_pipeline/` | 43 | Meta-docs/deprecation notice only | Deprecated pipeline archive; provenance only |
| `_legacy_quarantine/` | 10 | None | Quarantined legacy material; no active input role |
| `knowledge/archive/docs_legacy/` | 16 | None | Duplicate / obsolete legacy archive material |
| **Total** | **100** | | |

Low-visibility candidate does **not** mean implicit deletion.
Deletion, relocation, or pruning remains a future explicit decision requiring explicit maintainer sign-off.
No content is deleted or reorganized as part of this inventory.

---

## Guards In Place (verified 2026-03-28)

| Guard | Coverage | File |
|---|---|---|
| `docs-conflict-guard.yml` excludes full snapshot tree | Full snapshot | `.github/workflows/docs-conflict-guard.yml` |
| `linguist-documentation=true` for snapshot tree | Full snapshot, GitHub search/Linguist | `.gitattributes` (added #1235) |
| README classification table | Full snapshot, navigation disambiguation | `docs/archive/docs_hub_snapshot/README.md` |
| Retention bucket taxonomy | Full snapshot, prune governance | `docs/meta/DOCS_HUB_DELETE_READINESS.md` |
