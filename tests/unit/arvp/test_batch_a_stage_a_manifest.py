"""Tests for Batch-A Stage-A campaign manifest builder (#4032)."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.replay.canonical_json import canonical_hash
from tools.arvp_vacation.batch_a_stage_a_manifest import (
    EXPECTED_JOB_COUNT,
    EXPECTED_SCENARIO_RUN_COUNT,
    EXPECTED_STRATEGY_COUNT,
    EXPECTED_WINDOW_COUNT,
    StageAManifestError,
    build_stage_a_campaign_manifest,
    manifest_to_dict,
)
from tools.market_data.development_window_selector import (
    LOCKED_DEVELOPMENT_SELECTION_SHA256,
    load_window_bank_manifest,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]
MAIN_MANIFEST = (
    REPO_ROOT.parent
    / "Claire_de_Binare"
    / "artifacts/market_data/window_bank/binance/spot/BTCUSDT/1m/"
    "window_bank_manifest.json"
)
LOCAL_MANIFEST = (
    REPO_ROOT
    / "artifacts/market_data/window_bank/binance/spot/BTCUSDT/1m/"
    "window_bank_manifest.json"
)
SOURCE_SHA = "a" * 64


def _manifest_path() -> Path | None:
    if LOCAL_MANIFEST.exists():
        return LOCAL_MANIFEST
    if MAIN_MANIFEST.exists():
        return MAIN_MANIFEST
    return None


@pytest.fixture
def bank_manifest_path() -> Path:
    path = _manifest_path()
    if path is None:
        pytest.skip("Binance window bank manifest not available")
    return path


def test_builds_780_scenario_run_manifest(bank_manifest_path: Path) -> None:
    repo_root = bank_manifest_path.parents[7]
    manifest = build_stage_a_campaign_manifest(
        campaign_id="batch_a_stage_a_test",
        source_sha=SOURCE_SHA,
        manifest_path=bank_manifest_path,
        repo_root=repo_root,
    )
    assert manifest.strategy_count == EXPECTED_STRATEGY_COUNT
    assert manifest.window_count == EXPECTED_WINDOW_COUNT
    assert manifest.job_count == EXPECTED_JOB_COUNT
    assert manifest.scenario_run_count == EXPECTED_SCENARIO_RUN_COUNT
    assert manifest.development_selection_sha256 == LOCKED_DEVELOPMENT_SELECTION_SHA256
    payload = manifest_to_dict(manifest)
    assert payload["campaign_id"] == "batch_a_stage_a_test"
    assert payload["source_sha"] == SOURCE_SHA
    hash_payload = {key: value for key, value in payload.items() if key != "manifest_sha256"}
    assert manifest.manifest_sha256 == canonical_hash(hash_payload)


def test_rejects_invalid_source_sha(bank_manifest_path: Path) -> None:
    repo_root = bank_manifest_path.parents[7]
    with pytest.raises(StageAManifestError, match="source_sha"):
        build_stage_a_campaign_manifest(
            campaign_id="batch_a_stage_a_test",
            source_sha="not-a-sha",
            manifest_path=bank_manifest_path,
            repo_root=repo_root,
        )
