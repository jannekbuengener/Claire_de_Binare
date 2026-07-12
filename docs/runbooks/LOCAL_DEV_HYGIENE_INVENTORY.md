# Runbook: Local Dev Hygiene Inventory (#3999)

Status: canonical  
Issue: [#3999](https://github.com/jannekbuengener/Claire_de_Binare/issues/3999)  
Scope: read-only metadata inventory for `D:\Dev\{AI,Backups,Workspaces\Repos,Tools}`

## Goal

Produce a reproducible, read-only inventory and cleanup manifest for the local
Windows development workspace without deleting, moving, or mutating files.

## Boundaries

- **In scope:** metadata scan, classification, redacted evidence publication.
- **Out of scope:** deletion, archive moves, `git clean`, `docker prune`, child
  issues, Docker/DB/runtime mutation.
- **Not a duplicate of:** #282 (Docker), #291 (monthly cadence), #1332
  (governance provenance inside CDB repo).

## Outputs

| Output | Location | Git tracked |
|--------|----------|-------------|
| Raw inventory JSON | `artifacts/local-dev-hygiene/workspace_inventory.json` | No (gitignored) |
| Raw candidates/plan | `artifacts/local-dev-hygiene/cleanup_*.json/md` | No |
| Redacted evidence | `docs/evidence/local_dev_hygiene/LOCAL_DEV_HYGIENE_EVIDENCE.*` | Yes |

Raw outputs may contain paths that must not be published. Only the redacted
evidence summary is commit-worthy.

## Prerequisites

- Windows workstation with access to all four `D:\Dev` roots.
- PowerShell 5.1+.
- Python 3.12 + repo dependencies.
- Git available on PATH.

## Execution

From repo root:

```powershell
make local-dev-hygiene-inventory
```

Or manually:

```powershell
.\tools\cleanup\local_dev_workspace_inventory.ps1 `
  -ConfigPath infrastructure\config\ops\local_dev_hygiene.json
python -m tools.cleanup.local_dev_hygiene_classify `
  --inventory artifacts/local-dev-hygiene/workspace_inventory.json
```

## Scanner guarantees

1. **Fixed timestamp:** `scan_as_of_utc` written once at scan start; classifier
   and tests use this value for age buckets.
2. **Reparse points:** junctions/symlinks recorded, never traversed.
3. **Memory-safe:** streaming aggregation only; no full 400k+ file list in output.
4. **Fail-closed:** `AccessDenied`, long paths, and partial scans set
   `scan_status=partial` and populate `access_errors` / `limitations`.
5. **Dynamic git discovery:** all top-level repos under `Repos`; all worktrees
   from `git worktree list --porcelain` → `PROTECTED`.

## Classification rules (8 classes)

| Class | Meaning |
|-------|---------|
| KEEP_ACTIVE | Actively required |
| KEEP_PROVENANCE | Historical evidence / provenance |
| REGENERABLE | Rebuild from lockfile/installer |
| ARCHIVE_MOVE | Keep, move out of active dev area |
| DEDUPLICATE | Duplicate with evidence only |
| QUARANTINE_REVIEW | Unclear; manual review |
| DELETE_CANDIDATE | Removable after evidence review |
| PROTECTED | Never automated |

`DEDUPLICATE` requires one of:

- identical git remote **and** commit, with clean worktree, or
- bounded hash match on pre-narrowed candidates.

Otherwise assign `QUARANTINE_REVIEW`.

## Per-root completeness fields

Each root entry includes:

- `scan_status`, `access_errors`, `skipped_reparse_points`,
  `scan_duration_seconds`, `baseline_delta`, `completeness`, `limitations`

## Baseline plausibility

Screenshot baseline (Explorer-oriented):

- Total ~134.27 GB
- 414,174 files
- 71,093 directories

Compare logical byte totals with documented tolerance (default ±10% size,
±5% counts). Explorer vs logical size differences are expected.

## Review gate

Do **not** create child issues until a human reviews:

1. `docs/evidence/local_dev_hygiene/LOCAL_DEV_HYGIENE_EVIDENCE.md`
2. Local raw `cleanup_plan.md` (if needed for detail)

Proposed child slices remain deferred per issue body.

## Validation

```powershell
pytest -q tests/unit/cleanup/test_local_dev_hygiene_classify.py -m unit
ruff check tools/cleanup/local_dev_hygiene_classify.py tests/unit/cleanup/
python -m tools.cleanup.local_dev_hygiene_classify --validate-only
```

## Related runbooks

- [`local_ops_artifacts.md`](local_ops_artifacts.md) — repo-local artifact policy
- [`mcp_worktree_hygiene.md`](mcp_worktree_hygiene.md) — worktree drift
- [`MONTHLY_MAINTENANCE.md`](../../knowledge/operations/MONTHLY_MAINTENANCE.md) — cadence (#291)
