# Session Log: 2026-07-31 — Issue #3612 PG15 Archive Cleanup Preflight

## Auftrag

Read-only, fail-closed Preflight für spätere Entfernung von `/data/.pg15_archived/`.
Kein Delete, kein Cleanup, kein Volume-Zugriff.

## Scope / Boundaries

- Autorisiert: Preflight-Tool, Unit-Tests, Runbook, BACKUP_AUTOMATION Cross-Ref
- Nicht autorisiert: Volume-Mutation, Postgres start/stop, Backup erzeugen/löschen, Merge, Issue-Close
- LR: NO-GO (unverändert)

## Brain Evidence

- brain_source: repo-only
- brain_status: not-used
- repo_crosscheck: Issue #3612 (OPEN), #3600 migration log, compose.blue.yml postgres:18.4-alpine
- PR router: CREATE_NEW_BATCH_PR, lane ci-tooling, UNLOCKED

## Delivered

- `tools/postgres/pg15_archive_cleanup_preflight.py` — read-only evidence evaluator
- `tests/unit/tools/postgres/test_pg15_archive_cleanup_preflight.py` — targeted unit tests + static no-destructive proof
- `docs/runbooks/PG15_ARCHIVE_CLEANUP.md` — operator runbook
- `docs/runbooks/BACKUP_AUTOMATION.md` — cross-reference section

## Validation

- `pytest tests/unit/tools/postgres/test_pg15_archive_cleanup_preflight.py`
- `ruff check tools/postgres/ tests/unit/tools/postgres/`
- `black --check` on changed Python files
- `python -m tools.validate_readme_links`
- `git diff --check`
- `gitleaks protect --staged`

## Status

`DONE_PREFLIGHT_SLICE_ADDED_TO_PR` — merge and issue close out of scope.
