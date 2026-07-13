"""Parallel natural-paper preflight after telemetry PASS contract tests (#3980)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.arvp_np_telemetry_pass_preflight import (
    EXPECTED_SOURCE_SHA,
    NP_DONCHIAN_MANIFEST,
    NP_PB1_MANIFEST,
    NP_SIGNAL_COMPOSE_OVERRIDE,
    build_np_preflight_report,
    load_np_compose_override,
    load_np_manifests,
    runtime_go_phrase,
    validate_np_compose_alignment,
    validate_np_manifest_pair,
)
from tools.arvp_parallel_lane_compose_contract import (
    CAMPAIGN_ID_HOST_ENV_DONCHIAN,
    CAMPAIGN_ID_HOST_ENV_PB1,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]

PB1_CAMPAIGN_ID = "arvp_np_pb1_after_telemetry_pass_20260710t1700z"
DONCHIAN_CAMPAIGN_ID = "arvp_np_donchian_after_telemetry_pass_20260710t1700z"


def test_np_manifest_campaign_ids_are_distinct_and_fresh() -> None:
    pb1_manifest, donchian_manifest = load_np_manifests(REPO_ROOT)

    assert pb1_manifest["campaign_id"] == PB1_CAMPAIGN_ID
    assert donchian_manifest["campaign_id"] == DONCHIAN_CAMPAIGN_ID
    assert PB1_CAMPAIGN_ID != DONCHIAN_CAMPAIGN_ID
    assert "3912" not in PB1_CAMPAIGN_ID
    assert "p15" not in PB1_CAMPAIGN_ID
    assert "p0r" not in PB1_CAMPAIGN_ID


def test_np_bot_ids_are_distinct_from_prior_runs() -> None:
    pb1_manifest, donchian_manifest = load_np_manifests(REPO_ROOT)

    assert pb1_manifest["bot_id"] == "np-pb1-telemetry-pass-01"
    assert donchian_manifest["bot_id"] == "np-donchian-telemetry-pass-01"
    assert pb1_manifest["bot_id"] != "np-pb1-parallel-01"
    assert donchian_manifest["bot_id"] != "np-donchian-parallel-01"
    assert pb1_manifest["bot_id"] != "np-pb1-reverify-01"


def test_np_manifests_pin_expected_source_sha() -> None:
    pb1_manifest, donchian_manifest = load_np_manifests(REPO_ROOT)

    assert pb1_manifest["expected_source_sha"] == EXPECTED_SOURCE_SHA
    assert donchian_manifest["expected_source_sha"] == EXPECTED_SOURCE_SHA


def test_np_host_env_maps_manifest_campaign_ids_and_sha() -> None:
    pb1_manifest, donchian_manifest = load_np_manifests(REPO_ROOT)
    host_env = validate_np_manifest_pair(pb1_manifest, donchian_manifest)

    assert host_env[CAMPAIGN_ID_HOST_ENV_PB1] == PB1_CAMPAIGN_ID
    assert host_env[CAMPAIGN_ID_HOST_ENV_DONCHIAN] == DONCHIAN_CAMPAIGN_ID


def test_np_compose_override_aligns_with_host_env() -> None:
    pb1_manifest, donchian_manifest = load_np_manifests(REPO_ROOT)
    host_env = validate_np_manifest_pair(pb1_manifest, donchian_manifest)
    compose_override = load_np_compose_override(REPO_ROOT)
    validate_np_compose_alignment(host_env, compose_override)


def test_np_preflight_report_is_ready_pending_runtime_go() -> None:
    report = build_np_preflight_report(REPO_ROOT)

    assert report["status"] == "READY_PENDING_RUNTIME_GO"
    assert report["runtime_not_started"] is True
    assert report["runtime_verified"] is False
    assert report["lr_status"] == "NO-GO"
    assert report["recommended_window_hours"] == 4.0
    assert report["manifests"]["pb1"] == NP_PB1_MANIFEST
    assert report["manifests"]["donchian"] == NP_DONCHIAN_MANIFEST
    assert report["compose_override"] == NP_SIGNAL_COMPOSE_OVERRIDE
    assert report["runtime_freshness"]["expected_source_sha"] == EXPECTED_SOURCE_SHA
    assert "CDB_SOURCE_SHA" in report["host_env_exports"]["powershell"]


def test_runtime_go_phrase_contains_required_tokens() -> None:
    phrase = runtime_go_phrase()
    assert "RUNTIME-GO #3980" in phrase
    assert "4h ARVP PB1 + Donchian parallel natural-paper run after telemetry PASS" in phrase
    assert "CDB_CAMPAIGN_ID_PB1 and CDB_CAMPAIGN_ID_DONCHIAN set from manifests" in phrase
    assert "CDB_SOURCE_SHA verified in containers before observation" in phrase
    assert "no Live/Echtgeld" in phrase
