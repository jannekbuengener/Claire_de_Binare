# npm-cache Cleanup Evidence (redacted, preflight + dry-run)

Issue: [#4001](https://github.com/jannekbuengener/Claire_de_Binare/issues/4001)  
Parent: [#3999](https://github.com/jannekbuengener/Claire_de_Binare/issues/3999)  
Phase: **Preflight + Dry-run only** (no apply)  
Scan as of (UTC): `2026-07-12T18:36:07Z`

## Status

**`READY_FOR_HUMAN_APPLY_GO`**

Apply remains **blocked** until explicit Human-GO (`apply-approved` or equivalent) on #4001.

## Scope confirmation

| Check | Result |
|-------|--------|
| Exclusive path | `D:\Dev\Tools\npm-cache` |
| `npm config get cache` | matches scope |
| Root reparse/junction | none |
| Excluded paths untouched | yes |

## Live preflight measurement

| Metric | Value |
|--------|------:|
| Size (GB) | 58.714 |
| Files | 57,958 |
| Directories | 17,461 |
| Scan duration (s) | 5.82 |
| Access errors | 0 |
| Scan status | complete |

#3999 estimate (58.714 GB) matches live preflight exactly.

## Dry-run plan

- **Planned action:** `npm cache clean --force`
- **Expected reclaim:** ~58.7 GB
- **Risk:** low (REGENERABLE)
- **Recovery:** cache rebuilds on next `npm install` / `npm ci`; optional `npm cache verify`

Internal npm hardlink entries (`@@@` suffix) were observed but not traversed; canonical apply uses npm tooling, not manual deletion.

## Raw artifacts (local, gitignored)

- `artifacts/local-dev-hygiene/npm-cache-cleanup/preflight.json`
- `artifacts/local-dev-hygiene/npm-cache-cleanup/dry_run.md`

## Next step

Human-GO on #4001 for Phase 3 apply, then post-apply verification (Phase 4).
