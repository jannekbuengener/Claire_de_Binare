"""Primary evidence adoption unit tests (#4153).

test_id: tc_sensitivity_campaign_primary_adoption_001
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

from tools.arvp_vacation.sensitivity_campaign_primary_adoption import (
    ADOPT_WITH_RECORD,
    REPRO_MAY_RUN,
    VERDICT_BINDING,
    VERDICT_INCOMPLETE,
    VERDICT_PRIMARY_COMPLETE,
    SensitivityAdoptionError,
    adopt_primary_evidence,
    assert_adoption_inventory_allows_reproduction,
    build_primary_evidence_inventory,
    run_key_digest,
)
from tools.arvp_vacation.sensitivity_campaign_state import (
    CAMPAIGN_PHASE_PLANNED,
    CAMPAIGN_PHASE_PRIMARY_COMPLETE,
    CAMPAIGN_PHASE_PRIMARY_EVIDENCE_COMPLETE,
    CampaignBindings,
    commit_successful_result,
    read_campaign_phase,
    write_campaign_envelope,
)

BINDINGS = CampaignBindings(
    campaign_id="arvp-sensitivity-4153-v1",
    manifest_fingerprint="a" * 64,
    run_plan_fingerprint="b" * 64,
    authorization_fingerprint="c" * 64,
    execution_sha="d" * 40,
    main_sha="d" * 40,
)


def _seed_success(root: Path, run_key: str, trade_count: int = 1) -> None:
    commit_successful_result(
        root,
        run_key=run_key,
        bindings=BINDINGS,
        attempt=1,
        envelope={"run_key": run_key},
        result={"gate_reason": "OK", "trade_count": trade_count},
    )


def test_run_key_digest_order_independent() -> None:
    a = run_key_digest(["bb", "aa"])
    b = run_key_digest(["aa", "bb"])
    assert a == b
    assert len(a) == 64


def test_inventory_happy_path(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=2)
    keys = ["rk1", "rk2"]
    for k in keys:
        _seed_success(root, k)
    inv = build_primary_evidence_inventory(
        evidence_root=root,
        expected_run_keys=keys,
        bindings=BINDINGS,
        reproduction_code_sha="e" * 40,
    )
    assert inv["primary_verdict"] == VERDICT_PRIMARY_COMPLETE
    assert inv["adoption_verdict"] == ADOPT_WITH_RECORD
    assert inv["run_key_digest"] == run_key_digest(keys)


def test_inventory_detects_missing_key(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=2)
    _seed_success(root, "rk1")
    inv = build_primary_evidence_inventory(
        evidence_root=root,
        expected_run_keys=["rk1", "rk2"],
        bindings=BINDINGS,
        reproduction_code_sha="e" * 40,
    )
    assert inv["primary_verdict"] == VERDICT_INCOMPLETE


def test_inventory_detects_binding_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=1)
    _seed_success(root, "rk1")
    bad = CampaignBindings(
        campaign_id=BINDINGS.campaign_id,
        manifest_fingerprint="f" * 64,
        run_plan_fingerprint=BINDINGS.run_plan_fingerprint,
        authorization_fingerprint=BINDINGS.authorization_fingerprint,
        execution_sha=BINDINGS.execution_sha,
        main_sha=BINDINGS.main_sha,
    )
    inv = build_primary_evidence_inventory(
        evidence_root=root,
        expected_run_keys=["rk1"],
        bindings=bad,
        reproduction_code_sha="e" * 40,
    )
    assert inv["primary_verdict"] == VERDICT_BINDING


def test_adopt_promotes_to_primary_complete(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=2)
    keys = ["rk1", "rk2"]
    for k in keys:
        _seed_success(root, k)
    assert read_campaign_phase(root) == CAMPAIGN_PHASE_PLANNED
    result = adopt_primary_evidence(
        evidence_root=root,
        expected_run_keys=keys,
        bindings=BINDINGS,
        reproduction_code_sha="e" * 40,
        promote_to_primary_complete=True,
        power_off_recovery={"note": "test"},
    )
    assert result["status"] == "ADOPTED"
    assert result["campaign_phase"] == CAMPAIGN_PHASE_PRIMARY_COMPLETE
    assert result["adoption_verdict"] == REPRO_MAY_RUN
    assert_adoption_inventory_allows_reproduction(root, bindings=BINDINGS)


def test_adopt_can_stop_at_evidence_complete(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=1)
    _seed_success(root, "rk1")
    result = adopt_primary_evidence(
        evidence_root=root,
        expected_run_keys=["rk1"],
        bindings=BINDINGS,
        reproduction_code_sha="e" * 40,
        promote_to_primary_complete=False,
    )
    assert result["campaign_phase"] == CAMPAIGN_PHASE_PRIMARY_EVIDENCE_COMPLETE
    assert result["adoption_verdict"] == ADOPT_WITH_RECORD


def test_adopt_refuses_incomplete(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=2)
    _seed_success(root, "rk1")
    with pytest.raises(SensitivityAdoptionError) as exc:
        adopt_primary_evidence(
            evidence_root=root,
            expected_run_keys=["rk1", "rk2"],
            bindings=BINDINGS,
            reproduction_code_sha="e" * 40,
        )
    assert exc.value.reason_code == "ADOPT_PRIMARY_AUDIT_FAILED"
