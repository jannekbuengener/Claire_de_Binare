"""Campaign summary + PRIMARY_COMPLETE persistence tests (#4404).

test_id: tc_hh_hl_campaign_summary_001
test_type: schutz|bauteil|contract
cdb_area: arvp/validation-research
issue_ref: #4404 #4410
security_relevant: true
live_relevant: false
profitability_relevant: false

Protects:
- successful 39/39 → campaign_summary.json + PRIMARY_COMPLETE
- blocked / failed / incomplete → no PRIMARY_COMPLETE
- resume/skip counting
- binding mismatch fail-closed
- idempotent re-finalize
- run evidence immutability
- summary write failure leaves non-success lifecycle
- summary physical_parameter_set_fingerprint == grid/historical binding (#4410)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.arvp_vacation.hh_hl_campaign_grid import expand_hh_hl_variants
from tools.arvp_vacation.hh_hl_campaign_lifecycle import HH_HL_EXPECTED_RUN_COUNT
from tools.arvp_vacation.hh_hl_campaign_summary import (
    CAMPAIGN_SUMMARY_NAME,
    CAMPAIGN_SUMMARY_SCHEMA_VERSION,
    HhHlCampaignSummaryError,
    campaign_summary_path,
    inspect_primary_run_counts,
    persist_hh_hl_primary_completion,
    physical_parameter_set_fingerprint,
    read_campaign_summary,
)
from tools.arvp_vacation.sensitivity_campaign_state import (
    CAMPAIGN_PHASE_PLANNED,
    CAMPAIGN_PHASE_PRIMARY_COMPLETE,
    CAMPAIGN_PHASE_PRIMARY_RUNNING,
    CampaignBindings,
    commit_successful_result,
    read_campaign_phase,
    run_envelope_path,
    write_campaign_envelope,
    write_run_envelope,
)

BINDINGS = CampaignBindings(
    campaign_id="arvp-hh-hl-continuation-4374-prep-v1",
    manifest_fingerprint="1" * 64,
    run_plan_fingerprint="2" * 64,
    authorization_fingerprint="3" * 64,
    execution_sha="a" * 40,
    main_sha="b" * 40,
)
DATASET_SEL = "c" * 64
DATASET_DIGEST = "d" * 64
RUN_KEYS = tuple(f"rk_{i:02d}" for i in range(HH_HL_EXPECTED_RUN_COUNT))


def _seed_envelope(root: Path) -> None:
    write_campaign_envelope(
        root,
        bindings=BINDINGS,
        run_count=HH_HL_EXPECTED_RUN_COUNT,
        extra={"phase": "PRIMARY"},
    )


def _succeed_run(root: Path, run_key: str) -> None:
    commit_successful_result(
        root,
        run_key=run_key,
        bindings=BINDINGS,
        attempt=1,
        envelope={"run_key": run_key, "seed": "x"},
        result={"closed_trades_total": 0, "run_key": run_key},
        exit_code=0,
    )


def _fail_run(root: Path, run_key: str) -> None:
    write_run_envelope(
        root,
        run_key=run_key,
        bindings=BINDINGS,
        status="FAILED",
        attempt=1,
        envelope={"run_key": run_key},
        exit_code=1,
    )


def _block_run(root: Path, run_key: str) -> None:
    write_run_envelope(
        root,
        run_key=run_key,
        bindings=BINDINGS,
        status="BLOCKED",
        attempt=1,
        envelope={"run_key": run_key, "terminal_reason": "HOLD_EXECUTION_TEST"},
    )


def _snapshot_run_tree(root: Path) -> dict[str, str]:
    snap: dict[str, str] = {}
    runs = root / "runs"
    if not runs.exists():
        return snap
    for path in sorted(runs.rglob("*")):
        if path.is_file():
            snap[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    return snap


HISTORICAL_BASELINE_PARAMETER_FP = (
    "9067cd6aa48ad2cc2a7932af50e990888048b8f912b8f3e3ad0dd5b318d1c0a4"
)


def test_summary_parameter_fp_matches_grid_and_historical_binding() -> None:
    """#4410: summary must use grid strategy_id+param_set semantics (9067cd6a…)."""
    grid_fp = expand_hh_hl_variants()[0].physical_parameter_set_fingerprint
    summary_fp = physical_parameter_set_fingerprint()
    assert summary_fp == grid_fp
    assert summary_fp == HISTORICAL_BASELINE_PARAMETER_FP
    # Guard against params-only hash regression (76036390…).
    assert not summary_fp.startswith("76036390")


