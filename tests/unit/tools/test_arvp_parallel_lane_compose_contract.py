"""Unit tests for parallel lane compose contract helpers."""

from __future__ import annotations

import pytest

from tools.arvp_parallel_lane_compose_contract import (
    build_host_env_from_manifest,
    is_runtime_ready_campaign_id,
    validate_manifest_lane_alignment,
)

pytestmark = pytest.mark.unit


def test_is_runtime_ready_campaign_id_rejects_template_placeholders() -> None:
    assert is_runtime_ready_campaign_id("arvp_3912_np_parallel_pb1_20260709_1327")
    assert not is_runtime_ready_campaign_id("arvp_3912_np_parallel_pb1_TEMPLATE")
    assert not is_runtime_ready_campaign_id("RUNTIME_GO_SET")


def test_validate_manifest_lane_alignment_rejects_bot_id_drift() -> None:
    manifest = {
        "strategy_id": "primary_breakout_v1",
        "bot_id": "wrong-bot",
        "runtime_targets": ["cdb_signal_pb1"],
    }
    with pytest.raises(ValueError, match="bot_id"):
        validate_manifest_lane_alignment(manifest)


def test_build_host_env_from_manifest_rejects_unknown_strategy() -> None:
    manifest = {"strategy_id": "unknown_strategy", "campaign_id": "campaign_x"}
    with pytest.raises(ValueError, match="parallel signal lane"):
        build_host_env_from_manifest(manifest)
