"""Campaign/run state ledger unit tests (#4153).

test_id: tc_sensitivity_campaign_state_001
test_type: schutz|bauteil
cdb_area: arvp/validation-research
issue_ref: #4153
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.arvp_vacation.sensitivity_campaign_state import (
    CAMPAIGN_PHASES,
    CAMPAIGN_PHASE_BLOCKED,
    CAMPAIGN_PHASE_COMPLETED,
    CAMPAIGN_PHASE_PRIMARY_COMPLETE,
    CAMPAIGN_PHASE_PRIMARY_RUNNING,
    CAMPAIGN_PHASE_REPRODUCTION_COMPLETE,
    CAMPAIGN_PHASE_REPRODUCTION_PLANNED,
    CAMPAIGN_PHASE_REPRODUCTION_RUNNING,
    CampaignBindings,
    SensitivityStateError,
    assert_namespace_startable,
    commit_successful_reproduction_result,
    commit_successful_result,
    count_primary_succeeded,
    inspect_reproduction_for_resume,
    inspect_run_for_resume,
    read_campaign_phase,
    reproduction_comparison_path,
    reproduction_completion_marker_path,
    reproduction_dir,
    reproduction_envelope_path,
    reproduction_result_path,
    update_campaign_phase,
    write_campaign_envelope,
    write_comparison_evidence,
    write_reproduction_envelope,
    write_run_envelope,
)

BINDINGS = CampaignBindings(
    campaign_id="arvp-sensitivity-4153-v1",
    manifest_fingerprint="a" * 64,
    run_plan_fingerprint="b" * 64,
    authorization_fingerprint="c" * 64,
    execution_sha="d" * 40,
    main_sha="d" * 40,
)


def test_success_skip_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=2)
    envelope = {"run_key": "rk1", "seed": "x"}
    commit_successful_result(
        root,
        run_key="rk1",
        bindings=BINDINGS,
        attempt=1,
        envelope=envelope,
        result={"gate_reason": "OK", "trade_count": 0},
    )
    action = inspect_run_for_resume(
        root,
        run_key="rk1",
        bindings=BINDINGS,
        max_attempts=3,
        retry_failed=True,
    )
    assert action == "skip"


def test_partial_success_blocks(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_run_envelope(
        root,
        run_key="rk1",
        bindings=BINDINGS,
        status="SUCCEEDED",
        attempt=1,
        envelope={"run_key": "rk1"},
        exit_code=0,
        result_fingerprint="e" * 64,
    )
    # Missing COMPLETED marker + result.json → partial.
    with pytest.raises(SensitivityStateError) as exc:
        inspect_run_for_resume(
            root,
            run_key="rk1",
            bindings=BINDINGS,
            max_attempts=3,
            retry_failed=True,
        )
    assert "STATE_PARTIAL_SUCCESS_BLOCKED" in str(exc.value)


def test_retry_limit_exceeded(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_run_envelope(
        root,
        run_key="rk1",
        bindings=BINDINGS,
        status="FAILED",
        attempt=2,
        envelope={"run_key": "rk1"},
        exit_code=1,
    )
    with pytest.raises(SensitivityStateError) as exc:
        inspect_run_for_resume(
            root,
            run_key="rk1",
            bindings=BINDINGS,
            max_attempts=2,
            retry_failed=True,
        )
    assert "STATE_RETRY_LIMIT_EXCEEDED" in str(exc.value)


def test_retry_allowed_under_limit(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_run_envelope(
        root,
        run_key="rk1",
        bindings=BINDINGS,
        status="FAILED",
        attempt=1,
        envelope={"run_key": "rk1"},
        exit_code=1,
    )
    action = inspect_run_for_resume(
        root,
        run_key="rk1",
        bindings=BINDINGS,
        max_attempts=3,
        retry_failed=True,
    )
    assert action == "retry"


def test_binding_mismatch_blocks(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=1)
    other = CampaignBindings(
        campaign_id=BINDINGS.campaign_id,
        manifest_fingerprint="f" * 64,
        run_plan_fingerprint=BINDINGS.run_plan_fingerprint,
        authorization_fingerprint=BINDINGS.authorization_fingerprint,
        execution_sha=BINDINGS.execution_sha,
        main_sha=BINDINGS.main_sha,
    )
    with pytest.raises(SensitivityStateError) as exc:
        assert_namespace_startable(root, bindings=other, allow_resume=True)
    assert "STATE_BINDING_MISMATCH" in str(exc.value)


def test_running_without_completion_blocks(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_run_envelope(
        root,
        run_key="rk1",
        bindings=BINDINGS,
        status="RUNNING",
        attempt=1,
        envelope={"run_key": "rk1"},
    )
    with pytest.raises(SensitivityStateError) as exc:
        inspect_run_for_resume(
            root,
            run_key="rk1",
            bindings=BINDINGS,
            max_attempts=3,
            retry_failed=True,
        )
    assert "STATE_RUNNING_WITHOUT_COMPLETION" in str(exc.value)


def test_fresh_namespace(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    assert assert_namespace_startable(root, bindings=BINDINGS, allow_resume=True) == (
        "fresh"
    )


def test_campaign_phases_frozenset_membership() -> None:
    for expected in (
        "PRIMARY_PLANNED",
        "PRIMARY_RUNNING",
        "PRIMARY_EVIDENCE_COMPLETE",
        "PRIMARY_COMPLETE",
        "REPRODUCTION_PLANNED",
        "REPRODUCTION_RUNNING",
        "REPRODUCTION_COMPLETE",
        "COMPLETED",
        "BLOCKED",
    ):
        assert expected in CAMPAIGN_PHASES


def test_update_campaign_phase_happy_transition_sequence(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=1)
    assert read_campaign_phase(root) == "PLANNED"

    update_campaign_phase(root, bindings=BINDINGS, phase=CAMPAIGN_PHASE_PRIMARY_RUNNING)
    assert read_campaign_phase(root) == "PRIMARY_RUNNING"
    update_campaign_phase(
        root, bindings=BINDINGS, phase=CAMPAIGN_PHASE_PRIMARY_COMPLETE
    )
    update_campaign_phase(
        root, bindings=BINDINGS, phase=CAMPAIGN_PHASE_REPRODUCTION_PLANNED
    )
    update_campaign_phase(
        root, bindings=BINDINGS, phase=CAMPAIGN_PHASE_REPRODUCTION_RUNNING
    )
    update_campaign_phase(
        root, bindings=BINDINGS, phase=CAMPAIGN_PHASE_REPRODUCTION_COMPLETE
    )
    update_campaign_phase(root, bindings=BINDINGS, phase=CAMPAIGN_PHASE_COMPLETED)
    assert read_campaign_phase(root) == "COMPLETED"


def test_update_campaign_phase_illegal_transition_raises(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=1)
    # PLANNED -> COMPLETED is illegal (must go via PRIMARY_RUNNING).
    with pytest.raises(SensitivityStateError) as exc:
        update_campaign_phase(root, bindings=BINDINGS, phase=CAMPAIGN_PHASE_COMPLETED)
    assert "STATE_PHASE_ILLEGAL_TRANSITION" in str(exc.value)


def test_update_campaign_phase_terminal_stays(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=1)
    update_campaign_phase(root, bindings=BINDINGS, phase=CAMPAIGN_PHASE_BLOCKED)
    # Terminal BLOCKED cannot transition further.
    with pytest.raises(SensitivityStateError) as exc:
        update_campaign_phase(root, bindings=BINDINGS, phase=CAMPAIGN_PHASE_COMPLETED)
    assert "STATE_PHASE_ILLEGAL_TRANSITION" in str(exc.value)
    # Idempotent stay is allowed.
    update_campaign_phase(root, bindings=BINDINGS, phase=CAMPAIGN_PHASE_BLOCKED)
    assert read_campaign_phase(root) == "BLOCKED"


def test_update_campaign_phase_binding_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=1)
    other = CampaignBindings(
        campaign_id=BINDINGS.campaign_id,
        manifest_fingerprint="f" * 64,
        run_plan_fingerprint=BINDINGS.run_plan_fingerprint,
        authorization_fingerprint=BINDINGS.authorization_fingerprint,
        execution_sha=BINDINGS.execution_sha,
        main_sha=BINDINGS.main_sha,
    )
    with pytest.raises(SensitivityStateError) as exc:
        update_campaign_phase(
            root, bindings=other, phase=CAMPAIGN_PHASE_PRIMARY_RUNNING
        )
    assert "STATE_BINDING_MISMATCH" in str(exc.value)


def test_update_campaign_phase_unknown_raises(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=1)
    with pytest.raises(SensitivityStateError) as exc:
        update_campaign_phase(root, bindings=BINDINGS, phase="BOGUS_PHASE")
    assert "STATE_PHASE_UNKNOWN" in str(exc.value)


def test_update_campaign_phase_missing_envelope(tmp_path: Path) -> None:
    root = tmp_path / "unknown"
    with pytest.raises(SensitivityStateError) as exc:
        update_campaign_phase(
            root, bindings=BINDINGS, phase=CAMPAIGN_PHASE_PRIMARY_RUNNING
        )
    assert "STATE_PHASE_ENVELOPE_MISSING" in str(exc.value)


def test_reproduction_resume_success_skips(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=1)
    commit_successful_reproduction_result(
        root,
        run_key="rk1",
        reproduction_attempt=1,
        bindings=BINDINGS,
        attempt=1,
        envelope={"run_key": "rk1", "reproduction_attempt": 1},
        result={"gate_reason": "OK", "trade_count": 0},
    )
    write_comparison_evidence(
        root,
        run_key="rk1",
        reproduction_attempt=1,
        comparison={
            "status": "PASS",
            "reason_code": "REPRODUCTION_EXACT_MATCH",
            "mismatched_fields": [],
            "comparison_fingerprint": "e" * 64,
        },
    )
    assert reproduction_completion_marker_path(root, "rk1", 1).exists()
    action = inspect_reproduction_for_resume(
        root,
        run_key="rk1",
        reproduction_attempt=1,
        bindings=BINDINGS,
        max_attempts=3,
        retry_failed=True,
    )
    assert action == "skip"


def test_reproduction_resume_success_without_comparison_blocks(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=1)
    commit_successful_reproduction_result(
        root,
        run_key="rk1",
        reproduction_attempt=1,
        bindings=BINDINGS,
        attempt=1,
        envelope={"run_key": "rk1", "reproduction_attempt": 1},
        result={"gate_reason": "OK", "trade_count": 0},
    )
    with pytest.raises(SensitivityStateError) as exc:
        inspect_reproduction_for_resume(
            root,
            run_key="rk1",
            reproduction_attempt=1,
            bindings=BINDINGS,
            max_attempts=3,
            retry_failed=True,
        )
    assert "STATE_REPRO_COMPARISON_MISSING" in str(exc.value)


def test_reproduction_resume_running_with_pass_comparison_finalizes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "ns"
    write_reproduction_envelope(
        root,
        run_key="rk1",
        reproduction_attempt=1,
        bindings=BINDINGS,
        status="RUNNING",
        attempt=1,
        envelope={"run_key": "rk1", "reproduction_attempt": 1},
    )
    from tools.arvp_vacation.sensitivity_campaign_state import (
        persist_reproduction_result,
    )

    persist_reproduction_result(
        root,
        run_key="rk1",
        reproduction_attempt=1,
        bindings=BINDINGS,
        result={"gate_reason": "OK", "trade_count": 0},
    )
    write_comparison_evidence(
        root,
        run_key="rk1",
        reproduction_attempt=1,
        comparison={
            "status": "PASS",
            "reason_code": "REPRODUCTION_EXACT_MATCH",
            "mismatched_fields": [],
            "comparison_fingerprint": "e" * 64,
        },
    )
    action = inspect_reproduction_for_resume(
        root,
        run_key="rk1",
        reproduction_attempt=1,
        bindings=BINDINGS,
        max_attempts=3,
        retry_failed=True,
    )
    assert action == "finalize"


def test_reproduction_resume_partial_blocks(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_reproduction_envelope(
        root,
        run_key="rk1",
        reproduction_attempt=1,
        bindings=BINDINGS,
        status="SUCCEEDED",
        attempt=1,
        envelope={"run_key": "rk1", "reproduction_attempt": 1},
        exit_code=0,
        result_fingerprint="d" * 64,
    )
    with pytest.raises(SensitivityStateError) as exc:
        inspect_reproduction_for_resume(
            root,
            run_key="rk1",
            reproduction_attempt=1,
            bindings=BINDINGS,
            max_attempts=3,
            retry_failed=True,
        )
    assert "STATE_REPRO_PARTIAL_SUCCESS_BLOCKED" in str(exc.value)


def test_reproduction_resume_running_blocks(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_reproduction_envelope(
        root,
        run_key="rk1",
        reproduction_attempt=1,
        bindings=BINDINGS,
        status="RUNNING",
        attempt=1,
        envelope={"run_key": "rk1", "reproduction_attempt": 1},
    )
    with pytest.raises(SensitivityStateError) as exc:
        inspect_reproduction_for_resume(
            root,
            run_key="rk1",
            reproduction_attempt=1,
            bindings=BINDINGS,
            max_attempts=3,
            retry_failed=True,
        )
    assert "STATE_REPRO_RUNNING_WITHOUT_COMPLETION" in str(exc.value)


def test_reproduction_resume_retry_limit(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_reproduction_envelope(
        root,
        run_key="rk1",
        reproduction_attempt=1,
        bindings=BINDINGS,
        status="FAILED",
        attempt=2,
        envelope={"run_key": "rk1", "reproduction_attempt": 1},
        exit_code=1,
    )
    with pytest.raises(SensitivityStateError) as exc:
        inspect_reproduction_for_resume(
            root,
            run_key="rk1",
            reproduction_attempt=1,
            bindings=BINDINGS,
            max_attempts=2,
            retry_failed=True,
        )
    assert "STATE_REPRO_RETRY_LIMIT_EXCEEDED" in str(exc.value)


def test_reproduction_dir_layout(tmp_path: Path) -> None:
    from tools.arvp_vacation.sensitivity_campaign_state import fs_dirname_for_run_key

    d = reproduction_dir(tmp_path, "rk1", 1)
    assert d.parts[-3:] == (fs_dirname_for_run_key("rk1"), "reproduction", "1")
    env = reproduction_envelope_path(tmp_path, "rk1", 1)
    assert env.name == "run_envelope.json"
    assert env.parent == d
    res = reproduction_result_path(tmp_path, "rk1", 1)
    assert res.name == "result.json"
    cmp_path = reproduction_comparison_path(tmp_path, "rk1", 1)
    assert cmp_path.name == "comparison.json"


def test_write_comparison_evidence_writes_body(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=1)
    cmp_path = write_comparison_evidence(
        root,
        run_key="rk1",
        reproduction_attempt=1,
        comparison={
            "status": "PASS",
            "reason_code": "REPRODUCTION_RESULT_PASS",
            "compared_fields": ["gate_reason"],
        },
    )
    import json

    payload = json.loads(cmp_path.read_text(encoding="utf-8"))
    assert payload["run_key"] == "rk1"
    assert payload["reproduction_attempt"] == 1
    assert payload["comparison"]["status"] == "PASS"


def test_count_primary_succeeded_counts_only_bound_successes(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=2)
    commit_successful_result(
        root,
        run_key="rk1",
        bindings=BINDINGS,
        attempt=1,
        envelope={"run_key": "rk1"},
        result={"gate_reason": "OK", "trade_count": 0},
    )
    # rk2 is planned but not yet committed → count only counts rk1.
    n = count_primary_succeeded(
        root, bindings=BINDINGS, expected_run_keys=["rk1", "rk2"]
    )
    assert n == 1


def test_count_primary_succeeded_partial_blocks(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_run_envelope(
        root,
        run_key="rk1",
        bindings=BINDINGS,
        status="SUCCEEDED",
        attempt=1,
        envelope={"run_key": "rk1"},
        exit_code=0,
        result_fingerprint="d" * 64,
    )
    # No completion marker / result → treated as partial → fail-closed.
    with pytest.raises(SensitivityStateError) as exc:
        count_primary_succeeded(root, bindings=BINDINGS, expected_run_keys=["rk1"])
    assert "STATE_PARTIAL_SUCCESS_BLOCKED" in str(exc.value)


def test_fs_dirname_for_run_key_strips_windows_illegal_chars() -> None:
    from tools.arvp_vacation.sensitivity_campaign_state import (
        fs_dirname_for_run_key,
        run_key_needs_fs_mapping,
    )

    key = (
        "arvp-hh-hl-continuation-4374-prep-v1|binance_1m_month_2017_10|"
        "hh_hl_baseline_001|hh_hl_continuation_v1|ec40ba4f7fd61294"
    )
    assert run_key_needs_fs_mapping(key) is True
    dirname = fs_dirname_for_run_key(key)
    assert dirname.startswith("rk_")
    assert "|" not in dirname
    assert all(ch not in dirname for ch in '<>:"/\\|?*')
    # Deterministic
    assert fs_dirname_for_run_key(key) == dirname


def test_pipe_run_key_write_and_resume_roundtrip(tmp_path: Path) -> None:
    from tools.arvp_vacation.sensitivity_campaign_state import (
        LOGICAL_RUN_KEY_SIDECAR,
        fs_dirname_for_run_key,
        run_dir,
    )

    root = tmp_path / "ns"
    key = "camp|window|slot|strategy|deadbeef"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=1)
    envelope = {"run_key": key, "seed": "x"}
    commit_successful_result(
        root,
        run_key=key,
        bindings=BINDINGS,
        attempt=1,
        envelope=envelope,
        result={"gate_reason": "OK", "trade_count": 0},
    )
    run_path = run_dir(root, key)
    assert run_path.name == fs_dirname_for_run_key(key)
    assert "|" not in run_path.name
    sidecar = run_path / LOGICAL_RUN_KEY_SIDECAR
    assert sidecar.read_text(encoding="utf-8").strip() == key
    action = inspect_run_for_resume(
        root,
        run_key=key,
        bindings=BINDINGS,
        max_attempts=1,
        retry_failed=True,
    )
    assert action == "skip"
    # Logical key preserved in envelope payload
    env = (run_path / "run_envelope.json").read_text(encoding="utf-8")
    assert key in env


def test_legacy_raw_run_dir_still_readable(tmp_path: Path) -> None:
    """Pre-#4384 Linux trees used the raw run_key as the directory name."""
    from tools.arvp_vacation.sensitivity_campaign_state import run_dir

    root = tmp_path / "ns"
    legacy_key = "legacy_safe_key"
    legacy_dir = root / "runs" / legacy_key
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "run_envelope.json").write_text("{}", encoding="utf-8")
    assert run_dir(root, legacy_key) == legacy_dir
