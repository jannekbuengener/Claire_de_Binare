"""Diagnostic telemetry preflight contract tests (#3965)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.arvp_diag_telemetry_preflight import (
    DIAG_DONCHIAN_MANIFEST,
    DIAG_PB1_MANIFEST,
    DIAG_SIGNAL_COMPOSE_OVERRIDE,
    build_preflight_report,
    load_diag_manifests,
    validate_diag_compose_alignment,
    validate_diag_manifest_pair,
)
from tools.arvp_parallel_lane_compose_contract import (
    CAMPAIGN_ID_HOST_ENV_DONCHIAN,
    CAMPAIGN_ID_HOST_ENV_PB1,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]

PB1_CAMPAIGN_ID = "arvp_diag_p15_pb1_20260710t1100z"
DONCHIAN_CAMPAIGN_ID = "arvp_diag_p15_donchian_20260710t1100z"


def test_diag_manifest_campaign_ids_are_distinct_and_not_3912() -> None:
    pb1_manifest, donchian_manifest = load_diag_manifests(REPO_ROOT)

    assert pb1_manifest["campaign_id"] == PB1_CAMPAIGN_ID
    assert donchian_manifest["campaign_id"] == DONCHIAN_CAMPAIGN_ID
    assert PB1_CAMPAIGN_ID != DONCHIAN_CAMPAIGN_ID
    assert "3912" not in PB1_CAMPAIGN_ID
    assert "3912" not in DONCHIAN_CAMPAIGN_ID


def test_diag_bot_ids_are_distinct_from_3912() -> None:
    pb1_manifest, donchian_manifest = load_diag_manifests(REPO_ROOT)

    assert pb1_manifest["bot_id"] == "np-pb1-diag-01"
    assert donchian_manifest["bot_id"] == "np-donchian-diag-01"
    assert pb1_manifest["bot_id"] != "np-pb1-parallel-01"
    assert donchian_manifest["bot_id"] != "np-donchian-parallel-01"


def test_diag_host_env_maps_manifest_campaign_ids() -> None:
    pb1_manifest, donchian_manifest = load_diag_manifests(REPO_ROOT)
    host_env = validate_diag_manifest_pair(pb1_manifest, donchian_manifest)

    assert host_env[CAMPAIGN_ID_HOST_ENV_PB1] == PB1_CAMPAIGN_ID
    assert host_env[CAMPAIGN_ID_HOST_ENV_DONCHIAN] == DONCHIAN_CAMPAIGN_ID


def test_diag_compose_override_aligns_with_host_env() -> None:
    pb1_manifest, donchian_manifest = load_diag_manifests(REPO_ROOT)
    host_env = validate_diag_manifest_pair(pb1_manifest, donchian_manifest)
    from tools.arvp_diag_telemetry_preflight import load_diag_compose_override

    compose_override = load_diag_compose_override(REPO_ROOT)
    validate_diag_compose_alignment(host_env, compose_override)


def test_preflight_report_is_ready_pending_runtime_go() -> None:
    report = build_preflight_report(REPO_ROOT)

    assert report["status"] == "READY_PENDING_RUNTIME_GO"
    assert report["runtime_not_started"] is True
    assert report["lr_status"] == "NO-GO"
    assert report["manifests"]["pb1"] == DIAG_PB1_MANIFEST
    assert report["manifests"]["donchian"] == DIAG_DONCHIAN_MANIFEST
    assert report["compose_override"] == DIAG_SIGNAL_COMPOSE_OVERRIDE
