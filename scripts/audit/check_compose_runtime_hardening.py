#!/usr/bin/env python3
"""
CDB-SEC-007 - Compose Runtime Hardening Guard

Static, deterministic checks for BLUE/RED compose defaults:
- App services must be hardened (no-new-privileges, cap_drop ALL, read_only true)
- privileged containers forbidden
- docker socket mount forbidden
- host-level mounts forbidden in default runtime (allowed only behind an explicit trusted profile)
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BLUE = REPO_ROOT / "infrastructure/compose/compose.blue.yml"
DEFAULT_RED = REPO_ROOT / "infrastructure/compose/compose.red.yml"


APP_SERVICES_BLUE: Set[str] = {
    "cdb_market",
    "cdb_candles",
    "cdb_regime",
    "cdb_allocation",
    "cdb_risk",
    "cdb_execution",
    "cdb_db_writer",
    "cdb_paper_runner",
}

APP_SERVICES_RED: Set[str] = {
    "cdb_ws",
    "cdb_signal",
    "cdb_reports",
}

# Services that are allowed to be less strict than app services.
NON_APP_SERVICES: Set[str] = {
    # BLUE
    "cdb_postgres",
    "cdb_redis",
    # RED monitoring
    "cdb_prometheus",
    "cdb_grafana",
    "cdb_postgres_exporter",
    "cdb_redis_exporter",
    # Trusted-only host observability
    "cdb_cadvisor",
}

TRUSTED_PROFILES: Set[str] = {"trusted-host-observability"}


@dataclass(frozen=True)
class Finding:
    path: Path
    service: str
    message: str

    def format(self) -> str:
        rel = self.path.as_posix()
        return f"{rel}::{self.service}: {self.message}"


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"ERROR: missing file: {path}")
    try:
        data = yaml.safe_load(content) or {}
    except Exception as e:  # pragma: no cover
        raise SystemExit(f"ERROR: failed to parse YAML {path}: {e}")
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: expected YAML mapping at root: {path}")
    return data


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _has_no_new_privileges(service_cfg: Dict[str, Any]) -> bool:
    sec = service_cfg.get("security_opt")
    for item in _as_list(sec):
        if isinstance(item, str) and item.strip() == "no-new-privileges:true":
            return True
    return False


def _has_cap_drop_all(service_cfg: Dict[str, Any]) -> bool:
    cap = service_cfg.get("cap_drop")
    for item in _as_list(cap):
        if isinstance(item, str) and item.strip() == "ALL":
            return True
    return False


def _is_read_only_true(service_cfg: Dict[str, Any]) -> bool:
    ro = service_cfg.get("read_only")
    return ro is True


def _profiles(service_cfg: Dict[str, Any]) -> Set[str]:
    raw = service_cfg.get("profiles")
    profs: Set[str] = set()
    for item in _as_list(raw):
        if isinstance(item, str):
            profs.add(item.strip())
    return profs


def _iter_volume_strings(service_cfg: Dict[str, Any]) -> Iterable[str]:
    vols = service_cfg.get("volumes")
    for item in _as_list(vols):
        # docker compose supports long syntax dicts; we only care about common short string form here.
        if isinstance(item, str):
            yield item.strip()


def _has_forbidden_mounts(service_cfg: Dict[str, Any]) -> List[str]:
    """
    Return a list of forbidden mount indicators found.
    These are only forbidden in the default runtime (no trusted profile).
    """
    hits: List[str] = []
    for v in _iter_volume_strings(service_cfg):
        # Docker socket
        if "/var/run/docker.sock" in v:
            hits.append("/var/run/docker.sock")
        # Host root mounts (incl. cAdvisor patterns like "/:/rootfs:ro")
        if v.startswith("/:"):
            hits.append("host_root_mount(/:...)")
        # Other common host-level mounts used for host introspection
        if v.startswith("/sys:"):
            hits.append("host_mount(/sys)")
        if v.startswith("/var/run:"):
            hits.append("host_mount(/var/run)")
        if v.startswith("/var/lib/docker"):
            hits.append("host_mount(/var/lib/docker)")
    return sorted(set(hits))


def _check_compose_file(
    path: Path,
    app_services_expected: Set[str],
) -> List[Finding]:
    data = _load_yaml(path)
    services = data.get("services") or {}
    if not isinstance(services, dict):
        return [Finding(path=path, service="<root>", message="Invalid compose: services must be a mapping")]

    findings: List[Finding] = []

    for svc in sorted(app_services_expected):
        if svc not in services:
            findings.append(Finding(path=path, service=svc, message="Missing expected service"))
            continue
        cfg = services.get(svc) or {}
        if not isinstance(cfg, dict):
            findings.append(Finding(path=path, service=svc, message="Invalid service config (expected mapping)"))
            continue

        if cfg.get("privileged") is True:
            findings.append(Finding(path=path, service=svc, message="privileged: true is forbidden"))

        if not _has_no_new_privileges(cfg):
            findings.append(Finding(path=path, service=svc, message="Missing security_opt: no-new-privileges:true"))
        if not _has_cap_drop_all(cfg):
            findings.append(Finding(path=path, service=svc, message="Missing cap_drop: [ALL]"))
        if not _is_read_only_true(cfg):
            findings.append(Finding(path=path, service=svc, message="Missing read_only: true (allowlist required if intentional)"))

        profs = _profiles(cfg)
        if not (profs & TRUSTED_PROFILES):
            mounts = _has_forbidden_mounts(cfg)
            for m in mounts:
                findings.append(Finding(path=path, service=svc, message=f"Forbidden mount in default runtime: {m}"))

    # Broad scan: forbid privileged anywhere (not just app services)
    for svc, cfg in services.items():
        if not isinstance(cfg, dict):
            continue
        if cfg.get("privileged") is True:
            findings.append(Finding(path=path, service=str(svc), message="privileged: true is forbidden"))

        profs = _profiles(cfg)
        mounts = _has_forbidden_mounts(cfg)
        if mounts and not (profs & TRUSTED_PROFILES):
            # Limit to the explicit forbidden kinds for default runtime.
            # This is mainly to catch docker sock / host root mounts if someone reintroduces them.
            for m in mounts:
                findings.append(Finding(path=path, service=str(svc), message=f"Forbidden mount in default runtime: {m}"))

    return findings


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="CDB-SEC-007 guard: enforce compose runtime hardening defaults")
    p.add_argument("--blue", type=Path, default=DEFAULT_BLUE, help="Path to compose.blue.yml")
    p.add_argument("--red", type=Path, default=DEFAULT_RED, help="Path to compose.red.yml")
    args = p.parse_args(argv)

    findings: List[Finding] = []
    findings.extend(_check_compose_file(args.blue, APP_SERVICES_BLUE))
    findings.extend(_check_compose_file(args.red, APP_SERVICES_RED))

    if findings:
        print("FAIL: compose runtime hardening guard triggered")
        for f in findings:
            print(f"- {f.format()}")
        return 1

    print("OK: compose runtime hardening guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

