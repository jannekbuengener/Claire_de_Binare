"""Parallel lane manifest ↔ compose campaign ID contract (ARVP P1.5)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from core.replay.correlation_ledger_attribution import CDB_CAMPAIGN_ID_ENV

PARALLEL_SIGNAL_COMPOSE_OVERRIDE = (
    "manifests/runtime_np_parallel_signal_compose_override.yml"
)

# Host-level substitution keys set at RUNTIME-GO from rewritten campaign manifests.
CAMPAIGN_ID_HOST_ENV_PB1 = "CDB_CAMPAIGN_ID_PB1"
CAMPAIGN_ID_HOST_ENV_DONCHIAN = "CDB_CAMPAIGN_ID_DONCHIAN"

PB1_MANIFEST_PATH = "manifests/campaign_3912_np_parallel_pb1.yaml"
DONCHIAN_MANIFEST_PATH = "manifests/campaign_3912_np_parallel_donchian.yaml"

CAMPAIGN_ID_TEMPLATE_SUFFIX = "_TEMPLATE"
RUNTIME_GO_PLACEHOLDER = "RUNTIME_GO_SET"


@dataclass(frozen=True)
class ParallelSignalLane:
    service_name: str
    strategy_id: str
    bot_id: str
    campaign_id_host_env: str
    manifest_path: str


PARALLEL_SIGNAL_LANES: tuple[ParallelSignalLane, ...] = (
    ParallelSignalLane(
        service_name="cdb_signal_pb1",
        strategy_id="primary_breakout_v1",
        bot_id="np-pb1-parallel-01",
        campaign_id_host_env=CAMPAIGN_ID_HOST_ENV_PB1,
        manifest_path=PB1_MANIFEST_PATH,
    ),
    ParallelSignalLane(
        service_name="cdb_signal_donchian",
        strategy_id="donchian_breakout_v1",
        bot_id="np-donchian-parallel-01",
        campaign_id_host_env=CAMPAIGN_ID_HOST_ENV_DONCHIAN,
        manifest_path=DONCHIAN_MANIFEST_PATH,
    ),
)

LANE_BY_SERVICE: dict[str, ParallelSignalLane] = {
    lane.service_name: lane for lane in PARALLEL_SIGNAL_LANES
}


def lane_for_service(service_name: str) -> ParallelSignalLane:
    try:
        return LANE_BY_SERVICE[service_name]
    except KeyError as exc:
        raise ValueError(f"unknown parallel signal service: {service_name}") from exc


def load_campaign_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"manifest must be a YAML object: {manifest_path}")
    return raw


def manifest_campaign_id(manifest: Mapping[str, Any]) -> str:
    raw = manifest.get("campaign_id")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("manifest campaign_id must be a non-empty string")
    return raw.strip()


def is_runtime_ready_campaign_id(campaign_id: str) -> bool:
    if campaign_id.endswith(CAMPAIGN_ID_TEMPLATE_SUFFIX):
        return False
    if campaign_id == RUNTIME_GO_PLACEHOLDER:
        return False
    return bool(campaign_id.strip())


def compose_campaign_substitution(service_name: str) -> str:
    lane = lane_for_service(service_name)
    return f"${{{lane.campaign_id_host_env}:-}}"


def compose_service_campaign_env(service_name: str) -> dict[str, str]:
    return {CDB_CAMPAIGN_ID_ENV: compose_campaign_substitution(service_name)}


def build_host_env_from_manifest(manifest: Mapping[str, Any]) -> dict[str, str]:
    """Map one rewritten campaign manifest to its host compose substitution env."""
    strategy_id = manifest.get("strategy_id")
    lane = next(
        (item for item in PARALLEL_SIGNAL_LANES if item.strategy_id == strategy_id),
        None,
    )
    if lane is None:
        raise ValueError(
            f"manifest strategy_id {strategy_id!r} is not a parallel signal lane"
        )
    campaign_id = manifest_campaign_id(manifest)
    return {lane.campaign_id_host_env: campaign_id}


def build_parallel_compose_host_env(
    pb1_manifest: Mapping[str, Any],
    donchian_manifest: Mapping[str, Any],
) -> dict[str, str]:
    """Merge host env for both parallel lanes from rewritten manifests."""
    host_env: dict[str, str] = {}
    host_env.update(build_host_env_from_manifest(pb1_manifest))
    host_env.update(build_host_env_from_manifest(donchian_manifest))
    if (
        host_env[CAMPAIGN_ID_HOST_ENV_PB1]
        == host_env[CAMPAIGN_ID_HOST_ENV_DONCHIAN]
    ):
        raise ValueError("parallel lane campaign_id values must be distinct")
    return host_env


def resolve_lane_runtime_campaign_id(
    service_name: str,
    host_env: Mapping[str, str],
) -> str | None:
    """Resolve container CDB_CAMPAIGN_ID from host substitution env."""
    lane = lane_for_service(service_name)
    raw = host_env.get(lane.campaign_id_host_env, "").strip()
    return raw or None


def validate_manifest_lane_alignment(manifest: Mapping[str, Any]) -> ParallelSignalLane:
    lane = lane_for_service(_runtime_target_signal_service(manifest))
    if manifest.get("strategy_id") != lane.strategy_id:
        raise ValueError(
            f"manifest strategy_id {manifest.get('strategy_id')!r} "
            f"does not match lane {lane.service_name} ({lane.strategy_id!r})"
        )
    bot_id = manifest.get("bot_id")
    if bot_id != lane.bot_id:
        raise ValueError(
            f"manifest bot_id {bot_id!r} does not match lane "
            f"{lane.service_name} ({lane.bot_id!r})"
        )
    return lane


def validate_parallel_manifest_pair(
    pb1_manifest: Mapping[str, Any],
    donchian_manifest: Mapping[str, Any],
) -> dict[str, str]:
    pb1_lane = validate_manifest_lane_alignment(pb1_manifest)
    donchian_lane = validate_manifest_lane_alignment(donchian_manifest)
    if pb1_lane.service_name == donchian_lane.service_name:
        raise ValueError("parallel manifests must target distinct signal services")
    return build_parallel_compose_host_env(pb1_manifest, donchian_manifest)


def load_parallel_signal_compose_override(
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]
    path = root / PARALLEL_SIGNAL_COMPOSE_OVERRIDE
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("parallel signal compose override must be a YAML object")
    return raw


def _runtime_target_signal_service(manifest: Mapping[str, Any]) -> str:
    targets = manifest.get("runtime_targets")
    if not isinstance(targets, list):
        raise ValueError("manifest runtime_targets must be a list")
    signal_targets = [
        target
        for target in targets
        if isinstance(target, str) and target in LANE_BY_SERVICE
    ]
    if len(signal_targets) != 1:
        raise ValueError(
            "manifest must declare exactly one parallel signal runtime target"
        )
    return signal_targets[0]
