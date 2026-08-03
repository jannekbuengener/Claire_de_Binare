"""Fail-closed readiness preflight tests for #4153.

test_id: tc_sensitivity_preflight_001
test_type: schutz
cdb_area: arvp/validation-research
issue_ref: #4153
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tools.arvp_vacation.batch_a_gate_common import (
    STAGE_A_GATE_CONTRACT_PATH,
    compute_gate_contract_sha256,
    load_json_contract,
)
from tools.arvp_vacation.sensitivity_campaign_preflight import (
    VERDICT_BLOCKED,
    VERDICT_FROZEN,
    VERDICT_HOLDOUT,
    VERDICT_INVALID,
    VERDICT_READY,
    EffectiveConfigCapability,
    discover_effective_config_capability,
    main,
    run_manifest_preflight,
    run_repo_preflight,
    validate_effective_config_snapshot_structure,
)
from tools.arvp_vacation.sensitivity_experiment_manifest import load_manifest
from tools.market_data.development_window_selector import (
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
)

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "arvp" / "sensitivity"
VALID_MANIFEST = FIXTURE_DIR / "experiment_manifest_valid_v1.json"
COMPLETE_EFC = FIXTURE_DIR / "effective_config_snapshot_complete.json"
SUPERFICIAL_EFC = FIXTURE_DIR / "effective_config_snapshot_superficial.json"
REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture()
def valid_manifest() -> dict:
    return load_manifest(VALID_MANIFEST)


@pytest.fixture()
def complete_efc() -> dict:
    return json.loads(COMPLETE_EFC.read_text(encoding="utf-8"))


@pytest.fixture()
def synthetic_capability() -> EffectiveConfigCapability:
    return EffectiveConfigCapability(
        available=True,
        detail="synthetic test capability",
        validate_snapshot=validate_effective_config_snapshot_structure,
    )


def test_repo_preflight_ready_with_effective_config() -> None:
    """After #4151 Effective-Config capability, repo preflight must be READY."""
    report = run_repo_preflight(REPO_ROOT)
    assert report["verdict"] == VERDICT_READY
    assert report["gates"]["effective_config"]["status"] == "PASS"
    assert report["lr_status"] == "NO-GO"
    assert report["evidence"]["effective_config_capability_available"] is True
    assert report["evidence"]["effective_config_snapshot_fingerprint"]
    cap = discover_effective_config_capability(REPO_ROOT)
    assert cap.available is True


def test_synthetic_ready_with_injected_capability(
    valid_manifest: dict,
    complete_efc: dict,
    synthetic_capability: EffectiveConfigCapability,
) -> None:
    report = run_manifest_preflight(
        valid_manifest,
        REPO_ROOT,
        capability=synthetic_capability,
        effective_config_snapshot=complete_efc,
    )
    assert report["verdict"] == VERDICT_READY
    assert report["manifest_fingerprint"]
    assert all(g["status"] == "PASS" for g in report["gates"].values())


def test_missing_effective_config_fingerprint_blocked(valid_manifest: dict) -> None:
    bad = copy.deepcopy(valid_manifest)
    bad["effective_config_snapshot_fingerprint"] = ""
    # empty fails schema first
    report = run_manifest_preflight(bad, REPO_ROOT)
    assert report["verdict"] in {VERDICT_INVALID, VERDICT_BLOCKED}


def test_missing_efc_fingerprint_key_invalid(valid_manifest: dict) -> None:
    bad = copy.deepcopy(valid_manifest)
    del bad["effective_config_snapshot_fingerprint"]
    report = run_manifest_preflight(bad, REPO_ROOT)
    assert report["verdict"] == VERDICT_INVALID


def test_superficial_config_snapshot_blocked(
    valid_manifest: dict,
    synthetic_capability: EffectiveConfigCapability,
) -> None:
    superficial = json.loads(SUPERFICIAL_EFC.read_text(encoding="utf-8"))
    report = run_manifest_preflight(
        valid_manifest,
        REPO_ROOT,
        capability=synthetic_capability,
        effective_config_snapshot=superficial,
    )
    assert report["verdict"] == VERDICT_BLOCKED
    assert report["gates"]["effective_config"]["status"] == "BLOCKED"
    assert "superficial" in report["gates"]["effective_config"]["detail"].lower() or (
        "incomplete" in report["gates"]["effective_config"]["detail"].lower()
        or "rejected" in report["gates"]["effective_config"]["detail"].lower()
    )


def test_missing_content_fingerprint_blocked(valid_manifest: dict) -> None:
    bad = copy.deepcopy(valid_manifest)
    del bad["dataset_identity"]["content_fingerprint"]
    report = run_manifest_preflight(bad, REPO_ROOT)
    assert report["verdict"] == VERDICT_INVALID


