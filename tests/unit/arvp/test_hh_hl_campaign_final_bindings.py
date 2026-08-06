"""Final-bindings hardening for PR #4378 / Issue #4374.

test_id: tc_hh_hl_campaign_final_bindings_001
test_type: Schutz-Test (negative / boundary)
cdb_area: arvp_campaign
issue_ref: #4374 / #4378
live_relevant: false

Covers:
* public ``--skip-live-git-gate`` removed from FINAL CLI surfaces
* test resolver injection only (no public skip path)
* PRE_FINAL / fixture surface receipts never Owner-GO-eligible
* exact surface↔final-plan binding mismatches
* physical local eligibility (disk / dataset root / content drift)
* positive post-merge surface receipt acceptance
* every negative path emits no GO package and never starts a replay
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from tools.arvp_vacation import hh_hl_campaign_execution_prep as cli
from tools.arvp_vacation import hh_hl_campaign_sha_gate as sha_gate
from tools.arvp_vacation.hh_hl_campaign_dataset import load_pass_receipt
from tools.arvp_vacation.hh_hl_campaign_design_authorization import (
    VERIFIED_DESIGN_GO_BOUND_MAIN_SHA,
    build_reference_design_receipt,
)
from tools.arvp_vacation.hh_hl_campaign_run_plan import build_hh_hl_final_run_plan
from tools.arvp_vacation.hh_hl_campaign_sha_gate import GitShaResolver
from tools.arvp_vacation.hh_hl_campaign_surface import (
    EXPECTED_RUN_COUNT,
    HOLD_DATASET_SURFACE_PROOF_REQUIRED,
    HOLD_RESOURCE_BUDGET_INVALID,
    HOLD_SURFACE_BINDING_MISMATCH,
    HOLD_SURFACE_DATASET_ROOT_REQUIRED,
    PhysicalDatasetProof,
    PROBE_CODE_SHA,
    assert_physical_local_eligibility,
    assert_surface_receipt_binds_final,
    build_surface_receipt,
    probe_hh_hl_surface,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = PROJECT_ROOT / "config" / "arvp" / "hh_hl_campaign_4374_v1.json"
DATASET_RECEIPT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "evidence"
    / "arvp_hh_hl_dataset_local_proof_receipt_4374.json"
)

BASE_SHA = VERIFIED_DESIGN_GO_BOUND_MAIN_SHA
POST_MERGE_SHA = "a" * 40
EXECUTION_SHA = "b" * 40
FOREIGN_SHA = "f" * 40
FAR_FUTURE = "2027-06-01T00:00:00Z"

# Design-GO-bound expected digest (must match the final manifest).
EXPECTED_DIGEST = "10f94c34e32db28a9393c38f944db4968b42e87d9ed223397e3637ff44323af9"


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _final_plan(planning_sha: str = POST_MERGE_SHA, *, pre_final: bool = False):
    return build_hh_hl_final_run_plan(
        final_manifest=_load_manifest(),
        design_receipt=build_reference_design_receipt(repo_root=PROJECT_ROOT),
        dataset_receipt=load_pass_receipt(DATASET_RECEIPT_PATH),
        planning_sha=planning_sha,
        pre_final=pre_final,
    )


def _fake_resolver(
    *,
    main_tip: str = POST_MERGE_SHA,
    extra_commits: tuple[str, ...] = (EXECUTION_SHA,),
) -> GitShaResolver:
    known = {main_tip: "commit", **{sha: "commit" for sha in extra_commits}}
    return GitShaResolver(
        fetch=lambda: None,
        resolve_main_tip=lambda: main_tip,
        object_type=lambda sha: known.get(sha),
        head=lambda: main_tip,
    )


@pytest.fixture(autouse=True)
def _clear_test_overrides():
    sha_gate._test_set_sha_resolver_override(None)
    cli._test_set_physical_proof_override(None)
    cli._test_set_free_disk_override(None)
    yield
    sha_gate._test_set_sha_resolver_override(None)
    cli._test_set_physical_proof_override(None)
    cli._test_set_free_disk_override(None)


def _bound_receipt(**over: Any) -> dict:
    """Owner-GO-eligible receipt bound to the FINAL plan for POST_MERGE_SHA."""
    plan = _final_plan(POST_MERGE_SHA)
    manifest = _load_manifest()
    binding = manifest["dataset_binding"]
    receipt = probe_hh_hl_surface(
        fixture=False,
        manifest_fingerprint=str(manifest["manifest_fingerprint"]),
        run_plan_fingerprint=plan.run_plan_fingerprint,
        planning_sha=POST_MERGE_SHA,
        dataset_selection_sha256=str(binding["selection_sha256"]),
        dataset_content_fingerprint_digest=str(binding["content_fingerprint_digest"]),
        run_plan_loadable=True,
        resource_budget=dict(manifest["resource_budget_contract"]),
        reachability={"single_run": True, "reproduction": True, "analyzer": True},
        free_disk_bytes=21474836480,
        physical_dataset_proof_passed=True,
    )
    receipt.update(over)
    return receipt


def _eligible_receipt_with(**fields: Any) -> dict:
    """Build a fingerprint-consistent eligible receipt with baked-in field overrides.

    Unlike ``_bound_receipt(**over)`` (post-fingerprint mutation), this recomputes
    the fingerprint so ``load_and_validate_surface_receipt`` accepts the receipt
    and only the final-plan binding check fails.
    """
    plan = _final_plan(POST_MERGE_SHA)
    manifest = _load_manifest()
    binding = manifest["dataset_binding"]
    kwargs = {
        "fixture": False,
        "manifest_fingerprint": str(manifest["manifest_fingerprint"]),
        "run_plan_fingerprint": plan.run_plan_fingerprint,
        "planning_sha": POST_MERGE_SHA,
        "dataset_selection_sha256": str(binding["selection_sha256"]),
        "dataset_content_fingerprint_digest": str(
            binding["content_fingerprint_digest"]
        ),
        "run_plan_loadable": True,
        "resource_budget": dict(manifest["resource_budget_contract"]),
        "reachability": {
            "single_run": True,
            "reproduction": True,
            "analyzer": True,
        },
        "free_disk_bytes": 21474836480,
        "physical_dataset_proof_passed": True,
    }
    kwargs.update(fields)
    return probe_hh_hl_surface(**kwargs)


def _capture(capsys) -> dict:
    out = capsys.readouterr().out.strip()
    return json.loads(out)


def _pass_physical_proof(
    *,
    digest: str = EXPECTED_DIGEST,
    window_count: int = EXPECTED_RUN_COUNT,
) -> PhysicalDatasetProof:
    return PhysicalDatasetProof(
        passed=True,
        content_fingerprint_digest=digest,
        window_count=window_count,
        free_disk_bytes=21474836480,
    )


# --------------------------------------------------------------------------- #
# 1) Public skip-gate removed; injection-only resolver
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_public_skip_live_git_gate_flag_absent_from_cli():
    parser = cli.build_parser()
    assert "--skip-live-git-gate" not in parser.format_help()
    for argv in (
        ["finalize-plan", "--skip-live-git-gate"],
        ["prepare-execution-go", "--skip-live-git-gate"],
        ["probe-surface", "--skip-live-git-gate"],
    ):
        with pytest.raises(SystemExit):
            parser.parse_args(argv)


@pytest.mark.unit
def test_public_probe_surface_run_plan_fingerprint_override_absent():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(
            ["probe-surface", "--run-plan-fingerprint", "e" * 64]
        )


@pytest.mark.unit
def test_test_resolver_injection_only_no_cli_bypass(capsys):
    # Without injection, FINAL finalize-plan cannot invent a skip path; a
    # remnant attribute raises HOLD_EXECUTION_SHA_GATE_BYPASS.
    args = argparse.Namespace(
        repo_root=str(PROJECT_ROOT),
        planning_sha=POST_MERGE_SHA,
        pre_final=False,
        skip_live_git_gate=True,
        manifest=None,
        dataset_receipt=None,
        design_go_fixture_json=None,
        design_go_comment_id=None,
        live=False,
        repository=None,
        issue=None,
        out=None,
    )
    with pytest.raises(sha_gate.HhHlShaGateError) as exc:
        cli._assert_no_skip_gate_remnant(args)
    assert exc.value.reason_code == "HOLD_EXECUTION_SHA_GATE_BYPASS"

    # Direct private injection lets offline tests pass the always-on gate.
    sha_gate._test_set_sha_resolver_override(_fake_resolver())
    rc = cli.main(
        [
            "--repo-root",
            str(PROJECT_ROOT),
            "finalize-plan",
            "--planning-sha",
            POST_MERGE_SHA,
        ]
    )
    out = _capture(capsys)
    assert rc == 0
    assert out["status"] == "FINAL"


# --------------------------------------------------------------------------- #
# 2) PRE_FINAL / fixture never Owner-GO-eligible
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_pre_final_surface_receipt_not_owner_go_eligible():
    plan = _final_plan(POST_MERGE_SHA, pre_final=True)
    manifest = _load_manifest()
    binding = manifest["dataset_binding"]
    receipt = probe_hh_hl_surface(
        fixture=False,
        pre_final=True,
        manifest_fingerprint=str(manifest["manifest_fingerprint"]),
        run_plan_fingerprint=plan.run_plan_fingerprint,
        planning_sha=POST_MERGE_SHA,
        dataset_selection_sha256=str(binding["selection_sha256"]),
        dataset_content_fingerprint_digest=str(binding["content_fingerprint_digest"]),
        run_plan_loadable=True,
        resource_budget=dict(manifest["resource_budget_contract"]),
        reachability={"single_run": True, "reproduction": True, "analyzer": True},
        free_disk_bytes=21474836480,
        physical_dataset_proof_passed=True,
    )
    assert receipt["owner_go_package_eligible"] is False


@pytest.mark.unit
def test_fixture_probe_cli_never_owner_go_eligible(capsys):
    rc = cli.main(["--repo-root", str(PROJECT_ROOT), "probe-surface", "--fixture"])
    out = _capture(capsys)
    assert rc == 0
    assert out["fixture"] is True
    assert out["owner_go_package_eligible"] is False
    assert out["replays"] is False


# --------------------------------------------------------------------------- #
# 3) Exact binding mismatches → HOLD_EXECUTION_SURFACE_BINDING_MISMATCH
# --------------------------------------------------------------------------- #
@pytest.mark.unit
@pytest.mark.parametrize(
    "field,value",
    [
        ("planning_sha", FOREIGN_SHA),
        ("manifest_fingerprint", "e" * 64),
        ("run_plan_fingerprint", "e" * 64),
        ("dataset_selection_sha256", "e" * 64),
        ("dataset_content_fingerprint_digest", "e" * 64),
        (
            "resource_budget",
            {
                "max_parallelism": 99,
                "max_in_flight_runs": 1,
                "max_attempts_per_run": 1,
                "max_run_wall_time_seconds": 3600,
                "max_campaign_wall_time_seconds": 172800,
                "max_artifact_bytes": 21474836480,
                "minimum_free_disk_bytes": 21474836480,
                "max_consecutive_failures": 3,
                "max_total_failures": 5,
                "log_retention_days": 30,
            },
        ),
    ],
)
def test_foreign_binding_field_blocks_prepare_go(tmp_path: Path, capsys, field, value):
    replay = MagicMock()
    receipt = _eligible_receipt_with(**{field: value})
    path = tmp_path / "surface.json"
    path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    sha_gate._test_set_sha_resolver_override(_fake_resolver())
    rc = cli.main(
        [
            "--repo-root",
            str(PROJECT_ROOT),
            "prepare-execution-go",
            "--planning-sha",
            POST_MERGE_SHA,
            "--execution-sha",
            EXECUTION_SHA,
            "--surface-receipt",
            str(path),
            "--expires-at-utc",
            FAR_FUTURE,
        ]
    )
    out = _capture(capsys)
    assert rc == 1
    assert out["reason_code"] == HOLD_SURFACE_BINDING_MISMATCH
    assert "execution_go_payload" not in out
    assert out.get("ready_for_owner_execution_go") is not True
    replay.assert_not_called()


@pytest.mark.unit
def test_manipulated_probe_code_sha_blocks(tmp_path: Path, capsys):
    # Fingerprint-consistent receipt with a foreign probe_code_sha: rejected
    # before / at package assembly (load or binding). Never yields a GO package.
    plan = _final_plan(POST_MERGE_SHA)
    manifest = _load_manifest()
    binding = manifest["dataset_binding"]
    receipt = build_surface_receipt(
        execution_surface_id="services.validation.strategy_replay_runner.single_run",
        planning_sha=POST_MERGE_SHA,
        manifest_fingerprint=str(manifest["manifest_fingerprint"]),
        run_plan_fingerprint=plan.run_plan_fingerprint,
        dataset_selection_sha256=str(binding["selection_sha256"]),
        dataset_content_fingerprint_digest=str(binding["content_fingerprint_digest"]),
        run_plan_loadable=True,
        single_run_provider_reachable=True,
        reproduction_provider_reachable=True,
        analyzer_provider_reachable=True,
        resource_budget=dict(manifest["resource_budget_contract"]),
        free_disk_bytes=21474836480,
        fixture=False,
        physical_dataset_proof_passed=True,
        probe_code_sha="0" * 64,
    )
    path = tmp_path / "surface.json"
    path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    sha_gate._test_set_sha_resolver_override(_fake_resolver())
    rc = cli.main(
        [
            "--repo-root",
            str(PROJECT_ROOT),
            "prepare-execution-go",
            "--planning-sha",
            POST_MERGE_SHA,
            "--execution-sha",
            EXECUTION_SHA,
            "--surface-receipt",
            str(path),
            "--expires-at-utc",
            FAR_FUTURE,
        ]
    )
    out = _capture(capsys)
    assert rc == 1
    assert out.get("ready_for_owner_execution_go") is not True
    assert "execution_go_payload" not in out
    # Either load-time probe check or exact binding mismatch.
    assert out["reason_code"] in {
        HOLD_SURFACE_BINDING_MISMATCH,
        "HOLD_EXECUTION_SURFACE_RECEIPT_INVALID",
        "HOLD_EXECUTION_SURFACE_PROOF_REQUIRED",
        "HOLD_SURFACE_RECEIPT_PROBE_CODE_MISMATCH",
    }


@pytest.mark.unit
def test_assert_surface_receipt_binds_final_rejects_foreign_planning_sha():
    plan = _final_plan(POST_MERGE_SHA)
    manifest = _load_manifest()
    receipt = _eligible_receipt_with(planning_sha=FOREIGN_SHA)
    with pytest.raises(Exception, match=HOLD_SURFACE_BINDING_MISMATCH) as exc:
        assert_surface_receipt_binds_final(
            receipt,
            planning_sha=POST_MERGE_SHA,
            manifest=manifest,
            plan=plan,
        )
    assert getattr(exc.value, "reason_code", "") == HOLD_SURFACE_BINDING_MISMATCH


# --------------------------------------------------------------------------- #
# 4) Physical local eligibility
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_physical_insufficient_free_disk_blocks():
    with pytest.raises(Exception) as exc:
        assert_physical_local_eligibility(
            dataset_root=None,
            expected_content_digest=EXPECTED_DIGEST,
            resource_budget=_load_manifest()["resource_budget_contract"],
            free_disk_bytes=1,
            physical_proof_fn=lambda: _pass_physical_proof(),
        )
    assert getattr(exc.value, "reason_code", "") == HOLD_RESOURCE_BUDGET_INVALID


@pytest.mark.unit
def test_physical_missing_dataset_root_blocks():
    with pytest.raises(Exception) as exc:
        assert_physical_local_eligibility(
            dataset_root=None,
            expected_content_digest=EXPECTED_DIGEST,
            resource_budget=_load_manifest()["resource_budget_contract"],
            free_disk_bytes=21474836480,
            physical_proof_fn=None,
        )
    assert getattr(exc.value, "reason_code", "") == HOLD_SURFACE_DATASET_ROOT_REQUIRED


@pytest.mark.unit
def test_physical_dataset_content_drift_blocks():
    with pytest.raises(Exception) as exc:
        assert_physical_local_eligibility(
            dataset_root=None,
            expected_content_digest=EXPECTED_DIGEST,
            resource_budget=_load_manifest()["resource_budget_contract"],
            free_disk_bytes=21474836480,
            physical_proof_fn=lambda: _pass_physical_proof(digest="0" * 64),
        )
    assert getattr(exc.value, "reason_code", "") == HOLD_DATASET_SURFACE_PROOF_REQUIRED


@pytest.mark.unit
def test_probe_surface_non_fixture_physical_failures_emit_no_replay(capsys):
    sha_gate._test_set_sha_resolver_override(_fake_resolver())
    cli._test_set_free_disk_override(1)  # below budget
    cli._test_set_physical_proof_override(lambda: _pass_physical_proof())
    rc = cli.main(
        [
            "--repo-root",
            str(PROJECT_ROOT),
            "probe-surface",
            "--planning-sha",
            POST_MERGE_SHA,
        ]
    )
    out = _capture(capsys)
    assert rc == 1
    assert out["reason_code"] == HOLD_RESOURCE_BUDGET_INVALID
    assert out["replays"] is False
    assert out.get("owner_go_package_eligible") is not True


# --------------------------------------------------------------------------- #
# 5) Positive: full post-merge surface receipt accepted
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_full_post_merge_surface_receipt_accepted_for_prepare_go(
    tmp_path: Path, capsys
):
    path = tmp_path / "surface.json"
    path.write_text(json.dumps(_bound_receipt(), sort_keys=True), encoding="utf-8")
    sha_gate._test_set_sha_resolver_override(_fake_resolver())
    rc = cli.main(
        [
            "--repo-root",
            str(PROJECT_ROOT),
            "prepare-execution-go",
            "--planning-sha",
            POST_MERGE_SHA,
            "--execution-sha",
            EXECUTION_SHA,
            "--surface-receipt",
            str(path),
            "--expires-at-utc",
            FAR_FUTURE,
        ]
    )
    out = _capture(capsys)
    assert rc == 0
    assert out["ready_for_owner_execution_go"] is True
    assert out["campaign_execution_authorized"] is False
    assert out["github_comment_id"] is None
    payload = out["execution_go_payload"]
    assert payload["expected_run_count"] == 39
    assert out["replays"] is False
    # Receipt that backed the package carries the canonical probe contract.
    assert _bound_receipt()["probe_code_sha"] == PROBE_CODE_SHA


@pytest.mark.unit
def test_probe_surface_non_fixture_eligible_with_injected_physical_proof(capsys):
    sha_gate._test_set_sha_resolver_override(_fake_resolver())
    cli._test_set_free_disk_override(21474836480)
    cli._test_set_physical_proof_override(lambda: _pass_physical_proof())
    rc = cli.main(
        [
            "--repo-root",
            str(PROJECT_ROOT),
            "probe-surface",
            "--planning-sha",
            POST_MERGE_SHA,
        ]
    )
    out = _capture(capsys)
    assert rc == 0
    assert out["owner_go_package_eligible"] is True
    assert out["fixture"] is False
    assert out["replays"] is False
    assert EXPECTED_DIGEST == cli.EXPECTED_DATASET_CONTENT_DIGEST
