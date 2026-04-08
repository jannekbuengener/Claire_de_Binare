# SurrealDB Rollback & Cutover Plan (P0)

SurrealDB is a **sidecar**. Postgres remains the source of truth for trading state.
All cutovers must be reversible and **zero-data-loss**.

## Feature Flags (Env/Config)

**Config file:** `infrastructure/config/surrealdb/feature-flags.yaml`

- `surrealdb_enabled` (bool): master switch (default: false)
- `governance_source` (git | surrealdb): query source for governance reads
- `mirror_enabled` (bool): enable mirror ingestion (default: false)

**One-command disable (immediate rollback):**
```
set CDB_GOVERNANCE_SOURCE=git
```
or set `surrealdb_enabled: false` in the config file.

## Cutover (Reversible)

1. Enable mirror ingestion (`mirror_enabled: true`)
2. Run shadow reads (SurrealDB vs Git) and compare hashes
3. Switch read source (`governance_source: surrealdb`)
4. Keep Git as canonical (no writes to SurrealDB)

**Rollback:** set `governance_source: git` and/or `surrealdb_enabled: false`.

## No Data Loss Guarantees

- Trading state stays in Postgres
- Governance data remains in Git
- Ledger / evidence remain canonical in Git-backed artifacts
- SurrealDB is mirror-only / append-only

## Backup / Restore Scope (Issue #639)

- This issue adds a **physical** backup / restore path for the SurrealDB file backend only.
- It does **not** introduce a Governance importer, ownership switch, or shared-memory backup scope.
- Repo-canonical restore target for this cut is the file-backed sidecar volume behind `cdb_surrealdb` (`file:/data/surrealdb`).
- Minimal namespace / database decision for backup evidence and restore verification: `governance` / `governance_mirror`, because that is the repo-visible setup in `infrastructure/surrealdb/setup.surql`.
- Legacy examples that still mention `cdb` / `cdb` are not expanded by this issue; they remain follow-up cleanup work.

## Restore Drill (Scenario + Steps)

**Scenario:** SurrealDB corruption or outage.

**Steps:**
1. Set `governance_source: git` and/or `surrealdb_enabled: false` so reads fall back immediately.
2. Create a backup with `.\infrastructure\scripts\backup_all.ps1 -IncludeSurrealDB`.
3. Run a **destructive** restore with `.\infrastructure\scripts\restore_all.ps1 -BackupName <name> -Force`.
4. Confirm that the restore path cleared the SurrealDB target volume before copying the archived `surrealdb_data` payload back in.
5. Confirm `cdb_surrealdb` becomes healthy again and the post-restore verification matches the manifest evidence.

**PASS**

- `manifest.json` shows `Components.SurrealDB = true`
- Restore log shows volume metrics match the backup artifact
- `cdb_surrealdb` passes `/health`
- If count evidence was captured at backup time, the same counts are observed after restore

**FAIL**

- Restore relies on pre-existing volume contents
- `surrealdb_data` is missing or incomplete
- Container restart or health check fails
- Count verification fails where evidence exists

**Evidence**

- ZIP archive containing `surrealdb_data/`
- `manifest.json` with `Evidence.SurrealDB`
- Restore console log showing destructive clear + post-restore verification

## Machine-Readable Config

- `infrastructure/config/surrealdb/feature-flags.yaml`
