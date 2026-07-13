"""P1.5 parallel lane CDB_CAMPAIGN_ID compose contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.replay.correlation_ledger_attribution import CDB_CAMPAIGN_ID_ENV
from tools.arvp_parallel_lane_compose_contract import (
    CAMPAIGN_ID_HOST_ENV_DONCHIAN,
    CAMPAIGN_ID_HOST_ENV_PB1,
    DONCHIAN_MANIFEST_PATH,
    PB1_MANIFEST_PATH,
    build_host_env_from_manifest,
    build_parallel_compose_host_env,
    compose_campaign_substitution,
    load_campaign_manifest,
    load_parallel_signal_compose_override,
    resolve_lane_runtime_campaign_id,
    validate_manifest_lane_alignment,
    validate_parallel_manifest_pair,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]

PB1_CAMPAIGN_ID = "arvp_3912_np_parallel_pb1_20260709_1327"
DONCHIAN_CAMPAIGN_ID = "arvp_3912_np_parallel_donchian_20260709_1327"


def _rewritten_pb1_manifest() -> dict:
    manifest = load_campaign_manifest(REPO_ROOT / PB1_MANIFEST_PATH)
    manifest["campaign_id"] = PB1_CAMPAIGN_ID
    manifest["start_utc"] = "2026-07-09T13:27:00Z"
    manifest["timeout_utc"] = "2026-07-10T01:27:00Z"
    return manifest


def _rewritten_donchian_manifest() -> dict:
    manifest = load_campaign_manifest(REPO_ROOT / DONCHIAN_MANIFEST_PATH)
    manifest["campaign_id"] = DONCHIAN_CAMPAIGN_ID
    manifest["start_utc"] = "2026-07-09T13:27:00Z"
    manifest["timeout_utc"] = "2026-07-10T01:27:00Z"
    return manifest


def test_compose_override_declares_lane_specific_campaign_id_substitution() -> None:
    override = load_parallel_signal_compose_override(REPO_ROOT)
    pb1_env = override["services"]["cdb_signal_pb1"]["environment"]
    donchian_env = override["services"]["cdb_signal_donchian"]["environment"]

    assert pb1_env[CDB_CAMPAIGN_ID_ENV] == compose_campaign_substitution("cdb_signal_pb1")
    assert donchian_env[CDB_CAMPAIGN_ID_ENV] == compose_campaign_substitution(
        "cdb_signal_donchian"
    )
    assert pb1_env[CDB_CAMPAIGN_ID_ENV] != donchian_env[CDB_CAMPAIGN_ID_ENV]


@pytest.mark.parametrize(
    ("service_name", "expected_host_env", "expected_campaign_id"),
    (
        ("cdb_signal_pb1", CAMPAIGN_ID_HOST_ENV_PB1, PB1_CAMPAIGN_ID),
        (
            "cdb_signal_donchian",
            CAMPAIGN_ID_HOST_ENV_DONCHIAN,
            DONCHIAN_CAMPAIGN_ID,
        ),
    ),
)
def test_manifest_maps_to_lane_host_env_and_runtime_campaign_id(
    service_name: str,
    expected_host_env: str,
    expected_campaign_id: str,
) -> None:
    pb1_manifest = _rewritten_pb1_manifest()
    donchian_manifest = _rewritten_donchian_manifest()
    host_env = validate_parallel_manifest_pair(pb1_manifest, donchian_manifest)

    assert host_env[expected_host_env] == expected_campaign_id
    assert resolve_lane_runtime_campaign_id(service_name, host_env) == expected_campaign_id


def test_parallel_lane_campaign_ids_are_distinct() -> None:
    host_env = build_parallel_compose_host_env(
        _rewritten_pb1_manifest(),
        _rewritten_donchian_manifest(),
    )
    assert host_env[CAMPAIGN_ID_HOST_ENV_PB1] != host_env[CAMPAIGN_ID_HOST_ENV_DONCHIAN]


def test_manifest_lane_alignment_matches_bot_id_and_strategy_id() -> None:
    pb1_manifest = _rewritten_pb1_manifest()
    donchian_manifest = _rewritten_donchian_manifest()

    pb1_lane = validate_manifest_lane_alignment(pb1_manifest)
    donchian_lane = validate_manifest_lane_alignment(donchian_manifest)

    assert pb1_lane.service_name == "cdb_signal_pb1"
    assert pb1_lane.strategy_id == pb1_manifest["strategy_id"]
    assert pb1_lane.bot_id == pb1_manifest["bot_id"]

    assert donchian_lane.service_name == "cdb_signal_donchian"
    assert donchian_lane.strategy_id == donchian_manifest["strategy_id"]
    assert donchian_lane.bot_id == donchian_manifest["bot_id"]


def test_build_host_env_from_manifest_rejects_shared_campaign_id() -> None:
    pb1_manifest = _rewritten_pb1_manifest()
    donchian_manifest = _rewritten_donchian_manifest()
    donchian_manifest["campaign_id"] = pb1_manifest["campaign_id"]

    with pytest.raises(ValueError, match="distinct"):
        build_parallel_compose_host_env(pb1_manifest, donchian_manifest)


def test_compose_campaign_env_unchanged_for_signal_bot_and_strategy_ids() -> None:
    override = load_parallel_signal_compose_override(REPO_ROOT)
    pb1_env = override["services"]["cdb_signal_pb1"]["environment"]
    donchian_env = override["services"]["cdb_signal_donchian"]["environment"]

    assert pb1_env["SIGNAL_STRATEGY_ID"] == "primary_breakout_v1"
    assert pb1_env["SIGNAL_BOT_ID"] == "np-pb1-parallel-01"
    assert donchian_env["SIGNAL_STRATEGY_ID"] == "donchian_breakout_v1"
    assert donchian_env["SIGNAL_BOT_ID"] == "np-donchian-parallel-01"


def test_single_lane_host_env_builder() -> None:
    host_env = build_host_env_from_manifest(_rewritten_pb1_manifest())
    assert host_env == {CAMPAIGN_ID_HOST_ENV_PB1: PB1_CAMPAIGN_ID}
