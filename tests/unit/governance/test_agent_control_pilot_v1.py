"""
test_id: tc_agent_control_pilot_v1_001
test_name: agent_control_pilot_v1_foundation_e2e
test_type: Bauteil-Test
cdb_area: governance
rule_ref: docs/contracts/agent_pilot/CDB_AGENT_CONTROL_PILOT_REPORT_V1.md
decision_ref: cdb.agent_control_pilot_report.v1
issue_ref: 4258
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tools.agent_control.cli import main as cli_main
from tools.agent_control.evidence.emit import emit_evidence
from tools.agent_control.evidence.store import EvidenceJsonlStore
from tools.agent_control.errors import EvidenceError
from tools.agent_control.pilot import load_manifest, run_pilot, run_pilot_from_path
from tools.agent_control.pilot_report import (
    AUTHORITY_LIMITS,
    compute_report_digest,
    verify_report,
)
from tools.agent_control.paths import REPO_ROOT

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "agent_control" / "pilot"


def _run(name: str) -> dict:
    return run_pilot_from_path(FIXTURES / name, repo_root=REPO_ROOT)


@pytest.mark.unit
def test_p1_pass_full_chain() -> None:
    report = _run("p1_pass.manifest.json")
    assert report["final_status"] == "PASS"
    assert report["provider_call_count"] == 1
    assert report["head_sha"] == "a" * 40
    assert report["subject"]["head_sha"] == report["head_sha"]
    assert report["approval_recommendation"] == "APPROVE_RECOMMENDED"
    assert report["approval_context_digest"]
    assert report["run_evidence_refs"]
    assert report["authority_limits"] == AUTHORITY_LIMITS
    assert "not_issue_closure" in report["limitations"]
    assert "refs_4258_not_closes" in report["limitations"]
    verify_report(report)
    # Head bound in report+approval, not via evidence schema change
    assert "head_sha" not in (report["run_evidence_refs"][0] or {})


@pytest.mark.unit
def test_n1_delivery_conflict_no_provider_call() -> None:
    report = _run("n1_delivery_conflict.manifest.json")
    assert report["final_status"] == "BLOCKED"
    assert report["provider_call_count"] == 0
    codes = [
        (s.get("detail") or {}).get("terminal_code")
        for s in report["step_results"]
        if s["step"] == "preflight_dispatch"
    ]
    assert "DISPATCH_DELIVERY_TARGET_CONFLICT" in codes


@pytest.mark.unit
def test_n2_attenuated_timeout() -> None:
    report = _run("n2_attenuated_timeout.manifest.json")
    assert report["final_status"] == "PASS"
    atten = [
        s for s in report["step_results"] if s["step"] == "environment_attenuation"
    ]
    assert atten and atten[0]["status"] == "PASS"
    assert atten[0]["detail"]["effective_wall_time_seconds"] == 120
    assert atten[0]["detail"]["contract_wall_time_seconds"] == 14400
    assert report["input_digests"]["effective_wall_time_seconds"] == 120


@pytest.mark.unit
def test_n3_malformed_receipt() -> None:
    report = _run("n3_malformed_receipt.manifest.json")
    assert report["final_status"] == "FAIL"
    assert report["provider_call_count"] == 1
    assert report["approval_recommendation"] is None


@pytest.mark.unit
def test_n4_stale_head() -> None:
    report = _run("n4_stale_head.manifest.json")
    assert report["final_status"] == "BLOCKED"
    assert report["approval_recommendation"] != "APPROVE_RECOMMENDED"
    appr = [s for s in report["step_results"] if s["step"] == "approval_context"][0]
    assert "STALE_HEAD" in (appr["detail"].get("reason_codes") or [])


@pytest.mark.unit
def test_n5_mechanism_mismatch() -> None:
    report = _run("n5_mechanism_mismatch.manifest.json")
    assert report["final_status"] == "UNKNOWN"
    assert report["approval_recommendation"] != "APPROVE_RECOMMENDED"
    appr = [s for s in report["step_results"] if s["step"] == "approval_context"][0]
    assert "MECHANISM_MISMATCH" in (appr["detail"].get("reason_codes") or [])


@pytest.mark.unit
def test_n6_policy_drift() -> None:
    report = _run("n6_policy_drift.manifest.json")
    assert report["final_status"] in {"HOLD", "BLOCKED", "UNKNOWN"}
    assert report["approval_recommendation"] != "APPROVE_RECOMMENDED"


@pytest.mark.unit
def test_n7_hold_plus_pass_store_collision(tmp_path: Path) -> None:
    from tools.agent_control.clock import FrozenClock
    from tools.agent_control.dispatch import dispatch_run, watch_run
    from tools.agent_control.load import load_registry_document
    from tools.agent_control.paths import DEFAULT_CONFIG_ROOT
    from tools.agent_control.provider import MockProvider
    from tools.agent_control.run_store import InMemoryRunStore
    from datetime import datetime, timezone

    contract = json.loads(
        (FIXTURES / "contract_p1_pass.json").read_text(encoding="utf-8")
    )
    registry = load_registry_document(DEFAULT_CONFIG_ROOT)
    store = InMemoryRunStore()
    provider = MockProvider()
    clock = FrozenClock(datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc))
    result = dispatch_run(
        contract,
        registry,
        "acp-e2e-pilot",
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
        clock=clock,
        scenario="success",
    )
    run = result["run"]
    run = watch_run(run["run_id"], store, provider=provider, clock=clock)
    run = watch_run(run["run_id"], store, provider=provider, clock=clock)
    assert run["state"] == "PASS"
    b1 = emit_evidence(run["run_id"], store)["bundle"]

    # Second independent PASS run → distinct evidence_id
    store2 = InMemoryRunStore()
    provider2 = MockProvider()
    result2 = dispatch_run(
        contract,
        registry,
        "acp-e2e-pilot",
        store2,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider2,
        clock=clock,
        scenario="success",
        attempt=2,
    )
    run2 = result2["run"]
    run2 = watch_run(run2["run_id"], store2, provider=provider2, clock=clock)
    run2 = watch_run(run2["run_id"], store2, provider=provider2, clock=clock)
    b2 = emit_evidence(run2["run_id"], store2)["bundle"]
    assert b1["evidence_id"] != b2["evidence_id"]

    path = tmp_path / "pilot_store.jsonl"
    js = EvidenceJsonlStore(path)
    js.append_idempotent(b1)
    js.append_idempotent(b2)
    # Same id different digest → blocked
    bad = deepcopy(b1)
    bad["bundle_digest"] = "sha256:" + ("f" * 64)
    with pytest.raises(EvidenceError) as exc:
        js.append_idempotent(bad)
    assert "COLLISION" in exc.value.code or "collision" in exc.value.message.lower()


@pytest.mark.unit
def test_n8_authority_limits_immutable() -> None:
    report = _run("n8_authority.manifest.json")
    assert report["authority_limits"] == AUTHORITY_LIMITS
    for key, val in AUTHORITY_LIMITS.items():
        assert report["authority_limits"][key] is val
    # Pilot module must not expose merge helpers
    import tools.agent_control.pilot as pilot_mod

    src = Path(pilot_mod.__file__).read_text(encoding="utf-8")
    assert "gh pr merge" not in src
    assert "publish_cdb_local_ci" not in src or "False" in src
    assert "Closes #4258" not in src


@pytest.mark.unit
def test_report_digest_deterministic_under_key_reorder() -> None:
    report = _run("p1_pass.manifest.json")
    d1 = compute_report_digest(report)
    reordered = json.loads(json.dumps(report, sort_keys=False))
    # Force key order change by rebuild
    reordered2 = {k: reordered[k] for k in sorted(reordered.keys(), reverse=True)}
    d2 = compute_report_digest(reordered2)
    assert d1 == d2 == report["report_digest"]


@pytest.mark.unit
def test_unknown_never_pass() -> None:
    from tools.agent_control.pilot_report import PilotReportError, build_report

    with pytest.raises(PilotReportError):
        build_report(
            pilot_id="x",
            scenario_id="P1",
            subject={"head_sha": "a" * 40, "base_sha": "b" * 40, "issue": 4258},
            contract_versions={"execution": "cdb.agent_execution.v1"},
            run_id=None,
            attempt=None,
            head_sha="a" * 40,
            input_digests={},
            step_results=[{"step": "x", "status": "UNKNOWN"}],
            provider_call_count=0,
            run_evidence_refs=[],
            approval_context_digest=None,
            approval_recommendation=None,
            final_status="PASS",
            limitations=[],
        )


@pytest.mark.unit
def test_manifest_validation(tmp_path: Path) -> None:
    from tools.agent_control.pilot import PilotError

    bad = deepcopy(json.loads((FIXTURES / "p1_pass.manifest.json").read_text()))
    bad["head_sha"] = "not-a-sha"
    path = tmp_path / "bad_head.manifest.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(PilotError) as exc:
        load_manifest(path)
    assert exc.value.code in {"PILOT_HEAD_INVALID", "PILOT_MANIFEST_SCHEMA"}


@pytest.mark.unit
def test_manifest_rejects_non_object_provider(tmp_path: Path) -> None:
    from tools.agent_control.pilot import PilotError

    bad = deepcopy(json.loads((FIXTURES / "p1_pass.manifest.json").read_text()))
    bad["provider"] = "success"
    path = tmp_path / "bad_provider.manifest.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(PilotError) as exc:
        load_manifest(path)
    assert exc.value.code == "PILOT_MANIFEST_SCHEMA"


@pytest.mark.unit
def test_tampered_contract_digest_not_resealed(tmp_path: Path) -> None:
    from tools.agent_control.pilot import run_pilot

    manifest = deepcopy(json.loads((FIXTURES / "p1_pass.manifest.json").read_text()))
    contract = deepcopy(json.loads((FIXTURES / "contract_p1_pass.json").read_text()))
    contract["budget"]["wall_time_seconds"] = 1  # keep stale integrity.digest
    cpath = tmp_path / "tampered_contract.json"
    cpath.write_text(json.dumps(contract), encoding="utf-8")
    manifest["contract_path"] = str(cpath)
    report = run_pilot(manifest, repo_root=REPO_ROOT)
    assert report["final_status"] == "FAIL"
    load_steps = [s for s in report["step_results"] if s["step"] == "load_contract"]
    assert load_steps and load_steps[0]["status"] == "FAIL"
    assert "HASH" in (load_steps[0].get("detail") or {}).get("error", "").upper() or (
        "digest" in (load_steps[0].get("detail") or {}).get("error", "").lower()
    )


@pytest.mark.unit
def test_expect_final_status_does_not_manufacture_blocked() -> None:
    from tools.agent_control.pilot import _finalize

    steps: list[dict] = []
    report = _finalize(
        {
            "pilot_id": "x",
            "scenario_id": "N1",
            "expect_final_status": "BLOCKED",
            "subject": {},
        },
        steps,
        None,
        None,
        "a" * 40,
        "b" * 40,
        {},
        0,
        [],
        None,
        None,  # no approval
        blocked=False,
        hold=False,
        fail=False,
        unknown=False,
        evidence_ok=True,
        limitations=[],
        contract_digest=None,
    )
    assert report["final_status"] == "FAIL"
    assert any(s["step"] == "scenario_expectation" for s in report["step_results"])


@pytest.mark.unit
def test_verify_rejects_pass_with_unknown_step() -> None:
    from tools.agent_control.pilot_report import PilotReportError, attach_report_digest

    report = _run("p1_pass.manifest.json")
    report["step_results"] = list(report["step_results"]) + [
        {"step": "injected", "status": "UNKNOWN"}
    ]
    report["final_status"] = "PASS"
    report = attach_report_digest(report)
    with pytest.raises(PilotReportError) as exc:
        verify_report(report)
    assert exc.value.code == "PILOT_REPORT_UNKNOWN_PASS"


@pytest.mark.unit
def test_verify_rejects_integrity_digest_conflict() -> None:
    from tools.agent_control.pilot_report import PilotReportError

    report = _run("p1_pass.manifest.json")
    report["integrity"] = dict(report["integrity"])
    report["integrity"]["digest"] = "sha256:" + ("f" * 64)
    with pytest.raises(PilotReportError) as exc:
        verify_report(report)
    assert exc.value.code in {
        "PILOT_REPORT_DIGEST_MISMATCH",
        "PILOT_REPORT_DIGEST_CONFLICT",
    }


@pytest.mark.unit
def test_verify_rejects_head_sha_subject_mismatch() -> None:
    from tools.agent_control.pilot_report import PilotReportError, attach_report_digest

    report = _run("p1_pass.manifest.json")
    report["subject"] = dict(report["subject"])
    report["subject"]["head_sha"] = "c" * 40
    report = attach_report_digest(report)
    with pytest.raises(PilotReportError) as exc:
        verify_report(report)
    assert exc.value.code == "PILOT_REPORT_HEAD_MISMATCH"


@pytest.mark.unit
def test_call_count_checked_before_blocked_short_circuit() -> None:
    from tools.agent_control.pilot import _map_final_status

    status = _map_final_status(
        blocked=True,
        hold=False,
        fail=False,
        unknown=False,
        approval_rec=None,
        evidence_ok=True,
        provider_calls=1,
        expect_provider_calls=0,
    )
    assert status == "FAIL"


@pytest.mark.unit
def test_missing_base_sha_not_fabricated() -> None:
    from tools.agent_control.pilot import run_pilot

    manifest = deepcopy(json.loads((FIXTURES / "p1_pass.manifest.json").read_text()))
    manifest.pop("base_sha", None)
    report = run_pilot(manifest, repo_root=REPO_ROOT)
    assert report["final_status"] == "PASS"
    assert report["subject"]["base_sha"] is None


@pytest.mark.unit
def test_cli_pilot_run_and_verify(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    code = cli_main(
        [
            "pilot",
            "run",
            "--manifest",
            str(FIXTURES / "p1_pass.manifest.json"),
            "--out",
            str(out),
        ]
    )
    assert code == 0
    assert out.is_file()
    code2 = cli_main(["pilot", "verify", "--report", str(out)])
    assert code2 == 0


@pytest.mark.unit
def test_cli_n1_exit_blocked() -> None:
    code = cli_main(
        [
            "pilot",
            "run",
            "--manifest",
            str(FIXTURES / "n1_delivery_conflict.manifest.json"),
        ]
    )
    assert code == 2  # EXIT_BLOCKED
