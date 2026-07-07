"""Shared helpers for infra runbook drift regression tests (#3863)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNBOOKS_DIR = REPO_ROOT / "docs" / "runbooks"
COMPOSE_README = REPO_ROOT / "infrastructure" / "compose" / "README.md"
ALERTING_RUNBOOK = REPO_ROOT / "knowledge" / "operations" / "ALERTING_RUNBOOK.md"

INFRA_RUNBOOK_PATHS: tuple[Path, ...] = (
    RUNBOOKS_DIR / "BACKUP_AUTOMATION.md",
    RUNBOOKS_DIR / "cdb_secrets_ssot.md",
    RUNBOOKS_DIR / "local_ops_artifacts.md",
    COMPOSE_README,
    ALERTING_RUNBOOK,
)

# Repo-relative paths that infra runbooks should reference and that must exist on disk.
RUNBOOK_REQUIRED_REPO_PATHS: dict[str, tuple[str, ...]] = {
    "BACKUP_AUTOMATION.md": (
        "infrastructure/scripts/backup_all.ps1",
        "infrastructure/scripts/restore_all.ps1",
        "infrastructure/scripts/setup_backup_task.ps1",
        "infrastructure/scripts/backup_health_check.ps1",
    ),
    "cdb_secrets_ssot.md": (
        "scripts/secrets/sync_cdb_secrets.ps1",
    ),
    "local_ops_artifacts.md": (
        "tools/cdb.ps1",
    ),
    "README.md": (
        "infrastructure/compose/compose.blue.yml",
        "infrastructure/compose/compose.red.yml",
        "infrastructure/compose/base.yml",
        "infrastructure/compose/test.yml",
    ),
    "ALERTING_RUNBOOK.md": (
        "infrastructure/compose/compose.blue.yml",
        "infrastructure/compose/compose.red.yml",
        "infrastructure/monitoring/alertmanager.yml",
        "infrastructure/monitoring/prometheus.yml",
    ),
}

KNOWN_RUNBOOK_DRIFTS: dict[str, tuple[str, ...]] = {
    "local_ops_artifacts.md": (
        "Some ignore patterns still live in .git/info/exclude instead of root .gitignore.",
    ),
    "README.md": (
        "Compose README checklist items may lag contract-test coverage additions.",
    ),
}

LEGACY_RUNBOOK_MARKERS: tuple[tuple[str, str], ...] = (
    ("stack_up.ps1", "legacy stack_up entrypoint"),
    ("docker-compose.yml", "removed root compose file"),
    (".cdb_local/.secrets", "legacy secrets vault path in docs"),
)


@dataclass(frozen=True)
class InfraRunbookFinding:
    kind: str
    runbook: str
    detail: str


@dataclass(frozen=True)
class InfraRunbookDriftScan:
    runbooks_scanned: tuple[str, ...]
    missing_repo_paths: tuple[str, ...]
    legacy_markers: tuple[InfraRunbookFinding, ...]
    canonical_compose_mentions: int
    limitations: tuple[str, ...]
    findings: tuple[InfraRunbookFinding, ...] = field(default_factory=tuple)


def extract_backtick_paths(markdown_text: str) -> set[str]:
    refs: set[str] = set()
    for match in re.findall(r"`([^`]+)`", markdown_text):
        candidate = match.strip()
        if "/" in candidate or candidate.endswith((".yml", ".yaml", ".ps1", ".py", ".md")):
            refs.add(candidate.replace("\\", "/"))
    return refs


def scan_infra_runbook_drift() -> InfraRunbookDriftScan:
    runbooks_scanned: list[str] = []
    missing_paths: list[str] = []
    legacy_markers: list[InfraRunbookFinding] = []
    findings: list[InfraRunbookFinding] = []
    compose_mentions = 0

    for runbook_path in INFRA_RUNBOOK_PATHS:
        if not runbook_path.is_file():
            findings.append(
                InfraRunbookFinding(
                    kind="runbook_missing",
                    runbook=runbook_path.name,
                    detail=f"Expected runbook missing: {runbook_path}",
                )
            )
            continue
        runbooks_scanned.append(runbook_path.name)
        text = runbook_path.read_text(encoding="utf-8")
        compose_mentions += len(re.findall(r"compose\.blue\.yml|compose\.red\.yml", text))

        required = RUNBOOK_REQUIRED_REPO_PATHS.get(runbook_path.name, ())
        for relative in required:
            if not (REPO_ROOT / relative).is_file():
                missing_paths.append(relative)
                findings.append(
                    InfraRunbookFinding(
                        kind="runbook_repo_path_missing",
                        runbook=runbook_path.name,
                        detail=f"Runbook references missing repo path: {relative}",
                    )
                )

        for marker, detail in LEGACY_RUNBOOK_MARKERS:
            if marker in text:
                legacy_markers.append(
                    InfraRunbookFinding(
                        kind="legacy_runbook_marker",
                        runbook=runbook_path.name,
                        detail=f"{detail} ({marker})",
                    )
                )

        for drift_note in KNOWN_RUNBOOK_DRIFTS.get(runbook_path.name, ()):
            findings.append(
                InfraRunbookFinding(
                    kind="known_runbook_drift",
                    runbook=runbook_path.name,
                    detail=drift_note,
                )
            )

    limitations = (
        "Fixture-based static scan only; runbooks are not auto-corrected.",
        "Known drifts are explicit findings with limitations documented.",
        "Does not prove operator runbook accuracy at execution time.",
    )

    return InfraRunbookDriftScan(
        runbooks_scanned=tuple(runbooks_scanned),
        missing_repo_paths=tuple(sorted(set(missing_paths))),
        legacy_markers=tuple(legacy_markers),
        canonical_compose_mentions=compose_mentions,
        limitations=limitations,
        findings=tuple(findings),
    )
