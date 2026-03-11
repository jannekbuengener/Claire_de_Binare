# Verlosung Archive Handoff Note

**Date:** 2026-01-02
**Status:** ARCHIVED

## Summary
The documentation files from the `verlosung` directory have been moved to this archive location (`knowledge/archive/verlosung`) to comply with the Docs Hub governance (clean root, structured knowledge).

## Secrets
Sensitive files (`.key`, `.crt`, `.dh`) were identified in `verlosung` and have been moved to a secure external quarantine location.
See `verlosung/VERLOSUNG_SECRET_MANIFEST.md` in the root of the `verlosung` folder (or its new location) for details.

## Remaining Files
Code files (`.py`, `.ps1`) and workflow configurations (`.yml`) remain in the `verlosung` folder (or have been left for subsequent cleanup slices) as they belong to the Working Repo or need consolidation.

## Action Items
- Review archived documents for relevance.
- Migrate valid knowledge to `knowledge/` structure.
- Delete obsolete files.
