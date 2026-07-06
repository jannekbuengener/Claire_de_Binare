"""Shared helpers for secrets SSOT and backup/restore/DR contract tests (#3858, #3859)."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

CANONICAL_SECRETS_DIR_MARKERS: tuple[str, ...] = (
    r"Documents\.secrets\.cdb",
    r"Documents/\.secrets/\.cdb",
)

LEGACY_SECRETS_QUARANTINE_MARKERS: tuple[str, ...] = (
    r"\.cdb_local[\\/]\.secrets",
    r"\.cdb_local\.secrets",
)

ACTIVE_SECRETS_SCRIPTS: dict[str, str] = {
    "init_secrets": "infrastructure/scripts/init-secrets.ps1",
    "manage_secrets": "infrastructure/scripts/manage_secrets.ps1",
    "rotate_secrets": "tools/secrets/Rotate-Secrets.ps1",
    "setup_blue_red": "infrastructure/scripts/setup_blue_red.ps1",
}

BACKUP_RESTORE_DR_SCRIPTS: dict[str, str] = {
    "backup_all": "infrastructure/scripts/backup_all.ps1",
    "restore_all": "infrastructure/scripts/restore_all.ps1",
    "backup_manifest_helpers": "infrastructure/scripts/backup_manifest_helpers.ps1",
    "backup_health_check": "infrastructure/scripts/backup_health_check.ps1",
    "dr_backup": "infrastructure/scripts/dr_backup.ps1",
    "dr_restore": "infrastructure/scripts/dr_restore.ps1",
}

CANONICAL_COMPOSE_RUNTIME = (
    "infrastructure/compose/compose.blue.yml",
    "infrastructure/compose/compose.red.yml",
)

BACKUP_COMPONENT_ARTIFACTS: dict[str, str] = {
    "Postgres": "postgres_dump.sql",
    "Redis": "redis_dump.rdb",
    "SurrealDB": "surrealdb_data",
}

SECRET_ECHO_FORBIDDEN_LINE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Write-Host\s+\$content\b", re.IGNORECASE),
    re.compile(r"Write-Host\s+\$password\b", re.IGNORECASE),
    re.compile(r"Write-Host\s+\$pass\b", re.IGNORECASE),
    re.compile(r"Write-Output\s+\$content\b", re.IGNORECASE),
    re.compile(r"Write-Host\s+\$value\b", re.IGNORECASE),
    re.compile(
        r"Write-Host\s+.*\$env:(REDIS_PASSWORD|POSTGRES_PASSWORD|GRAFANA_PASSWORD)\b"
    ),
)


def read_repo_text(relative_path: str) -> str:
    path = REPO_ROOT / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"Missing repo file: {relative_path}")
    return path.read_text(encoding="utf-8")


def script_uses_canonical_secrets_path(script_text: str) -> bool:
    if "SECRETS_PATH" in script_text:
        return True
    return any(re.search(marker, script_text) for marker in CANONICAL_SECRETS_DIR_MARKERS)


def script_promotes_legacy_secrets_path(script_text: str) -> bool:
    return any(re.search(marker, script_text) for marker in LEGACY_SECRETS_QUARANTINE_MARKERS)


def script_secret_echo_violations(script_text: str) -> list[str]:
    violations: list[str] = []
    for line in script_text.splitlines():
        if ".Length" in line or "chars)" in line:
            continue
        for pattern in SECRET_ECHO_FORBIDDEN_LINE_PATTERNS:
            if pattern.search(line):
                violations.append(f"{pattern.pattern}: {line.strip()}")
    return violations


def script_has_operator_gate(script_text: str) -> bool:
    return "Read-Host" in script_text or re.search(r"\[switch\]\$Force", script_text) is not None


def compose_requires_secrets_path(compose_text: str) -> bool:
    return "SECRETS_PATH:?SECRETS_PATH must be set" in compose_text
