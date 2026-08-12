# CDB Bulk-Storage Path Contract

Status: Canonical Windows host policy for #4419. This is a policy and config
foundation only; it neither provisions directories nor migrates data.

## Canonical root and layout

```text
Y:\CDB-Storage\
  market-history\
  replay-arvp\
  logs\
  evidence\
  archive\
```

`Y:\Worktrees` is exclusively the governed Git-worktree root. Bulk data MUST
never be placed there. Junctions and symlinks are not an accepted substitute
for this contract.

## Configuration surface

New consumers opt in with `CDB_BULK_STORAGE_ROOT=Y:\CDB-Storage`. They must
resolve a named subtree with `tools.storage.bulk_storage_contract`; missing,
non-canonical, `Y:\Worktrees`, or reparse-point roots fail closed. The helper
does not create paths and has no fallback root.

Existing `CDB_WINDOW_BANK_ROOT` and `CDB_DATASET_ROOT` consumers remain
unchanged in this issue. Existing repo-relative market-data paths, ARVP/replay
artifact roots, and Compose `logs` binds also remain in place until their
separate migration issues. No automatic copy, move, deletion, or junction
cutover is permitted.

## Retention mapping

| Subtree | Retention intent |
| --- | --- |
| `market-history` | Preserve long-term replay and research reproducibility. |
| `replay-arvp` | Retain campaign/replay data under its evidence policy. |
| `logs` | Distinguish active local logs from separately archived logs. |
| `evidence` | Preserve auditable evidence. |
| `archive` | Hold explicitly archived material. |

Reproducible caches do not belong in this durable bulk store.

## Consumer adoption rule

A consumer may use this root only in a later, explicitly scoped migration
issue. That issue must validate the configured target before writing and must
not infer a replacement for its current D:/repo-relative path.
