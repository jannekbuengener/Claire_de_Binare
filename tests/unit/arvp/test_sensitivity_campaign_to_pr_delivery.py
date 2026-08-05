"""Delivery handoff + PR_READY verify tests (#4366 slice 2).

test_id: tc_sensitivity_campaign_to_pr_delivery_001
test_type: schutz|bauteil
cdb_area: arvp/validation-research
issue_ref: #4366
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.arvp_vacation.sensitivity_campaign_to_pr import (
    HANDOFF_READY,
    HOLD_BRANCH,
    HOLD_FP,
    HOLD_HEAD_PR,
    HOLD_PATHS,
    VERDICT_PR_READY,
    CampaignToPrError,
    prepare_delivery,
    verify_delivery,
)

pytestmark = [pytest.mark.unit]


def _write_slim(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    inv = {
        "schema_version": "cdb.sensitivity_campaign_primary_evidence_adoption.v1",
        "campaign_id": "arvp-sensitivity-4366-v1",
        "manifest_fingerprint": "a" * 64,
        "run_plan_fingerprint": "b" * 64,
        "authorization_fingerprint": "c" * 64,
        "bound_main_sha": "d" * 40,
        "bound_execution_sha": "d" * 40,
        "inventory_fingerprint": "e" * 64,
        "run_key_digest": "f" * 64,
        "allowed_evidence_namespace": "artifacts/arvp_sensitivity/demo",
        "lr_status": "NO-GO",
        "primary_verdict": "PRIMARY_EVIDENCE_COMPLETE",
    }
    (root / "primary_evidence_inventory.json").write_text(
        json.dumps(inv, indent=2) + "\n", encoding="utf-8"
    )
    analysis = root / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    (analysis / "classification_report.json").write_text(
        json.dumps(
            {
                "schema_version": "cdb.sensitivity_campaign_classification.v1",
                "classification": "INCONCLUSIVE",
                "lr_status": "NO-GO",
                "no_automatic_promotion": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (analysis / "analysis_envelope.json").write_text(
        json.dumps({"schema_version": "cdb.sensitivity_campaign_analysis.v1"}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    (root / "CLOSEOUT_CARD.md").write_text(
        "# Fixture\n\n- No Stage-B / Live / Echtgeld\n", encoding="utf-8"
    )


def test_prepare_delivery_emits_handoff(tmp_path: Path) -> None:
    root = tmp_path / "slim"
    _write_slim(root)
    out = tmp_path / "out"
    result = prepare_delivery(
        evidence_root=root,
        output_dir=out,
        issue_number=4366,
        commit_sha="a" * 40,
        output_rel="docs/evidence/arvp/campaign-to-pr/",
    )
    assert result["verdict"] == HANDOFF_READY
    handoff = result["handoff"]
    assert handoff["schema_version"].endswith("delivery_handoff.v1")
    assert "gh_pr_create" in handoff["forbidden_actions"]
    assert (out / "delivery_handoff.json").is_file()
    assert (out / "pr_body.md").is_file()


def test_verify_delivery_pr_ready(tmp_path: Path) -> None:
    root = tmp_path / "slim"
    _write_slim(root)
    out = tmp_path / "out"
    result = prepare_delivery(evidence_root=root, output_dir=out, issue_number=4366)
    handoff = result["handoff"]
    pkg_fp = handoff["slim_package"]["package_fingerprint"]
    paths = list(handoff["expected_package_relative_paths"])
    observed = {
        "branch_name": "batch/validation-research-issue-4366-pr-ready",
        "head_sha": "b" * 40,
        "pr_number": 9999,
        "pr_head_sha": "b" * 40,
        "pr_base": "main",
        "commit_paths": paths,
        "slim_package_fingerprint": pkg_fp,
    }
    verified = verify_delivery(
        handoff_path=out / "delivery_handoff.json", observed_facts=observed
    )
    assert verified["verdict"] == VERDICT_PR_READY


def test_verify_rejects_anti_repush_branch(tmp_path: Path) -> None:
    root = tmp_path / "slim"
    _write_slim(root)
    out = tmp_path / "out"
    result = prepare_delivery(evidence_root=root, output_dir=out)
    handoff = result["handoff"]
    observed = {
        "branch_name": "batch/validation-research-issue-4366",
        "head_sha": "b" * 40,
        "pr_number": 1,
        "pr_head_sha": "b" * 40,
        "pr_base": "main",
        "commit_paths": list(handoff["expected_package_relative_paths"]),
        "slim_package_fingerprint": handoff["slim_package"]["package_fingerprint"],
    }
    with pytest.raises(CampaignToPrError) as exc:
        verify_delivery(
            handoff_path=out / "delivery_handoff.json", observed_facts=observed
        )
    assert exc.value.reason_code == HOLD_BRANCH


def test_verify_rejects_head_pr_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "slim"
    _write_slim(root)
    out = tmp_path / "out"
    result = prepare_delivery(evidence_root=root, output_dir=out)
    handoff = result["handoff"]
    observed = {
        "branch_name": "batch/validation-research-issue-4366-pr-ready",
        "head_sha": "b" * 40,
        "pr_number": 1,
        "pr_head_sha": "c" * 40,
        "pr_base": "main",
        "commit_paths": list(handoff["expected_package_relative_paths"]),
        "slim_package_fingerprint": handoff["slim_package"]["package_fingerprint"],
    }
    with pytest.raises(CampaignToPrError) as exc:
        verify_delivery(
            handoff_path=out / "delivery_handoff.json", observed_facts=observed
        )
    assert exc.value.reason_code == HOLD_HEAD_PR


def test_verify_rejects_fingerprint_drift(tmp_path: Path) -> None:
    root = tmp_path / "slim"
    _write_slim(root)
    out = tmp_path / "out"
    result = prepare_delivery(evidence_root=root, output_dir=out)
    handoff = result["handoff"]
    observed = {
        "branch_name": "batch/validation-research-issue-4366-pr-ready",
        "head_sha": "b" * 40,
        "pr_number": 1,
        "pr_head_sha": "b" * 40,
        "pr_base": "main",
        "commit_paths": list(handoff["expected_package_relative_paths"]),
        "slim_package_fingerprint": "0" * 64,
    }
    with pytest.raises(CampaignToPrError) as exc:
        verify_delivery(
            handoff_path=out / "delivery_handoff.json", observed_facts=observed
        )
    assert exc.value.reason_code == HOLD_FP


def test_verify_rejects_missing_paths(tmp_path: Path) -> None:
    root = tmp_path / "slim"
    _write_slim(root)
    out = tmp_path / "out"
    result = prepare_delivery(evidence_root=root, output_dir=out)
    handoff = result["handoff"]
    observed = {
        "branch_name": "batch/validation-research-issue-4366-pr-ready",
        "head_sha": "b" * 40,
        "pr_number": 1,
        "pr_head_sha": "b" * 40,
        "pr_base": "main",
        "commit_paths": ["CLOSEOUT_CARD.md"],
        "slim_package_fingerprint": handoff["slim_package"]["package_fingerprint"],
    }
    with pytest.raises(CampaignToPrError) as exc:
        verify_delivery(
            handoff_path=out / "delivery_handoff.json", observed_facts=observed
        )
    assert exc.value.reason_code == HOLD_PATHS
