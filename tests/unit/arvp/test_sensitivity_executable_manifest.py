"""Executable campaign manifest contract tests (#4153).

test_id: tc_sensitivity_executable_manifest_001
test_type: schutz|bauteil
cdb_area: arvp/validation-research
issue_ref: #4153
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from tools.arvp_vacation.sensitivity_campaign_grid import (
    EXPECTED_RUN_COUNT,
    EXPECTED_UNIQUE_VARIANTS,
    OWNER_RATIFICATION_COMMENT_ID,
    variant_breakdown,
)
from tools.arvp_vacation.sensitivity_campaign_preflight import (
    VERDICT_BLOCKED,
    VERDICT_READY,
    VERDICT_READY_CAMPAIGN,
    main,
    run_manifest_preflight,
    run_repo_preflight,
)
from tools.arvp_vacation.sensitivity_experiment_manifest import (
    MANIFEST_SCHEMA_VERSION_V11,
    SensitivityManifestError,
    attach_fingerprint,
    fingerprint_manifest,
    load_manifest,
    validate_manifest,
    validate_manifest_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_MANIFEST = REPO_ROOT / "config" / "arvp" / "sensitivity_campaign_4153_v1.json"
FIXTURE_MANIFEST = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "arvp"
    / "sensitivity"
    / "experiment_manifest_valid_v1.json"
)


@pytest.fixture()
def executable_manifest() -> dict:
    return load_manifest(CANONICAL_MANIFEST)


def test_v1_fixture_still_valid_and_non_executable() -> None:
    fixture = load_manifest(FIXTURE_MANIFEST)
    validate_manifest_schema(fixture)
    assert fixture["executable"] is False
    assert fixture["schema_version"] == "cdb.sensitivity_experiment_manifest.v1"


def test_canonical_executable_manifest_valid(executable_manifest: dict) -> None:
    validate_manifest(executable_manifest)
    assert executable_manifest["schema_version"] == MANIFEST_SCHEMA_VERSION_V11
    assert executable_manifest["executable"] is True
    assert executable_manifest["execution_mode"] == "replay_only"
    assert executable_manifest["strategies"] == ["primary_breakout_v1"]
    assert executable_manifest["parameter_grid"]["cdb_021"] == "OUT"
    assert (
        executable_manifest["owner_ratification"]["issue_comment_id"]
        == OWNER_RATIFICATION_COMMENT_ID
    )
    assert executable_manifest["expansion"]["expected_run_count"] == EXPECTED_RUN_COUNT
    assert executable_manifest["expansion"]["unique_variant_count"] == (
        EXPECTED_UNIQUE_VARIANTS
    )
    assert len(executable_manifest["window_bindings"]) == 39


def test_executable_missing_required_field_invalid(executable_manifest: dict) -> None:
    bad = copy.deepcopy(executable_manifest)
    del bad["expansion"]
    with pytest.raises(SensitivityManifestError):
        validate_manifest_schema(bad)


def test_executable_wrong_counts_invalid(executable_manifest: dict) -> None:
    bad = copy.deepcopy(executable_manifest)
    bad["expansion"]["expected_run_count"] = 820
    bad.pop("manifest_fingerprint", None)
    bad = attach_fingerprint(bad)
    with pytest.raises(SensitivityManifestError):
        validate_manifest(bad)


def test_executable_paper_boundary_invalid(executable_manifest: dict) -> None:
    bad = copy.deepcopy(executable_manifest)
    bad["explicit_bans"]["paper"] = False
    bad.pop("manifest_fingerprint", None)
    bad = attach_fingerprint(bad)
    with pytest.raises(SensitivityManifestError):
        validate_manifest(bad)


def test_fingerprint_stable_and_semantic(executable_manifest: dict) -> None:
    body = copy.deepcopy(executable_manifest)
    body.pop("manifest_fingerprint", None)
    a = fingerprint_manifest(body)
    b = fingerprint_manifest(copy.deepcopy(body))
    assert a == b
    changed = copy.deepcopy(body)
    changed["campaign_version"] = "4153.v1-changed"
    assert fingerprint_manifest(changed) != a
    # Non-semantic: re-embedding fingerprint must not alter body hash.
    attached = attach_fingerprint(body)
    assert attached["manifest_fingerprint"] == a


def test_repo_preflight_ready_without_manifest() -> None:
    report = run_repo_preflight(REPO_ROOT)
    assert report["verdict"] == VERDICT_READY


def test_fixture_manifest_blocked_for_stale_efc() -> None:
    fixture = load_manifest(FIXTURE_MANIFEST)
    report = run_manifest_preflight(fixture, REPO_ROOT)
    assert report["verdict"] == VERDICT_BLOCKED
    assert "effective_config_fingerprint_mismatch" in report["blocking_reasons"]


def test_canonical_manifest_preflight_campaign_ready(
    executable_manifest: dict,
) -> None:
    report = run_manifest_preflight(executable_manifest, REPO_ROOT)
    assert report["verdict"] == VERDICT_READY_CAMPAIGN
    assert report["gates"]["run_expansion"]["status"] == "PASS"
    assert report["gates"]["ratified_grid"]["status"] == "PASS"
    assert report["gates"]["manifest_fingerprint"]["status"] == "PASS"
    assert report["lr_status"] == "NO-GO"
    # No campaign execution side effects: expansion is pure.
    assert variant_breakdown()["unique_total"] == 21


def test_tampered_fingerprint_blocked(executable_manifest: dict) -> None:
    bad = copy.deepcopy(executable_manifest)
    bad["manifest_fingerprint"] = "0" * 64
    report = run_manifest_preflight(bad, REPO_ROOT)
    assert report["verdict"] == VERDICT_BLOCKED
    assert "manifest_fingerprint_mismatch" in report["blocking_reasons"]


def test_cli_manifest_exit_zero_for_campaign_ready() -> None:
    code = main(["--manifest", str(CANONICAL_MANIFEST)])
    assert code == 0


def test_cli_repo_exit_zero() -> None:
    assert main([]) == 0
