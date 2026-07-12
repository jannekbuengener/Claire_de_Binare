# npm-cache Cleanup Evidence (redacted)

Issue: [#4001](https://github.com/jannekbuengener/Claire_de_Binare/issues/4001)  
Parent: [#3999](https://github.com/jannekbuengener/Claire_de_Binare/issues/3999)  
Phase: **Preflight + Apply + Verification**  
Apply as of (UTC): `2026-07-12T19:30:54Z`

## Status

**`DONE_APPLY_OK`** — Human-GO (`APPLY_APPROVED`) executed; awaiting PR merge for `DONE_MERGED_CLOSED`.

## Scope confirmation

| Check | Result |
|-------|--------|
| Exclusive path | `D:\Dev\Tools\npm-cache` |
| `npm config get cache` | matches scope |
| Root reparse/junction | none |
| Excluded paths untouched | yes (existence verified) |

## Before (preflight baseline)

| Metric | Value |
|--------|------:|
| Size (GB) | 58.714 |
| Size (bytes) | 63,043,419,766 |
| Files | 57,958 |
| Directories | 17,461 |
| Access errors | 0 |

## Apply

| Field | Value |
|-------|------:|
| Command | `npm cache clean --force` |
| Exit code | 0 |
| Duration (s) | 18.29 |

## After (post-apply measurement)

| Metric | Value |
|--------|------:|
| Size (GB) | 0.27 |
| Size (bytes) | 290,025,604 |
| Files | 45,599 |
| Directories | 5,268 |
| Access errors | 0 |
| Scan status | complete |

## Reclaim vs preflight baseline

| Metric | Value |
|--------|------:|
| Bytes freed | 62,753,394,162 |
| GB freed | 58.444 |

Remaining ~0.27 GB is empty npm cache skeleton (directory structure); `npm cache verify` reports **0 content bytes**.

## Cache smoke

```
npm cache verify → exit 0
Content verified: 0 (0 bytes)
Index entries: 0
```

## Protected areas (unchanged)

- `D:\Dev\Tools\npm` — present
- `D:\Dev\AI` (Ollama) — present
- `D:\Dev\Backups` — present
- `D:\Dev\Workspaces\Repos` — present

## Tools

- Preflight: `tools/cleanup/npm_cache_preflight.ps1`
- Apply + verify: `tools/cleanup/npm_cache_apply.ps1`

## Raw artifacts (local, gitignored)

- `artifacts/local-dev-hygiene/npm-cache-cleanup/preflight.json`
- `artifacts/local-dev-hygiene/npm-cache-cleanup/dry_run.md`
- `artifacts/local-dev-hygiene/npm-cache-cleanup/apply_result.json`
- `artifacts/local-dev-hygiene/npm-cache-cleanup/before_after.md`
