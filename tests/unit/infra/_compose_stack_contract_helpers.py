"""Shared helpers for compose / BLUE-RED / stack-lifecycle contract tests (#3856, #3857)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_DIR = REPO_ROOT / "infrastructure" / "compose"

ComposeLayer = Literal["canonical_runtime", "legacy_ci", "legacy_overlay", "optional_overlay"]

COMPOSE_LAYER_FILES: dict[str, ComposeLayer] = {
    "compose.blue.yml": "canonical_runtime",
    "compose.red.yml": "canonical_runtime",
    "base.yml": "legacy_ci",
    "dev.yml": "legacy_overlay",
    "test.yml": "legacy_ci",
    "logging.yml": "optional_overlay",
    "prod.yml": "legacy_overlay",
}

CANONICAL_RUNTIME_FILES = (
    "compose.blue.yml",
    "compose.red.yml",
)

LEGACY_CI_FILES = (
    "base.yml",
    "dev.yml",
    "test.yml",
)

BLUE_CANONICAL_SERVICES: frozenset[str] = frozenset(
    {
        "cdb_postgres",
        "cdb_redis",
        "cdb_market",
        "cdb_candles",
        "cdb_regime",
        "cdb_allocation",
        "cdb_risk",
        "cdb_execution",
        "cdb_db_writer",
        "cdb_paper_runner",
    }
)

RED_CANONICAL_SERVICES: frozenset[str] = frozenset(
    {
        "cdb_ws",
        "cdb_signal",
        "cdb_prometheus",
        "cdb_grafana",
        "cdb_postgres_exporter",
        "cdb_redis_exporter",
        "cdb_cadvisor",
        "cdb_reports",
    }
)

KNOWN_CANONICAL_VOLUMES = frozenset({"kill_switch_state"})


def is_known_canonical_volume(name: str) -> bool:
    return name.endswith("_data") or name.startswith("cdb_") or name in KNOWN_CANONICAL_VOLUMES


CANONICAL_NETWORK = "cdb_network"
TEST_NETWORK = "cdb_test_network"

SECRET_ECHO_FORBIDDEN_LINE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Write-Host\s+\$value\b", re.IGNORECASE),
    re.compile(r"Write-Output\s+\$value\b", re.IGNORECASE),
    re.compile(
        r"Write-Host\s+.*\$env:(REDIS_PASSWORD|POSTGRES_PASSWORD|GRAFANA_PASSWORD)\b"
    ),
)

MUTATING_DOCKER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"docker\s+compose\s+.*\bup\b", re.IGNORECASE),
    re.compile(r"docker-compose\s+.*\bup\b", re.IGNORECASE),
    re.compile(r"docker\s+compose\s+.*\bdown\b", re.IGNORECASE),
    re.compile(r"docker-compose\s+.*\bdown\b", re.IGNORECASE),
    re.compile(r"docker\s+rm\b", re.IGNORECASE),
    re.compile(r"docker\s+stop\b", re.IGNORECASE),
    re.compile(r"docker\s+network\s+create\b", re.IGNORECASE),
    re.compile(r"docker\s+network\s+rm\b", re.IGNORECASE),
    re.compile(r"docker\s+volume\s+rm\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class LegacyTopologyFinding:
    script: str
    pattern: str
    detail: str


def load_compose_yaml(filename: str) -> dict[str, Any]:
    path = COMPOSE_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Compose file missing: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Compose file must parse to mapping: {filename}")
    return data


def service_names(compose: dict[str, Any]) -> list[str]:
    services = compose.get("services") or {}
    if not isinstance(services, dict):
        return []
    return sorted(name for name in services if name.startswith("cdb_"))


def services_missing_healthcheck(compose: dict[str, Any]) -> list[str]:
    services = compose.get("services") or {}
    missing: list[str] = []
    if not isinstance(services, dict):
        return missing
    for name, cfg in services.items():
        if not name.startswith("cdb_"):
            continue
        if not isinstance(cfg, dict):
            missing.append(name)
            continue
        if "healthcheck" not in cfg:
            missing.append(name)
    return sorted(missing)


def container_name_mismatches(compose: dict[str, Any]) -> list[str]:
    services = compose.get("services") or {}
    mismatches: list[str] = []
    if not isinstance(services, dict):
        return mismatches
    for name, cfg in services.items():
        if not name.startswith("cdb_"):
            continue
        if not isinstance(cfg, dict):
            continue
        container_name = cfg.get("container_name")
        if container_name and container_name != name:
            mismatches.append(f"{name} -> {container_name}")
    return sorted(mismatches)


def network_names(compose: dict[str, Any]) -> set[str]:
    networks = compose.get("networks") or {}
    if not isinstance(networks, dict):
        return set()
    return set(networks.keys())


def volume_names(compose: dict[str, Any]) -> set[str]:
    volumes = compose.get("volumes") or {}
    if not isinstance(volumes, dict):
        return set()
    return set(volumes.keys())


def read_script_text(relative_path: str) -> str:
    path = REPO_ROOT / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"Script missing: {relative_path}")
    return path.read_text(encoding="utf-8")


def find_legacy_compose_references(script_text: str, script_name: str) -> list[LegacyTopologyFinding]:
    findings: list[LegacyTopologyFinding] = []
    legacy_markers = (
        ("base.yml", "legacy single-compose base chain"),
        ("dev.yml", "legacy dev overlay"),
        ("docker-compose down", "unqualified legacy docker-compose"),
        ("docker-compose `", "legacy docker-compose hyphen invocation"),
    )
    for marker, detail in legacy_markers:
        if marker in script_text:
            findings.append(
                LegacyTopologyFinding(script=script_name, pattern=marker, detail=detail)
            )
    return findings


def script_has_operator_gate(script_text: str) -> bool:
    return "Read-Host" in script_text or re.search(r"\[switch\]\$Force", script_text) is not None


def script_mutating_paths_gated(script_text: str) -> bool:
    if not any(pattern.search(script_text) for pattern in MUTATING_DOCKER_PATTERNS):
        return True
    return script_has_operator_gate(script_text)


def script_secret_echo_violations(script_text: str) -> list[str]:
    violations: list[str] = []
    for line in script_text.splitlines():
        if ".Length" in line:
            continue
        for pattern in SECRET_ECHO_FORBIDDEN_LINE_PATTERNS:
            if pattern.search(line):
                violations.append(f"{pattern.pattern}: {line.strip()}")
    return violations