def test_request_hash_as_content_hash_blocked(valid_manifest: dict) -> None:
    bad = copy.deepcopy(valid_manifest)
    req = bad["dataset_identity"]["request_fingerprint"]
    bad["dataset_identity"]["content_fingerprint"] = req
    report = run_manifest_preflight(bad, REPO_ROOT)
    assert report["verdict"] == VERDICT_BLOCKED
    assert "request_as_content_fingerprint" in report["blocking_reasons"]


def test_manipulated_policy_fingerprint_blocked(valid_manifest: dict) -> None:
    bad = copy.deepcopy(valid_manifest)
    bad["parameter_control"]["register_fingerprint"] = "0" * 64
    report = run_manifest_preflight(bad, REPO_ROOT)
    assert report["verdict"] == VERDICT_BLOCKED
    assert "parameter_control_fingerprint_mismatch" in report["blocking_reasons"]


def test_changed_stage_a_gate_fingerprint_frozen(
    valid_manifest: dict,
    complete_efc: dict,
    synthetic_capability: EffectiveConfigCapability,
) -> None:
    bad = copy.deepcopy(valid_manifest)
    bad["frozen_boundaries"]["stage_a_gate_contract_sha256"] = "a" * 64
    report = run_manifest_preflight(
        bad,
        REPO_ROOT,
        capability=synthetic_capability,
        effective_config_snapshot=complete_efc,
    )
    assert report["verdict"] == VERDICT_FROZEN


def test_risk_family_in_parameter_space_frozen(valid_manifest: dict) -> None:
    bad = copy.deepcopy(valid_manifest)
    bad["parameter_families"].append(
        {
            "family_id": "kill_switch_threshold",
            "parameter_ids": ["CDB-002"],
            "value_range": {"min": 0, "max": 1},
            "step": 1,
            "change_authority": "RESEARCH_ALLOWED",
        }
    )
    report = run_manifest_preflight(bad, REPO_ROOT)
    assert report["verdict"] == VERDICT_FROZEN


def test_oos_windows_holdout_blocked(valid_manifest: dict) -> None:
    bad = copy.deepcopy(valid_manifest)
    bad["oos_windows"] = ["binance_1m_month_2023_01"]
    report = run_manifest_preflight(bad, REPO_ROOT)
    assert report["verdict"] == VERDICT_HOLDOUT


def test_stress_window_in_set_holdout_blocked(valid_manifest: dict) -> None:
    bad = copy.deepcopy(valid_manifest)
    windows = list(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS)
    windows[-1] = "binance_1m_month_2099_01"
    bad["development_windows"]["window_ids"] = windows
    report = run_manifest_preflight(bad, REPO_ROOT)
    assert report["verdict"] == VERDICT_HOLDOUT


def test_unknown_parameter_rule_blocked(valid_manifest: dict) -> None:
    bad = copy.deepcopy(valid_manifest)
    bad["parameter_families"][0]["parameter_ids"] = ["CDB-999"]
    report = run_manifest_preflight(bad, REPO_ROOT)
    assert report["verdict"] == VERDICT_BLOCKED
    assert "unknown_parameter_rule" in report["blocking_reasons"]


def test_forbidden_parameter_authority_blocked(valid_manifest: dict) -> None:
    """CDB-004 is FROZEN_UNTIL_CONTRACT — not allowed for research tuning."""
    bad = copy.deepcopy(valid_manifest)
    bad["parameter_families"][0]["parameter_ids"] = ["CDB-004"]
    report = run_manifest_preflight(bad, REPO_ROOT)
    assert report["verdict"] == VERDICT_BLOCKED
    assert "parameter_authority_denied" in report["blocking_reasons"]


def test_missing_stale_contradictory_evidence_blocked(
    valid_manifest: dict,
) -> None:
    # Missing EFC capability + contradictory economics version
    bad = copy.deepcopy(valid_manifest)
    bad["execution_economics_contract_version"] = "execution_economics_gross_to_net.v0"
    # schema rejects wrong const
    report = run_manifest_preflight(bad, REPO_ROOT)
    assert report["verdict"] in {VERDICT_INVALID, VERDICT_BLOCKED}


def test_stage_a_gate_fingerprint_regression_stable() -> None:
    contract = load_json_contract(STAGE_A_GATE_CONTRACT_PATH)
    fp = compute_gate_contract_sha256(contract)
    assert fp == "714b183b8219eb07050d99dab1caaa65797142d2671c1128f2036ac7213bdefc"


def test_cli_repo_preflight_exits_ready() -> None:
    rc = main(["--repo-root", str(REPO_ROOT)])
    assert rc == 0


def test_no_secrets_in_readiness_report(valid_manifest: dict) -> None:
    report = run_manifest_preflight(valid_manifest, REPO_ROOT)
    blob = json.dumps(report)
    for token in ("api_key", "password", "REDIS_PASSWORD", "Documents/.secrets"):
        assert token not in blob
