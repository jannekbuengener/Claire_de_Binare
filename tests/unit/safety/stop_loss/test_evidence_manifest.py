"""Evidence manifest generator tests (Issue #4186).

Protected rule: the committed evidence artifact must be reproducible from the
library code and must not drift from the honest protection status.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.safety.stop_loss_protection import STOP_LOSS_PROTECTION_STATUS
from tools.safety.stop_loss_consumer_evidence import (
    EVIDENCE_SCHEMA_VERSION,
    build_manifest,
)

_ARTIFACT = (
    Path(__file__).resolve().parents[4]
    / "docs"
    / "evidence"
    / "risk"
    / "4186_stop_loss_consumer_dedup.json"
)


@pytest.fixture(scope="module")
def manifest() -> dict:
    return build_manifest(include_timestamp=False)


@pytest.mark.unit
def test_all_scenarios_pass(manifest):
    failures = [s for s in manifest["scenarios"] if s["status"] != "PASS"]
    assert failures == []
    assert manifest["verdict"] == "PASS_CONSUMER_DEDUP_MOCK_SHADOW"


@pytest.mark.unit
def test_shadow_run_emits_exactly_one_unique_intent(manifest):
    shadow = manifest["shadow_run"]
    assert shadow["emitted_intent_count"] == 1
    assert shadow["unique_emitted_intent_count"] == 1
    assert shadow["productive_adapter_enabled"] is False


@pytest.mark.unit
def test_shadow_run_restarts_and_stays_deduped(manifest):
    steps = manifest["shadow_run"]["steps"]
    restart_steps = [step for step in steps if step["restarted_before_step"]]
    assert restart_steps, "shadow replay must simulate at least one consumer restart"

    first_restart = restart_steps[0]["index"]
    emitting = [step for step in steps if step["intent_id"] is not None]
    assert len(emitting) == 1
    assert emitting[0]["index"] < first_restart, "restart must follow the emission"

    after_restart = [step for step in steps if step["index"] >= first_restart]
    assert all(step["intent_id"] is None for step in after_restart)
    assert all(step["decision"] == "DUPLICATE_SUPPRESSED" for step in after_restart)


@pytest.mark.unit
def test_manifest_declares_honest_boundaries(manifest):
    boundaries = manifest["boundaries"]
    assert boundaries["lr_verdict"] == "NO-GO"
    assert boundaries["live_go"] is False
    assert boundaries["echtgeld_go"] is False
    assert boundaries["productive_adapter_enabled"] is False
    assert boundaries["productive_queue_enabled"] is False
    assert boundaries["productive_db_write"] is False
    assert boundaries["real_stack_persistence_proven"] is False
    assert boundaries["risk_limits_changed"] is False


@pytest.mark.unit
def test_manifest_keeps_protection_unavailable(manifest):
    assert manifest["stop_loss_protection_status"] == "UNAVAILABLE"
    assert manifest["stop_loss_protection_status"] == STOP_LOSS_PROTECTION_STATUS.value
    assert manifest["stop_loss_protection_evidence_gaps"] == [
        "real_stack_persistence_proven",
        "productive_exit_path_proven",
    ]


@pytest.mark.unit
def test_committed_artifact_binds_a_clean_commit():
    """The artifact must name the commit it was produced from, not a dirty tree."""
    committed = json.loads(_ARTIFACT.read_text(encoding="utf-8"))

    assert committed["commit_sha"] != "unknown"
    assert len(committed["commit_sha"]) == 40
    assert committed["worktree_dirty"] is False


@pytest.mark.unit
def test_committed_artifact_matches_current_behaviour(manifest):
    committed = json.loads(_ARTIFACT.read_text(encoding="utf-8"))

    assert committed["schema_version"] == EVIDENCE_SCHEMA_VERSION
    assert committed["verdict"] == manifest["verdict"]
    assert committed["scenarios"] == manifest["scenarios"]
    assert committed["contract_versions"] == manifest["contract_versions"]
    assert committed["shadow_run"] == manifest["shadow_run"]
    assert committed["boundaries"] == manifest["boundaries"]
