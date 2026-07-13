"""ARVP diagnostic telemetry verification preflight (#3965).

Prepares host-env export instructions and validates manifest ↔ compose alignment
without starting runtime.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from core.replay.correlation_ledger_attribution import CDB_CAMPAIGN_ID_ENV
from tools.arvp_parallel_lane_compose_contract import (
    CAMPAIGN_ID_HOST_ENV_DONCHIAN,
    CAMPAIGN_ID_HOST_ENV_PB1,
    build_parallel_compose_host_env,
    load_campaign_manifest,
    manifest_campaign_id,
)

DIAG_PB1_MANIFEST = "manifests/campaign_diag_telemetry_pb1.yaml"
DIAG_DONCHIAN_MANIFEST = "manifests/campaign_diag_telemetry_donchian.yaml"
DIAG_SIGNAL_COMPOSE_OVERRIDE = (
    "manifests/runtime_np_diag_telemetry_signal_compose_override.yml"
)

EXPECTED_DIAG_BOT_IDS = {
    "cdb_signal_pb1": "np-pb1-diag-01",
    "cdb_signal_donchian": "np-donchian-diag-01",
}

EXPECTED_STRATEGY_IDS = {
    "cdb_signal_pb1": "primary_breakout_v1",
    "cdb_signal_donchian": "donchian_breakout_v1",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_diag_manifests(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    pb1 = load_campaign_manifest(root / DIAG_PB1_MANIFEST)
    donchian = load_campaign_manifest(root / DIAG_DONCHIAN_MANIFEST)
    return pb1, donchian


def load_diag_compose_override(root: Path) -> dict[str, Any]:
    path = root / DIAG_SIGNAL_COMPOSE_OVERRIDE
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("diagnostic signal compose override must be a YAML object")
    return raw


def validate_diag_manifest_pair(
    pb1_manifest: dict[str, Any],
    donchian_manifest: dict[str, Any],
) -> dict[str, str]:
    pb1_id = manifest_campaign_id(pb1_manifest)
    donchian_id = manifest_campaign_id(donchian_manifest)
    if pb1_id == donchian_id:
        raise ValueError("diagnostic lane campaign_id values must be distinct")
    if pb1_manifest.get("bot_id") == "np-pb1-parallel-01":
        raise ValueError("diagnostic PB1 manifest must not reuse #3912 bot_id")
    if donchian_manifest.get("bot_id") == "np-donchian-parallel-01":
        raise ValueError("diagnostic Donchian manifest must not reuse #3912 bot_id")
    return build_parallel_compose_host_env(pb1_manifest, donchian_manifest)


def validate_diag_compose_alignment(
    host_env: dict[str, str],
    compose_override: dict[str, Any],
) -> None:
    services = compose_override.get("services")
    if not isinstance(services, dict):
        raise ValueError("compose override services must be a mapping")

    for service_name, expected_bot_id in EXPECTED_DIAG_BOT_IDS.items():
        service = services.get(service_name)
        if not isinstance(service, dict):
            raise ValueError(f"missing compose service: {service_name}")
        environment = service.get("environment")
        if not isinstance(environment, dict):
            raise ValueError(f"{service_name} environment must be a mapping")

        expected_strategy = EXPECTED_STRATEGY_IDS[service_name]
        if environment.get("SIGNAL_STRATEGY_ID") != expected_strategy:
            raise ValueError(
                f"{service_name} SIGNAL_STRATEGY_ID mismatch: "
                f"{environment.get('SIGNAL_STRATEGY_ID')!r} != {expected_strategy!r}"
            )
        if environment.get("SIGNAL_BOT_ID") != expected_bot_id:
            raise ValueError(
                f"{service_name} SIGNAL_BOT_ID mismatch: "
                f"{environment.get('SIGNAL_BOT_ID')!r} != {expected_bot_id!r}"
            )

        host_key = (
            CAMPAIGN_ID_HOST_ENV_PB1
            if service_name == "cdb_signal_pb1"
            else CAMPAIGN_ID_HOST_ENV_DONCHIAN
        )
        expected_campaign = host_env[host_key]
        substitution = f"${{{host_key}:-}}"
        if environment.get(CDB_CAMPAIGN_ID_ENV) != substitution:
            raise ValueError(
                f"{service_name} {CDB_CAMPAIGN_ID_ENV} must use {substitution!r}"
            )
        if not expected_campaign:
            raise ValueError(f"host env {host_key} must be non-empty")


def resolve_repo_source_sha(root: Path) -> str | None:
    """Return current git HEAD for runtime image freshness checks."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        sha = proc.stdout.strip()
        return sha or None
    except (OSError, subprocess.SubprocessError):
        return None


def build_runtime_freshness_guard(root: Path) -> dict[str, Any]:
    sha = resolve_repo_source_sha(root)
    return {
        "expected_source_sha": sha,
        "container_build_marker_env": "CDB_SOURCE_SHA",
        "rebuild_required_after_telemetry_fix": True,
        "limitation": (
            "Preflight cannot verify running container image SHA without docker inspect; "
            "operator must rebuild signal services after P0 telemetry merges."
        ),
    }


def format_powershell_exports(host_env: dict[str, str]) -> str:
    lines = [
        f'$env:{key} = "{value}"'
        for key, value in sorted(host_env.items())
    ]
    return "\n".join(lines)


def format_bash_exports(host_env: dict[str, str]) -> str:
    lines = [f'export {key}="{value}"' for key, value in sorted(host_env.items())]
    return "\n".join(lines)


def build_preflight_report(root: Path | None = None) -> dict[str, Any]:
    base = root or repo_root()
    pb1_manifest, donchian_manifest = load_diag_manifests(base)
    host_env = validate_diag_manifest_pair(pb1_manifest, donchian_manifest)
    compose_override = load_diag_compose_override(base)
    validate_diag_compose_alignment(host_env, compose_override)

    return {
        "status": "READY_PENDING_RUNTIME_GO",
        "parent_issue": 3965,
        "manifests": {
            "pb1": DIAG_PB1_MANIFEST,
            "donchian": DIAG_DONCHIAN_MANIFEST,
        },
        "compose_override": DIAG_SIGNAL_COMPOSE_OVERRIDE,
        "campaign_ids": {
            CAMPAIGN_ID_HOST_ENV_PB1: host_env[CAMPAIGN_ID_HOST_ENV_PB1],
            CAMPAIGN_ID_HOST_ENV_DONCHIAN: host_env[CAMPAIGN_ID_HOST_ENV_DONCHIAN],
        },
        "bot_ids": {
            "pb1": pb1_manifest["bot_id"],
            "donchian": donchian_manifest["bot_id"],
        },
        "host_env_exports": {
            "powershell": format_powershell_exports(host_env),
            "bash": format_bash_exports(host_env),
        },
        "runtime_freshness": build_runtime_freshness_guard(base),
        "runtime_not_started": True,
        "lr_status": "NO-GO",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable preflight report on stdout",
    )
    args = parser.parse_args(argv)

    report = build_preflight_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    print("ARVP diagnostic telemetry preflight (#3965)")
    print(f"Status: {report['status']}")
    print()
    print("Host env (PowerShell — set before docker compose up):")
    print(report["host_env_exports"]["powershell"])
    print()
    print("Host env (bash):")
    print(report["host_env_exports"]["bash"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"preflight failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
