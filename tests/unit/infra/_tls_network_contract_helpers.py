"""Shared helpers for TLS / network overlay contract tests (#3860)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from tests.unit.infra._compose_stack_contract_helpers import (
    CANONICAL_RUNTIME_FILES,
    COMPOSE_DIR,
    REPO_ROOT,
)

TLS_DIR = REPO_ROOT / "infrastructure" / "tls"
SCRIPTS_DIR = REPO_ROOT / "infrastructure" / "scripts"

TLS_OVERLAY_FILE = "tls.yml"
NETWORK_PROD_OVERLAY_FILE = "network-prod.yml"

CERT_UTILITY_SCRIPTS: tuple[str, ...] = (
    "infrastructure/tls/generate_certs.sh",
    "infrastructure/tls/postgres_ssl_init.sh",
)

NETWORK_SETUP_SCRIPT = "infrastructure/scripts/setup-network.sh"

CANONICAL_LOCALHOST_BIND = "127.0.0.1"

# Sidecar / lab overlays where public bind may be an explicit finding, not canon.
KNOWN_PUBLIC_EXPOSURE_FILES: frozenset[str] = frozenset(
    {
        "surrealdb.yml",
        "surrealdb-audit-trail-t3.yml",
        "memory.yml",
    }
)

SERVICE_NAME_PATTERN = re.compile(r"\bcdb_[a-z0-9_]+\b")

PortBindingKind = Literal["localhost", "public", "unqualified", "none"]


@dataclass(frozen=True)
class PortBindingFinding:
    compose_file: str
    service: str
    binding: str
    kind: PortBindingKind


@dataclass(frozen=True)
class CertUtilityClassification:
    relative_path: str
    is_cert_utility: bool
    has_legacy_banner: bool
    mutates_filesystem: bool
    detail: str


@dataclass(frozen=True)
class TlsNetworkScan:
    tls_overlay_services: tuple[str, ...]
    tls_cert_mount_paths: tuple[str, ...]
    network_prod_internal: bool | None
    network_prod_ports_nulled: tuple[str, ...]
    canonical_localhost_bindings: tuple[PortBindingFinding, ...]
    public_exposure_findings: tuple[PortBindingFinding, ...]
    cert_utilities: tuple[CertUtilityClassification, ...]
    service_name_references: tuple[str, ...]
    limitations: tuple[str, ...] = field(default_factory=tuple)


def load_overlay_yaml(filename: str) -> dict[str, Any]:
    path = COMPOSE_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Overlay missing: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Overlay must parse to mapping: {filename}")
    return data


def classify_port_binding(binding: str) -> PortBindingKind:
    text = str(binding).strip().strip("'\"")
    if not text:
        return "none"
    if text.startswith("0.0.0.0:") or text.startswith("0.0.0.0/"):
        return "public"
    if text.startswith(f"{CANONICAL_LOCALHOST_BIND}:"):
        return "localhost"
    host_part = text.split(":", 1)[0]
    if host_part.isdigit():
        return "unqualified"
    if ":" not in text:
        return "unqualified"
    return "public"


def extract_port_bindings(compose: dict[str, Any], filename: str) -> list[PortBindingFinding]:
    services = compose.get("services") or {}
    findings: list[PortBindingFinding] = []
    if not isinstance(services, dict):
        return findings
    for service, cfg in services.items():
        if not isinstance(cfg, dict):
            continue
        ports = cfg.get("ports")
        if ports is None:
            continue
        if not isinstance(ports, list):
            continue
        for binding in ports:
            if binding is None:
                continue
            binding_text = str(binding)
            findings.append(
                PortBindingFinding(
                    compose_file=filename,
                    service=service,
                    binding=binding_text,
                    kind=classify_port_binding(binding_text),
                )
            )
    return findings


def scan_compose_port_bindings(filenames: tuple[str, ...]) -> list[PortBindingFinding]:
    collected: list[PortBindingFinding] = []
    for filename in filenames:
        compose = load_overlay_yaml(filename)
        collected.extend(extract_port_bindings(compose, filename))
    return collected


def classify_cert_utility_script(relative_path: str) -> CertUtilityClassification:
    path = REPO_ROOT / relative_path
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()
    mutates = any(
        marker in lowered
        for marker in ("openssl", "mkdir -p", "chmod", "keytool", "certutil")
    )
    is_cert = "cert" in lowered or "tls" in lowered or "ssl" in lowered
    has_banner = "certificate" in lowered or "tls" in lowered[:500]
    return CertUtilityClassification(
        relative_path=relative_path,
        is_cert_utility=is_cert and mutates,
        has_legacy_banner=False,
        mutates_filesystem=mutates,
        detail="read-only utility classification; tests do not execute script",
    )


def extract_tls_cert_mount_paths(tls_overlay: dict[str, Any]) -> list[str]:
    mounts: list[str] = []
    services = tls_overlay.get("services") or {}
    if not isinstance(services, dict):
        return mounts
    for cfg in services.values():
        if not isinstance(cfg, dict):
            continue
        volumes = cfg.get("volumes") or []
        if not isinstance(volumes, list):
            continue
        for volume in volumes:
            text = str(volume)
            if "/tls" in text or "tls/" in text or ".crt" in text or ".key" in text:
                mounts.append(text)
    return sorted(set(mounts))


def extract_service_names_from_text(*texts: str) -> tuple[str, ...]:
    names: set[str] = set()
    for text in texts:
        names.update(SERVICE_NAME_PATTERN.findall(text))
    return tuple(sorted(names))


def scan_tls_network_contract() -> TlsNetworkScan:
    tls_overlay = load_overlay_yaml(TLS_OVERLAY_FILE)
    network_overlay = load_overlay_yaml(NETWORK_PROD_OVERLAY_FILE)

    tls_services = tuple(
        sorted(name for name in (tls_overlay.get("services") or {}) if name.startswith("cdb_"))
    )
    cert_mounts = tuple(extract_tls_cert_mount_paths(tls_overlay))

    networks = network_overlay.get("networks") or {}
    cdb_network = networks.get("cdb_network") if isinstance(networks, dict) else None
    internal_flag = (
        bool(cdb_network.get("internal"))
        if isinstance(cdb_network, dict)
        else None
    )

    nulled_ports: list[str] = []
    services = network_overlay.get("services") or {}
    if isinstance(services, dict):
        for name, cfg in services.items():
            if isinstance(cfg, dict) and cfg.get("ports") is None:
                nulled_ports.append(name)

    all_bindings = scan_compose_port_bindings(tuple(CANONICAL_RUNTIME_FILES))
    canonical_localhost = tuple(
        b for b in all_bindings if b.kind == "localhost"
    )
    public_findings = tuple(
        b
        for b in scan_compose_port_bindings(
            tuple(sorted(path.name for path in COMPOSE_DIR.glob("*.yml")))
        )
        if b.kind in {"public", "unqualified"}
    )

    cert_utils = tuple(classify_cert_utility_script(path) for path in CERT_UTILITY_SCRIPTS)

    prometheus_text = (
        REPO_ROOT / "infrastructure" / "monitoring" / "prometheus.yml"
    ).read_text(encoding="utf-8")
    network_text = (COMPOSE_DIR / NETWORK_PROD_OVERLAY_FILE).read_text(encoding="utf-8")
    service_refs = extract_service_names_from_text(
        yaml.safe_dump(tls_overlay),
        network_text,
        prometheus_text,
    )

    limitations = (
        "Port scans are static YAML only; no Docker network or TLS runtime proof.",
        "Public exposure findings include known sidecar overlays; not auto-fixed.",
        "Cert utility scripts are classified read-only; tests never generate certificates.",
        "setup-network.sh is present but not executed (network creation forbidden).",
    )

    return TlsNetworkScan(
        tls_overlay_services=tls_services,
        tls_cert_mount_paths=cert_mounts,
        network_prod_internal=internal_flag,
        network_prod_ports_nulled=tuple(sorted(nulled_ports)),
        canonical_localhost_bindings=canonical_localhost,
        public_exposure_findings=public_findings,
        cert_utilities=cert_utils,
        service_name_references=service_refs,
        limitations=limitations,
    )


def network_setup_script_is_mutating() -> bool:
    path = REPO_ROOT / NETWORK_SETUP_SCRIPT
    text = path.read_text(encoding="utf-8")
    return "docker network create" in text
