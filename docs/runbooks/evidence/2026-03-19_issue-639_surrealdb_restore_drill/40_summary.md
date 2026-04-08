# Issue #639 SurrealDB Restore Drill Evidence

Status: PASS
Timestamp: 2026-03-19 Europe/Berlin
Active container: cdb_surrealdb
Active volume: cdb_database_surrealdb_data
Backup name: cdb_backup_20260319_200420
Archive: F:\Claire_Backups\cdb_backup_20260319_200420.zip

Preflight:
- cdb_surrealdb running, healthy, restartCount=0
- /surreal is-ready => OK
- Active volume matches script default: cdb_database_surrealdb_data
- Disposable baseline seeded in governance/governance_mirror

Baseline evidence:
- Tables present: governance_events, audit_trail, ledger_event
- Pre counts: governance_events=1, audit_trail=1, ledger_event=1
- Pre volume metrics: 4 files, 80459 bytes

Destructive step:
- Stopped cdb_surrealdb
- Cleared cdb_database_surrealdb_data via alpine helper
- Verified destroyed state: 0 files, 4096 bytes, container exited
- Verified readiness no longer available while container stopped

Backup evidence:
- backup_all.ps1 -IncludeSurrealDB exit code 0
- Manifest Components.SurrealDB = true
- Manifest Evidence.SurrealDB present
- Manifest SurrealDB volume = cdb_database_surrealdb_data
- Manifest SurrealDB metrics = 4 files / 57036 bytes
- Manifest QueryStatus = count_check_unavailable

Restore evidence:
- restore_all.ps1 -BackupName cdb_backup_20260319_200420 -Force exit code 0
- Post restore container status: running, healthy, restartCount=0
- /surreal is-ready => OK
- Post volume metrics: 4 files, 82484 bytes
- Post counts: governance_events=1, audit_trail=1, ledger_event=1
- Seed records restored with same record ids: governance_events:issue639_pre, audit_trail:issue639_pre, ledger_event:issue639_pre

Assessment:
- This was a real destructive drill, not a restart over intact data
- Physical restore path is proven locally
- Scripted manifest count evidence remains limited because backup_all.ps1 still marks QueryStatus=count_check_unavailable
