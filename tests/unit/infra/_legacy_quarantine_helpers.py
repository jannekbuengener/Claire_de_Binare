"""Shared helpers for legacy script quarantine contract tests (#3862)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LEGACY_SCRIPTS_DIR = REPO_ROOT / "infrastructure" / "scripts" / "legacy"

LEGACY_BANNER_PATTERN = re.compile(r"^\s*#\s*LEGACY\b", re.IGNORECASE | re.MULTILINE)

OLD_COMPOSE_MARKERS: tuple[tuple[str, str], ...] = (
    ("base.yml", "legacy single-compose base chain"),
    ("dev.yml", "legacy dev overlay"),
    ("docker-compose.base.yml", "removed root compose fragment"),
)

OLD_SECRETS_MARKERS: tuple[tuple[str, str], ...] = (
    (".cdb_local/.secrets", "legacy local vault path"),
    (".cdb_local\\.secrets", "legacy local vault path (escaped)"),
    (".secrets/", "repo-root secrets directory"),
    (".env.compose", "legacy compose env bundle"),
)

OLD_CONTAINER_MARKERS: tuple[tuple[str, str], ...] = (
    ("cdb_core", "pre-BLUE/RED core container name"),
    ("claire_de_binare_cdb_network", "legacy docker network naming"),
)

CANONICAL_RUNTIME_HINTS: tuple[str, ...] = (
    "compose.blue.yml",
    "compose.red.yml",
    "tools/cdb.ps1",
    "setup_blue_red.ps1",
    "SECRETS_PATH",
    "Documents/.secrets/.cdb",
)


@dataclass(frozen=True)
class LegacyMarkerFinding:
    script: str
    marker: str
    category: str
    detail: str


@dataclass(frozen=True)
class LegacyQuarantineScan:
    legacy_scripts: tuple[str, ...]
    scripts_missing_banner: tuple[str, ...]
    compose_markers: tuple[LegacyMarkerFinding, ...]
    secrets_markers: tuple[LegacyMarkerFinding, ...]
    container_markers: tuple[LegacyMarkerFinding, ...]
    canonical_hints_in_legacy: tuple[str, ...]
    limitations: tuple[str, ...]
    findings: tuple[LegacyMarkerFinding, ...] = field(default_factory=tuple)


def list_legacy_scripts() -> list[str]:
    if not LEGACY_SCRIPTS_DIR.is_dir():
        return []
    return sorted(path.name for path in LEGACY_SCRIPTS_DIR.iterdir() if path.is_file())


def script_has_legacy_banner(text: str) -> bool:
    return LEGACY_BANNER_PATTERN.search(text) is not None


def scan_legacy_markers(text: str, script_name: str) -> list[LegacyMarkerFinding]:
    findings: list[LegacyMarkerFinding] = []
    for marker, detail in OLD_COMPOSE_MARKERS:
        if marker in text:
            findings.append(
                LegacyMarkerFinding(
                    script=script_name,
                    marker=marker,
                    category="old_compose_path",
                    detail=detail,
                )
            )
    for marker, detail in OLD_SECRETS_MARKERS:
        if marker in text:
            findings.append(
                LegacyMarkerFinding(
                    script=script_name,
                    marker=marker,
                    category="old_secrets_path",
                    detail=detail,
                )
            )
    for marker, detail in OLD_CONTAINER_MARKERS:
        if marker in text:
            findings.append(
                LegacyMarkerFinding(
                    script=script_name,
                    marker=marker,
                    category="old_container_name",
                    detail=detail,
                )
            )
    return findings


def scan_legacy_quarantine() -> LegacyQuarantineScan:
    scripts = list_legacy_scripts()
    missing_banner: list[str] = []
    compose_markers: list[LegacyMarkerFinding] = []
    secrets_markers: list[LegacyMarkerFinding] = []
    container_markers: list[LegacyMarkerFinding] = []
    canonical_hints: list[str] = []

    for script_name in scripts:
        text = (LEGACY_SCRIPTS_DIR / script_name).read_text(encoding="utf-8")
        if not script_has_legacy_banner(text):
            missing_banner.append(script_name)
        for finding in scan_legacy_markers(text, script_name):
            if finding.category == "old_compose_path":
                compose_markers.append(finding)
            elif finding.category == "old_secrets_path":
                secrets_markers.append(finding)
            else:
                container_markers.append(finding)
        for hint in CANONICAL_RUNTIME_HINTS:
            if hint in text:
                canonical_hints.append(f"{script_name}:{hint}")

    all_findings = tuple(compose_markers + secrets_markers + container_markers)
    limitations = (
        "Legacy scripts are quarantined reference-only; tests do not execute them.",
        "Marker findings in legacy scripts are expected and document drift signals.",
        "No legacy reactivation or topology repair in this slice.",
    )

    return LegacyQuarantineScan(
        legacy_scripts=tuple(scripts),
        scripts_missing_banner=tuple(missing_banner),
        compose_markers=tuple(compose_markers),
        secrets_markers=tuple(secrets_markers),
        container_markers=tuple(container_markers),
        canonical_hints_in_legacy=tuple(sorted(set(canonical_hints))),
        limitations=limitations,
        findings=all_findings,
    )
