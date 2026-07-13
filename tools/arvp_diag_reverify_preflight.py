"""ARVP diagnostic telemetry re-verify preflight (#3973).

Prepares host-env exports, build-freshness guard, and compose alignment
after #3971 regression fix — without starting runtime.
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
from tools.arvp_diag_telemetry_preflight import (
    format_bash_exports,
    format_powershell_exports,
    resolve_repo_source_sha,
)
from tools.arvp_parallel_lane_compose_contract import (
    CAMPAIGN_ID_HOST_ENV_DONCHIAN,
    CAMPAIGN_ID_HOST_ENV_PB1,
    build_parallel_compose_host_env,
    load_campaign_manifest,
    manifest_campaign_id,
)

REVERIFY_PB1_MANIFEST = "manifests/campaign_diag_reverify_pb1.yaml"
REVERIFY_DONCHIAN_MANIFEST = "manifests/campaign_diag_reverify_donchian.yaml"
REVERIFY_SIGNAL_COMPOSE_OVERRIDE = (
    "manifests/runtime_np_diag_reverify_signal_compose_override.yml"
)

EXPECTED_REVERIFY_SOURCE_SHA = "251faf59d94f50bd77972c06b3a7cf23d6ecf401"

EXPECTED_REVERIFY_BOT_IDS = {
    "cdb_signal_pb1": "np-pb1-reverify-01",
    "cdb_signal_donchian": "np-donchian-reverify-01",
}

EXPECTED_STRATEGY_IDS = {
    "cdb_signal_pb1": "primary_breakout_v1",
    "cdb_signal_donchian": "donchian_breakout_v1",
}

FORBIDDEN_3967_BOT_IDS = {"np-pb1-diag-01", "np-donchian-diag-01"}
FORBIDDEN_3967_CAMPAIGN_PREFIXES = (
    "arvp_diag_p15_pb1_20260710t1100z",
    "arvp_diag_p15_donchian_20260710t1100z",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_reverify_manifests(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    pb1 = load_campaign_manifest(root / REVERIFY_PB1_MANIFEST)
    donchian = load_campaign_manifest(root / REVERIFY_DONCHIAN_MANIFEST)
    return pb1, donchian


def load_reverify_compose_override(root: Path) -> dict[str, Any]:
    path = root / REVERIFY_SIGNAL_COMPOSE_OVERRIDE
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("re-verify signal compose override must be a YAML object")
    return raw


def validate_reverify_manifest_pair(
    pb1_manifest: dict[str, Any],
    donchian_manifest: dict[str, Any],
) -> dict[str, str]:
    pb1_id = manifest_campaign_id(pb1_manifest)
    donchian_id = manifest_campaign_id(donchian_manifest)
    if pb1_id == donchian_id:
        raise ValueError("re-verify lane campaign_id values must be distinct")
    for manifest in (pb1_manifest, donchian_manifest):
        bot_id = manifest.get("bot_id")
        if bot_id in FORBIDDEN_3967_BOT_IDS:
            raise ValueError(f"re-verify manifest must not reuse #3967 bot_id: {bot_id}")
        campaign_id = manifest.get("campaign_id")
        if campaign_id in FORBIDDEN_3967_CAMPAIGN_PREFIXES:
            raise ValueError(
                f"re-verify manifest must not reuse #3967 campaign_id: {campaign_id}"
            )
        expected_sha = manifest.get("expected_source_sha")
        if expected_sha != EXPECTED_REVERIFY_SOURCE_SHA:
            raise ValueError(
                f"expected_source_sha mismatch: {expected_sha!r} != "
                f"{EXPECTED_REVERIFY_SOURCE_SHA!r}"
            )
    return build_parallel_compose_host_env(pb1_manifest, donchian_manifest)


def validate_reverify_compose_alignment(
    host_env: dict[str, str],
    compose_override: dict[str, Any],
) -> None:
    services = compose_override.get("services")
    if not isinstance(services, dict):
        raise ValueError("compose override services must be a mapping")

    for service_name, expected_bot_id in EXPECTED_REVERIFY_BOT_IDS.items():
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

        cdb_source_sha = environment.get("CDB_SOURCE_SHA")
        if not isinstance(cdb_source_sha, str) or "CDB_SOURCE_SHA" not in cdb_source_sha:
            raise ValueError(f"{service_name} must declare CDB_SOURCE_SHA substitution")

        build = service.get("build")
        if not isinstance(build, dict):
            raise ValueError(f"{service_name} must declare build args for freshness")
        build_args = build.get("args")
        if not isinstance(build_args, dict) or "CDB_SOURCE_SHA" not in build_args:
            raise ValueError(f"{service_name} build.args must include CDB_SOURCE_SHA")


def build_runtime_freshness_guard(root: Path) -> dict[str, Any]:
    repo_sha = resolve_repo_source_sha(root)
    return {
        "expected_source_sha": EXPECTED_REVERIFY_SOURCE_SHA,
        "repo_head_sha": repo_sha,
        "repo_head_matches_expected": repo_sha == EXPECTED_REVERIFY_SOURCE_SHA,
        "container_build_marker_env": "CDB_SOURCE_SHA",
        "rebuild_required_before_execute": True,
        "rebuild_services": ["cdb_signal_pb1", "cdb_signal_donchian"],
        "execute_hold_if_unproven": (
            "If container CDB_SOURCE_SHA != expected_source_sha before observation, "
            "Execute must HOLD (FAIL_STALE_IMAGE_GUARD) — do not start supervisors."
        ),
        "verify_commands": [
            "docker compose ... build --no-cache cdb_signal_pb1 cdb_signal_donchian",
            "docker inspect cdb_signal_pb1 --format '{{range .Config.Env}}{{println .}}{{end}}' | findstr CDB_SOURCE_SHA",
            "docker inspect cdb_signal_donchian --format '{{range .Config.Env}}{{println .}}{{end}}' | findstr CDB_SOURCE_SHA",
            "curl -s http://127.0.0.1:8015/metrics | findstr correlation_ledger_insert_conflicts_total",
            "curl -s http://127.0.0.1:8016/metrics | findstr correlation_ledger_insert_conflicts_total",
        ],
        "limitation": (
            "This preflight slice does not run docker inspect or start containers."
        ),
    }


def build_reverify_preflight_report(root: Path | None = None) -> dict[str, Any]:
    base = root or repo_root()
    pb1_manifest, donchian_manifest = load_reverify_manifests(base)
    host_env = validate_reverify_manifest_pair(pb1_manifest, donchian_manifest)
    compose_override = load_reverify_compose_override(base)
    validate_reverify_compose_alignment(host_env, compose_override)

    host_env_with_sha = {
        **host_env,
        "CDB_SOURCE_SHA": EXPECTED_REVERIFY_SOURCE_SHA,
    }

    return {
        "status": "READY_PENDING_RUNTIME_GO",
        "parent_issue": 3973,
        "manifests": {
            "pb1": REVERIFY_PB1_MANIFEST,
            "donchian": REVERIFY_DONCHIAN_MANIFEST,
        },
        "compose_override": REVERIFY_SIGNAL_COMPOSE_OVERRIDE,
        "campaign_ids": {
            CAMPAIGN_ID_HOST_ENV_PB1: host_env[CAMPAIGN_ID_HOST_ENV_PB1],
            CAMPAIGN_ID_HOST_ENV_DONCHIAN: host_env[CAMPAIGN_ID_HOST_ENV_DONCHIAN],
        },
        "bot_ids": {
            "pb1": pb1_manifest["bot_id"],
            "donchian": donchian_manifest["bot_id"],
        },
        "host_env_exports": {
            "powershell": format_powershell_exports(host_env_with_sha),
            "bash": format_bash_exports(host_env_with_sha),
        },
        "runtime_freshness": build_runtime_freshness_guard(base),
        "runtime_not_started": True,
        "runtime_verified": False,
        "lr_status": "NO-GO",
        "proof_gaps_remaining": [
            "campaign_id_propagated_to_ledger",
            "lane_campaign_evidence",
            "#3971 fix runtime-verified",
        ],
    }


def runtime_go_phrase(tracking_issue: int = 3973) -> str:
    return (
        f"RUNTIME-GO #{tracking_issue}: start 2h ARVP telemetry re-verify run after "
        f"#3971 with rebuilt signal images, "
        f"expected_source_sha={EXPECTED_REVERIFY_SOURCE_SHA}, "
        f"PB1 + Donchian, CDB_CAMPAIGN_ID_PB1 and CDB_CAMPAIGN_ID_DONCHIAN set from "
        f"manifests, CDB_SOURCE_SHA verified in containers before observation, "
        f"MOCK_TRADING=true, DRY_RUN=true, MEXC_TESTNET=true, USE_REAL_BALANCE=false, "
        f"no Live/Echtgeld."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable preflight report on stdout",
    )
    args = parser.parse_args(argv)

    report = build_reverify_preflight_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    print("ARVP diagnostic telemetry re-verify preflight (#3973)")
    print(f"Status: {report['status']}")
    print()
    print("Host env (PowerShell — set before docker compose build/up):")
    print(report["host_env_exports"]["powershell"])
    print()
    print("Host env (bash):")
    print(report["host_env_exports"]["bash"])
    print()
    print("RUNTIME-GO phrase (post on #3973 when ready):")
    print(runtime_go_phrase())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"preflight failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
