"""Campaign-to-PR Orchestrator v1 unit tests (#4366).

test_id: tc_sensitivity_campaign_to_pr_001
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

from tools.arvp_vacation.sensitivity_campaign_state import (
    CAMPAIGN_PHASE_COMPLETED,
    CAMPAIGN_PHASE_PRIMARY_COMPLETE,
    CampaignBindings,
    write_campaign_envelope,
)
from tools.arvp_vacation.sensitivity_campaign_to_pr import (
    HOLD_BINDING,
    HOLD_PHASE,
    HOLD_RAW,
    VERDICT_DRY_RUN_PASS,
    VERDICT_PREPARE_PASS,
    BindingPins,
    CampaignToPrError,
    assert_no_raw_run_staging,
    build_batch_pr_body,
    main,
    run_orchestrator,
)
from tools.pr_routing.engine import parse_batch_pr_body

pytestmark = [pytest.mark.unit]


BINDINGS = CampaignBindings(
    campaign_id="arvp-sensitivity-4366-v1",
    manifest_fingerprint="a" * 64,
    run_plan_fingerprint="b" * 64,
    authorization_fingerprint="c" * 64,
    execution_sha="d" * 40,
    main_sha="d" * 40,
)


def _write_slim(root: Path, *, abs_ns: bool = False) -> None:
    root.mkdir(parents=True, exist_ok=True)
    ns = (
        r"D:\Dev\Workspaces\Repos\artifacts\arvp_sensitivity\demo"
        if abs_ns
        else "artifacts/arvp_sensitivity/demo"
    )
    inv = {
        "schema_version": "cdb.sensitivity_campaign_primary_evidence_adoption.v1",
        "campaign_id": BINDINGS.campaign_id,
        "manifest_fingerprint": BINDINGS.manifest_fingerprint,
        "run_plan_fingerprint": BINDINGS.run_plan_fingerprint,
        "authorization_fingerprint": BINDINGS.authorization_fingerprint,
        "bound_main_sha": BINDINGS.main_sha,
        "bound_execution_sha": BINDINGS.execution_sha,
        "inventory_fingerprint": "e" * 64,
        "run_key_digest": "f" * 64,
        "allowed_evidence_namespace": ns,
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
                "reasons": ["fixture"],
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
        "# Fixture closeout\n\n- No Stage-B / Live / Echtgeld\n", encoding="utf-8"
    )


def test_dry_run_slim_closeout_pass(tmp_path: Path) -> None:
    root = tmp_path / "slim"
    _write_slim(root)
    report = run_orchestrator(evidence_root=root, mode="dry-run")
    assert report["verdict"] == VERDICT_DRY_RUN_PASS
    assert report["source_mode"] == "slim_closeout"
    assert report["classification"] == "INCONCLUSIVE"


def test_hold_phase_when_incomplete_namespace(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=1)
    from tools.arvp_vacation.sensitivity_campaign_state import (
        CAMPAIGN_ENVELOPE_NAME,
        atomic_write_json,
        read_json,
    )

    env_path = root / CAMPAIGN_ENVELOPE_NAME
    env = read_json(env_path)
    env["campaign_phase"] = CAMPAIGN_PHASE_PRIMARY_COMPLETE
    atomic_write_json(env_path, env)
    with pytest.raises(CampaignToPrError) as exc:
        run_orchestrator(evidence_root=root, mode="dry-run")
    assert exc.value.reason_code == HOLD_PHASE


def test_hold_binding_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "slim"
    _write_slim(root)
    with pytest.raises(CampaignToPrError) as exc:
        run_orchestrator(
            evidence_root=root,
            mode="dry-run",
            pins=BindingPins(manifest_fingerprint="0" * 64),
        )
    assert exc.value.reason_code == HOLD_BINDING


def test_prepare_rejects_raw_runs_in_output_candidates(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    _write_slim(root)
    (root / "runs" / "rk1").mkdir(parents=True)
    with pytest.raises(CampaignToPrError) as exc:
        run_orchestrator(evidence_root=root, mode="dry-run")
    assert exc.value.reason_code == HOLD_PHASE


def test_assert_no_raw_run_staging() -> None:
    with pytest.raises(CampaignToPrError) as exc:
        assert_no_raw_run_staging(["analysis/x.json", "runs/rk1/result.json"])
    assert exc.value.reason_code == HOLD_RAW


def test_prepare_pass_redacts_absolute_namespace(tmp_path: Path) -> None:
    root = tmp_path / "slim"
    _write_slim(root, abs_ns=True)
    out = tmp_path / "out"
    report = run_orchestrator(
        evidence_root=root,
        mode="prepare-pr-inputs",
        output_dir=out,
        issue_number=4366,
        commit_sha="a" * 40,
    )
    assert report["verdict"] == VERDICT_PREPARE_PASS
    inv = json.loads(
        (out / "primary_evidence_inventory.json").read_text(encoding="utf-8")
    )
    assert inv["allowed_evidence_namespace"].startswith("artifacts/")
    assert "D:" not in inv["allowed_evidence_namespace"]
    assert not (out / "runs").exists()
    body = (out / "pr_body.md").read_text(encoding="utf-8")
    meta = parse_batch_pr_body(body)
    assert meta.planned_issues == (4366,)
    assert 4366 in meta.ledger


def test_completed_namespace_dry_run(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    write_campaign_envelope(root, bindings=BINDINGS, run_count=1)
    from tools.arvp_vacation.sensitivity_campaign_state import (
        CAMPAIGN_ENVELOPE_NAME,
        atomic_write_json,
        read_json,
    )

    env_path = root / CAMPAIGN_ENVELOPE_NAME
    env = read_json(env_path)
    env["campaign_phase"] = CAMPAIGN_PHASE_COMPLETED
    atomic_write_json(env_path, env)
    _write_slim(root)
    (root / "runs").mkdir(exist_ok=True)
    report = run_orchestrator(evidence_root=root, mode="dry-run")
    assert report["verdict"] == VERDICT_DRY_RUN_PASS
    assert report["source_mode"] == "completed_namespace"


def test_cli_dry_run_exit_codes(tmp_path: Path) -> None:
    root = tmp_path / "slim"
    _write_slim(root)
    assert (
        main(
            [
                "dry-run",
                "--evidence-root",
                str(root),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "dry-run",
                "--evidence-root",
                str(tmp_path / "missing"),
            ]
        )
        == 2
    )


def test_pr_body_builder_validates() -> None:
    body = build_batch_pr_body(
        issue_number=4366,
        commit_sha="b" * 40,
        classification="INCONCLUSIVE",
        output_rel="docs/evidence/arvp/4366-orchestrator/",
    )
    meta = parse_batch_pr_body(body)
    assert meta.batch_key == "validation-research"
    assert meta.objective_key == "issue-4366"
