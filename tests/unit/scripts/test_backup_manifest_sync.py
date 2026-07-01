"""Unit tests for backup manifest helper reconciliation (no Docker)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
HELPERS = REPO_ROOT / "infrastructure" / "scripts" / "backup_manifest_helpers.ps1"


def _ps_path(path: Path) -> str:
    return str(path).replace("'", "''")


def _run_helpers(script_body: str) -> dict:
    command = f". '{_ps_path(HELPERS)}'; {script_body}"
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    text = result.stdout.strip()
    json_line = text.splitlines()[-1]
    return json.loads(json_line)


@pytest.mark.unit
def test_sync_sets_redis_true_when_rdb_present(tmp_path: Path) -> None:
    work_dir = tmp_path / "backup"
    work_dir.mkdir()
    (work_dir / "redis_dump.rdb").write_bytes(b"redis-data")

    payload = _run_helpers(
        f"""
$status = @{{ Postgres = $false; Redis = $false; SurrealDB = $false }}
$evidence = @{{ Postgres = @{{}}; Redis = @{{}}; SurrealDB = @{{}} }}
Sync-BackupComponentManifest -WorkDir '{_ps_path(work_dir)}' -ComponentStatus $status -ComponentEvidence $evidence
@{{ Redis = $status.Redis; SizeBytes = $evidence.Redis.SizeBytes }} | ConvertTo-Json -Compress
"""
    )

    assert payload["Redis"] is True
    assert payload["SizeBytes"] == len(b"redis-data")


@pytest.mark.unit
def test_sync_keeps_redis_false_when_rdb_missing(tmp_path: Path) -> None:
    work_dir = tmp_path / "backup"
    work_dir.mkdir()

    payload = _run_helpers(
        f"""
$status = @{{ Postgres = $false; Redis = $false; SurrealDB = $false }}
$evidence = @{{ Postgres = @{{}}; Redis = @{{}}; SurrealDB = @{{}} }}
Sync-BackupComponentManifest -WorkDir '{_ps_path(work_dir)}' -ComponentStatus $status -ComponentEvidence $evidence
@{{ Redis = $status.Redis }} | ConvertTo-Json -Compress
"""
    )

    assert payload["Redis"] is False


@pytest.mark.unit
def test_sync_keeps_redis_false_when_rdb_empty(tmp_path: Path) -> None:
    work_dir = tmp_path / "backup"
    work_dir.mkdir()
    (work_dir / "redis_dump.rdb").write_bytes(b"")

    payload = _run_helpers(
        f"""
$status = @{{ Postgres = $false; Redis = $true; SurrealDB = $false }}
$evidence = @{{ Postgres = @{{}}; Redis = @{{}}; SurrealDB = @{{}} }}
Sync-BackupComponentManifest -WorkDir '{_ps_path(work_dir)}' -ComponentStatus $status -ComponentEvidence $evidence
@{{ Redis = $status.Redis }} | ConvertTo-Json -Compress
"""
    )

    assert payload["Redis"] is False


@pytest.mark.unit
def test_sync_sets_postgres_true_when_dump_present(tmp_path: Path) -> None:
    work_dir = tmp_path / "backup"
    work_dir.mkdir()
    (work_dir / "postgres_dump.sql").write_text(
        "PostgreSQL database dump\n", encoding="utf-8"
    )

    payload = _run_helpers(
        f"""
$status = @{{ Postgres = $false; Redis = $false; SurrealDB = $false }}
$evidence = @{{ Postgres = @{{}}; Redis = @{{}}; SurrealDB = @{{}} }}
Sync-BackupComponentManifest -WorkDir '{_ps_path(work_dir)}' -ComponentStatus $status -ComponentEvidence $evidence
@{{ Postgres = $status.Postgres; Artifact = $evidence.Postgres.Artifact }} | ConvertTo-Json -Compress
"""
    )

    assert payload["Postgres"] is True
    assert payload["Artifact"] == "postgres_dump.sql"


@pytest.mark.unit
def test_resolve_inclusion_treats_redis_artifact_as_included(tmp_path: Path) -> None:
    backup_root = tmp_path / "archive"
    backup_root.mkdir()
    (backup_root / "redis_dump.rdb").write_bytes(b"redis-data")

    payload = _run_helpers(
        f"""
$result = Resolve-BackupComponentInclusion `
    -BackupRoot '{_ps_path(backup_root)}' `
    -ManifestFlag $false `
    -ComponentName 'Redis' `
    -ArtifactPattern 'redis_dump.rdb' `
    -ArtifactLabel 'redis_dump.rdb'
@{{ Included = $result.Included; DriftCorrected = $result.DriftCorrected }} | ConvertTo-Json -Compress
"""
    )

    assert payload["Included"] is True
    assert payload["DriftCorrected"] is True
