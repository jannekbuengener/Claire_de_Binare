# Windows Worktree Y: Root Contract

Status: Canonical for local Windows operator host  
Issues: #4386, #4387–#4393  
LR: NO-GO (orthogonal)

## Rule

On the **local Windows operator host**, all **newly created** additional Git
worktrees MUST reside under:

```text
Y:\Worktrees\<repository>\<worktree-name>
```

- `C:` and `D:` MUST NOT be used for new additional worktrees.
- If the canonical `Y:` root is unavailable or not writable, creation MUST
  fail closed. No fallback path is permitted.
- The **main checkout** MAY remain on `D:` (e.g.
  `D:\Dev\Workspaces\Repos\Claire_de_Binare`).
- Linux / CI / Hermes are **not** bound to a Windows drive letter.

## Environment

| Name | Meaning |
|---|---|
| `CDB_WORKTREE_ROOT` | Optional override; default on Windows is `Y:\Worktrees` |

## Governed commands

```powershell
python -m tools.worktrees resolve-root
python -m tools.worktrees resolve-path --repository Claire_de_Binare --name issue-4386
python -m tools.worktrees validate-path --path 'Y:\Worktrees\Claire_de_Binare\foo'
python -m tools.worktrees validate-path --purpose main_checkout --path 'D:\Dev\Workspaces\Repos\Claire_de_Binare'
python -m tools.worktrees create --repository Claire_de_Binare --name issue-4386 --branch dedicated/ci-tooling-issue-4386
# add --execute only after dry-run PASS
python -m tools.worktrees reconcile --from-git
```

Dry-run is the default for `create`.

## Reason codes (selected)

| Code | Meaning |
|---|---|
| `WORKTREE_PATH_ALLOWED` | Path under Y: root PASS |
| `WORKTREE_ON_C_DRIVE` | New create on C: FAIL |
| `WORKTREE_ON_D_DRIVE` | New create on D: FAIL |
| `WORKTREE_OUTSIDE_CANONICAL_ROOT` | Outside root FAIL |
| `WORKTREE_ROOT_UNAVAILABLE` | Root missing FAIL |
| `WORKTREE_ROOT_NOT_WRITABLE` | Root not writable FAIL |
| `WORKTREE_POLICY_NOT_APPLICABLE` | Linux/CI skip |
| `MAIN_CHECKOUT_ALLOWED` | Main on D: OK |

## Legacy reconcile classes

| Class | Meaning |
|---|---|
| `OBSOLETE_REMOVE` | Clean + merged/prunable; controlled remove candidate |
| `NEEDED_QUICK_FINISH` | Clean, active issue, finish then cleanup |
| `NEEDED_FOLLOWUP_ISSUE` | Remaining work needs a GitHub issue |
| `UNCLEAR_HOLD` | Dirty/unpushed/locked/incomplete → STOP |

Classification is read-only. No blind delete/migrate.

## Related

- Consumer map: [`docs/ops/worktree_path_consumer_map.md`](../ops/worktree_path_consumer_map.md)
- Parent epic: #4386
