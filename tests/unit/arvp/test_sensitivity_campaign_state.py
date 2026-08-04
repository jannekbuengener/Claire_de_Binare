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
    CampaignBindings,
    SensitivityStateError,
    assert_namespace_startable,
    commit_successful_result,
    inspect_run_for_resume,
    write_campaign_envelope,
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