def test_39_of_39_success_writes_summary_and_primary_complete(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    _seed_envelope(root)
    for key in RUN_KEYS:
        _succeed_run(root, key)

    before = _snapshot_run_tree(root)
    result = persist_hh_hl_primary_completion(
        root,
        bindings=BINDINGS,
        expected_run_keys=RUN_KEYS,
        dataset_selection_sha256=DATASET_SEL,
        dataset_content_fingerprint_digest=DATASET_DIGEST,
        github_comment_id=5222204496,
        authorizing_github_login="jannekbuengener",
        owner_go_status="GO_HH_HL_CAMPAIGN_EXECUTION",
    )
    assert result["ok"] is True
    assert result["idempotent"] is False
    assert read_campaign_phase(root) == CAMPAIGN_PHASE_PRIMARY_COMPLETE
    summary = read_campaign_summary(root)
    assert summary["schema_version"] == CAMPAIGN_SUMMARY_SCHEMA_VERSION
    assert summary["campaign_phase"] == CAMPAIGN_PHASE_PRIMARY_COMPLETE
    assert summary["expected_run_count"] == 39
    assert summary["succeeded_count"] == 39
    assert summary["resumed_skipped_count"] == 0
    assert summary["failed_count"] == 0
    assert summary["blocked_count"] == 0
    assert summary["authorization_fingerprint"] == BINDINGS.authorization_fingerprint
    assert summary["execution_sha"] == BINDINGS.execution_sha
    assert summary["manifest_fingerprint"] == BINDINGS.manifest_fingerprint
    assert summary["run_plan_fingerprint"] == BINDINGS.run_plan_fingerprint
    assert summary["dataset_selection_sha256"] == DATASET_SEL
    assert summary["dataset_content_fingerprint_digest"] == DATASET_DIGEST
    assert summary["physical_parameter_set_fingerprint"] == (
        HISTORICAL_BASELINE_PARAMETER_FP
    )
    assert summary["lr_status"] == "NO-GO"
    assert (root / CAMPAIGN_SUMMARY_NAME).exists()
    assert before == _snapshot_run_tree(root)


def test_blocked_run_prevents_primary_complete(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    _seed_envelope(root)
    for key in RUN_KEYS[:-1]:
        _succeed_run(root, key)
    _block_run(root, RUN_KEYS[-1])

    with pytest.raises(HhHlCampaignSummaryError) as exc:
        persist_hh_hl_primary_completion(
            root,
            bindings=BINDINGS,
            expected_run_keys=RUN_KEYS,
            dataset_selection_sha256=DATASET_SEL,
            dataset_content_fingerprint_digest=DATASET_DIGEST,
        )
    assert exc.value.reason_code == "HOLD_CAMPAIGN_SUMMARY_PRIMARY_INCOMPLETE"
    assert read_campaign_phase(root) == CAMPAIGN_PHASE_PLANNED
    assert not campaign_summary_path(root).exists()


def test_failed_run_prevents_primary_complete(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    _seed_envelope(root)
    for key in RUN_KEYS[:-1]:
        _succeed_run(root, key)
    _fail_run(root, RUN_KEYS[-1])

    with pytest.raises(HhHlCampaignSummaryError) as exc:
        persist_hh_hl_primary_completion(
            root,
            bindings=BINDINGS,
            expected_run_keys=RUN_KEYS,
            dataset_selection_sha256=DATASET_SEL,
            dataset_content_fingerprint_digest=DATASET_DIGEST,
        )
    assert exc.value.reason_code == "HOLD_CAMPAIGN_SUMMARY_PRIMARY_INCOMPLETE"
    assert not campaign_summary_path(root).exists()
    assert read_campaign_phase(root) != CAMPAIGN_PHASE_PRIMARY_COMPLETE


def test_incomplete_runs_prevent_primary_complete(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    _seed_envelope(root)
    for key in RUN_KEYS[:20]:
        _succeed_run(root, key)

    counts = inspect_primary_run_counts(
        root, bindings=BINDINGS, expected_run_keys=RUN_KEYS
    )
    assert counts.missing == 19
    assert counts.is_primary_complete is False

    with pytest.raises(HhHlCampaignSummaryError) as exc:
        persist_hh_hl_primary_completion(
            root,
            bindings=BINDINGS,
            expected_run_keys=RUN_KEYS,
            dataset_selection_sha256=DATASET_SEL,
            dataset_content_fingerprint_digest=DATASET_DIGEST,
        )
    assert exc.value.reason_code == "HOLD_CAMPAIGN_SUMMARY_PRIMARY_INCOMPLETE"
    assert not campaign_summary_path(root).exists()


def test_resume_skips_counted_correctly(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    _seed_envelope(root)
    for key in RUN_KEYS:
        _succeed_run(root, key)
    skipped = list(RUN_KEYS[:10])

    result = persist_hh_hl_primary_completion(
        root,
        bindings=BINDINGS,
        expected_run_keys=RUN_KEYS,
        skipped_run_keys=skipped,
        dataset_selection_sha256=DATASET_SEL,
        dataset_content_fingerprint_digest=DATASET_DIGEST,
    )
    summary = result["summary"]
    assert summary["resumed_skipped_count"] == 10
    assert summary["succeeded_count"] == 29
    assert summary["failed_count"] == 0
    assert read_campaign_phase(root) == CAMPAIGN_PHASE_PRIMARY_COMPLETE


def test_binding_mismatch_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    _seed_envelope(root)
    for key in RUN_KEYS:
        _succeed_run(root, key)

    other = CampaignBindings(
        campaign_id=BINDINGS.campaign_id,
        manifest_fingerprint=BINDINGS.manifest_fingerprint,
        run_plan_fingerprint=BINDINGS.run_plan_fingerprint,
        authorization_fingerprint="9" * 64,
        execution_sha=BINDINGS.execution_sha,
        main_sha=BINDINGS.main_sha,
    )
    with pytest.raises(HhHlCampaignSummaryError) as exc:
        persist_hh_hl_primary_completion(
            root,
            bindings=other,
            expected_run_keys=RUN_KEYS,
            dataset_selection_sha256=DATASET_SEL,
            dataset_content_fingerprint_digest=DATASET_DIGEST,
        )
    assert exc.value.reason_code == "HOLD_CAMPAIGN_SUMMARY_BINDING_MISMATCH"
    assert not campaign_summary_path(root).exists()
    assert read_campaign_phase(root) == CAMPAIGN_PHASE_PLANNED


def test_finalize_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    _seed_envelope(root)
    for key in RUN_KEYS:
        _succeed_run(root, key)

    first = persist_hh_hl_primary_completion(
        root,
        bindings=BINDINGS,
        expected_run_keys=RUN_KEYS,
        dataset_selection_sha256=DATASET_SEL,
        dataset_content_fingerprint_digest=DATASET_DIGEST,
    )
    before_runs = _snapshot_run_tree(root)
    before_summary = campaign_summary_path(root).read_text(encoding="utf-8")
    second = persist_hh_hl_primary_completion(
        root,
        bindings=BINDINGS,
        expected_run_keys=RUN_KEYS,
        dataset_selection_sha256=DATASET_SEL,
        dataset_content_fingerprint_digest=DATASET_DIGEST,
    )
    assert second["idempotent"] is True
    assert second["campaign_phase"] == CAMPAIGN_PHASE_PRIMARY_COMPLETE
    assert before_runs == _snapshot_run_tree(root)
    assert before_summary == campaign_summary_path(root).read_text(encoding="utf-8")
    assert (
        first["summary"]["summary_fingerprint"]
        == second["summary"]["summary_fingerprint"]
    )


def test_run_evidence_unchanged_by_finalize(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    _seed_envelope(root)
    for key in RUN_KEYS:
        _succeed_run(root, key)
    before = _snapshot_run_tree(root)
    persist_hh_hl_primary_completion(
        root,
        bindings=BINDINGS,
        expected_run_keys=RUN_KEYS,
        dataset_selection_sha256=DATASET_SEL,
        dataset_content_fingerprint_digest=DATASET_DIGEST,
    )
    after = _snapshot_run_tree(root)
    assert before == after
    # Envelope + summary may change; run trees must not.
    assert "campaign_summary.json" not in before
    assert (root / "campaign_summary.json").exists()


def test_summary_write_failure_leaves_no_primary_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "evidence"
    _seed_envelope(root)
    for key in RUN_KEYS:
        _succeed_run(root, key)

    import tools.arvp_vacation.hh_hl_campaign_summary as summary_mod

    real_atomic = summary_mod.atomic_write_json

    def _selective(path: Path, payload: Any) -> None:
        if Path(path).name == CAMPAIGN_SUMMARY_NAME:
            raise OSError("simulated summary write failure")
        return real_atomic(path, payload)

    monkeypatch.setattr(summary_mod, "atomic_write_json", _selective)

    with pytest.raises(HhHlCampaignSummaryError) as exc:
        persist_hh_hl_primary_completion(
            root,
            bindings=BINDINGS,
            expected_run_keys=RUN_KEYS,
            dataset_selection_sha256=DATASET_SEL,
            dataset_content_fingerprint_digest=DATASET_DIGEST,
        )
    assert exc.value.reason_code == "HOLD_CAMPAIGN_SUMMARY_WRITE_FAILED"
    assert not campaign_summary_path(root).exists()
    # May have advanced to PRIMARY_RUNNING before summary write; must not be complete.
    assert read_campaign_phase(root) != CAMPAIGN_PHASE_PRIMARY_COMPLETE


def test_unexpected_extra_run_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    _seed_envelope(root)
    for key in RUN_KEYS:
        _succeed_run(root, key)
    _succeed_run(root, "rk_extra_unexpected")

    with pytest.raises(HhHlCampaignSummaryError) as exc:
        persist_hh_hl_primary_completion(
            root,
            bindings=BINDINGS,
            expected_run_keys=RUN_KEYS,
            dataset_selection_sha256=DATASET_SEL,
            dataset_content_fingerprint_digest=DATASET_DIGEST,
        )
    assert exc.value.reason_code == "HOLD_CAMPAIGN_SUMMARY_PRIMARY_INCOMPLETE"
    assert not campaign_summary_path(root).exists()


def test_phase_transition_failure_after_summary_not_primary_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "evidence"
    _seed_envelope(root)
    for key in RUN_KEYS:
        _succeed_run(root, key)

    import tools.arvp_vacation.hh_hl_campaign_summary as summary_mod

    real_update = summary_mod.update_campaign_phase
    calls = {"n": 0}

    def _update(root_path, *, bindings, phase, extra=None):
        calls["n"] += 1
        if phase == CAMPAIGN_PHASE_PRIMARY_COMPLETE:
            from tools.arvp_vacation.sensitivity_campaign_state import (
                SensitivityStateError,
            )

            raise SensitivityStateError("STATE_PHASE_ILLEGAL_TRANSITION:forced")
        return real_update(root_path, bindings=bindings, phase=phase, extra=extra)

    monkeypatch.setattr(summary_mod, "update_campaign_phase", _update)

    with pytest.raises(HhHlCampaignSummaryError) as exc:
        persist_hh_hl_primary_completion(
            root,
            bindings=BINDINGS,
            expected_run_keys=RUN_KEYS,
            dataset_selection_sha256=DATASET_SEL,
            dataset_content_fingerprint_digest=DATASET_DIGEST,
        )
    assert exc.value.reason_code == "HOLD_CAMPAIGN_SUMMARY_PHASE_UPDATE_FAILED"
    # Summary may exist, but lifecycle must not claim PRIMARY_COMPLETE.
    assert read_campaign_phase(root) == CAMPAIGN_PHASE_PRIMARY_RUNNING
    assert campaign_summary_path(root).exists()
