"""Re-verify diagnostic telemetry preflight contract tests (#3973)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.arvp_diag_reverify_preflight import (
    EXPECTED_REVERIFY_SOURCE_SHA,
    REVERIFY_DONCHIAN_MANIFEST,
    REVERIFY_PB1_MANIFEST,
    REVERIFY_SIGNAL_COMPOSE_OVERRIDE,
    build_reverify_preflight_report,
    load_reverify_compose_override,
    load_reverify_manifests,
    runtime_go_phrase,
    validate_reverify_compose_alignment,
    validate_reverify_manifest_pair,
)
from tools.arvp_parallel_lane_compose_contract import (
    CAMPAIGN_ID_HOST_ENV_DONCHIAN,
    CAMPAIGN_ID_HOST_ENV_PB1,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]

PB1_CAMPAIGN_ID = "arvp_diag_p0r_pb1_20260710t1600z"
DONCHIAN_CAMPAIGN_ID = "arvp_diag_p0r_donchian_20260710t1600z"


def test_reverify_manifest_campaign_ids_are_distinct_and_not_3967() -> None:
    pb1_manifest, donchian_manifest = load_reverify_manifests(REPO_ROOT)

    assert pb1_manifest["campaign_id"] == PB1_CAMPAIGN_ID
    assert donchian_manifest["campaign_id"] == DONCHIAN_CAMPAIGN_ID
    assert PB1_CAMPAIGN_ID != DONCHIAN_CAMPAIGN_ID
    assert "p15" not in PB1_CAMPAIGN_ID
    assert "p15" not in DONCHIAN_CAMPAIGN_ID


def test_reverify_bot_ids_are_distinct_from_3967() -> None:
    pb1_manifest, donchian_manifest = load_reverify_manifests(REPO_ROOT)

    assert pb1_manifest["bot_id"] == "np-pb1-reverify-01"
    assert donchian_manifest["bot_id"] == "np-donchian-reverify-01"
    assert pb1_manifest["bot_id"] != "np-pb1-diag-01"
    assert donchian_manifest["bot_id"] != "np-donchian-diag-01"


def test_reverify_manifests_pin_expected_source_sha() -> None:
    pb1_manifest, donchian_manifest = load_reverify_manifests(REPO_ROOT)

    assert pb1_manifest["expected_source_sha"] == EXPECTED_REVERIFY_SOURCE_SHA
    assert donchian_manifest["expected_source_sha"] == EXPECTED_REVERIFY_SOURCE_SHA


def test_reverify_host_env_maps_manifest_campaign_ids_and_sha() -> None:
    pb1_manifest, donchian_manifest = load_reverify_manifests(REPO_ROOT)
    host_env = validate_reverify_manifest_pair(pb1_manifest, donchian_manifest)

    assert host_env[CAMPAIGN_ID_HOST_ENV_PB1] == PB1_CAMPAIGN_ID
    assert host_env[CAMPAIGN_ID_HOST_ENV_DONCHIAN] == DONCHIAN_CAMPAIGN_ID


def test_reverify_compose_override_aligns_with_host_env() -> None:
    pb1_manifest, donchian_manifest = load_reverify_manifests(REPO_ROOT)
    host_env = validate_reverify_manifest_pair(pb1_manifest, donchian_manifest)
    compose_override = load_reverify_compose_override(REPO_ROOT)
    validate_reverify_compose_alignment(host_env, compose_override)


def test_reverify_preflight_report_is_ready_pending_runtime_go() -> None:
    report = build_reverify_preflight_report(REPO_ROOT)

    assert report["status"] == "READY_PENDING_RUNTIME_GO"
    assert report["runtime_not_started"] is True
    assert report["runtime_verified"] is False
    assert report["lr_status"] == "NO-GO"
    assert report["manifests"]["pb1"] == REVERIFY_PB1_MANIFEST
    assert report["manifests"]["donchian"] == REVERIFY_DONCHIAN_MANIFEST
    assert report["compose_override"] == REVERIFY_SIGNAL_COMPOSE_OVERRIDE
    assert (
        report["runtime_freshness"]["expected_source_sha"]
        == EXPECTED_REVERIFY_SOURCE_SHA
    )
    assert "CDB_SOURCE_SHA" in report["host_env_exports"]["powershell"]


def test_runtime_go_phrase_contains_required_tokens() -> None:
    phrase = runtime_go_phrase()
    assert "RUNTIME-GO #3973" in phrase
    assert EXPECTED_REVERIFY_SOURCE_SHA in phrase
    assert "CDB_SOURCE_SHA verified" in phrase
    assert "no Live/Echtgeld" in phrase
