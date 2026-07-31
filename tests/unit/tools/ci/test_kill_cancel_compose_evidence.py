"""Contract/unit tests for kill-cancel compose evidence writer (#4222).

test_id: tc_kill_cancel_compose_evidence_4222
test_type: bauteil
cdb_area: ci
rule_ref: cdb-kill-cancel-compose-evidence/v1
issue_ref: #4222
security_relevant: false
live_relevant: false
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.ci.kill_cancel_compose_evidence import (
    SCENARIO_TEST_MAP,
    EvidenceStatus,
    build_manifest,
    junit_testcase_status,
    resolve_overall_verdict,
    resolve_scenarios,
)

pytestmark = pytest.mark.unit


def _write_junit(path: Path, cases: list[tuple[str, str | None]]) -> None:
    """cases: (name, outcome) where outcome is None|failure|error|skipped."""
    parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<testsuites name="pytest tests">',
        '<testsuite name="pytest" errors="0" failures="0" skipped="0" tests="0">',
    ]
    for name, outcome in cases:
        if outcome is None:
            parts.append(
                f'<testcase classname="tests.e2e.drill" name="{name}" time="0.01" />'
            )
        elif outcome == "skipped":
            parts.append(
                f'<testcase classname="tests.e2e.drill" name="{name}" time="0.0">'
                f'<skipped type="pytest.skip" message="x">skip</skipped>'
                f"</testcase>"
            )
        else:
            parts.append(
                f'<testcase classname="tests.e2e.drill" name="{name}" time="0.01">'
                f'<{outcome} message="boom">traceback</{outcome}>'
                f"</testcase>"
            )
    parts.extend(["</testsuite>", "</testsuites>", ""])
    path.write_text("\n".join(parts), encoding="utf-8")


def test_successful_testcase_maps_to_pass(tmp_path: Path) -> None:
    xml = tmp_path / "phase1.xml"
    _write_junit(xml, [("test_s1_s2_inactive_keeps_resting_orders_open", None)])
    assert (
        junit_testcase_status(xml, "test_s1_s2_inactive_keeps_resting_orders_open")
        == EvidenceStatus.PASS
    )


def test_failure_maps_to_fail(tmp_path: Path) -> None:
    xml = tmp_path / "phase1.xml"
    _write_junit(xml, [("test_s4_unevaluable_fail_closed", "failure")])
    assert (
        junit_testcase_status(xml, "test_s4_unevaluable_fail_closed")
        == EvidenceStatus.FAIL
    )


def test_error_maps_to_fail(tmp_path: Path) -> None:
    xml = tmp_path / "phase1.xml"
    _write_junit(xml, [("test_s11_fill_after_kill_fail", "error")])
    assert (
        junit_testcase_status(xml, "test_s11_fill_after_kill_fail")
        == EvidenceStatus.FAIL
    )


def test_skipped_maps_to_hold(tmp_path: Path) -> None:
    xml = tmp_path / "phase1.xml"
    _write_junit(xml, [("test_s6_cancel_rejection_hold", "skipped")])
    assert (
        junit_testcase_status(xml, "test_s6_cancel_rejection_hold")
        == EvidenceStatus.HOLD
    )


def test_malformed_xml_is_parse_error(tmp_path: Path) -> None:
    xml = tmp_path / "phase1.xml"
    xml.write_text("<not-closed", encoding="utf-8")
    assert (
        junit_testcase_status(xml, "test_s1_s2_inactive_keeps_resting_orders_open")
        == EvidenceStatus.PARSE_ERROR
    )


def test_missing_file_is_not_run(tmp_path: Path) -> None:
    xml = tmp_path / "phase1.xml"
    assert (
        junit_testcase_status(xml, "test_s1_s2_inactive_keeps_resting_orders_open")
        == EvidenceStatus.NOT_RUN
    )


def test_unmapped_scenario_is_missing_mapping(tmp_path: Path) -> None:
    xml = tmp_path / "phase1.xml"
    _write_junit(xml, [("test_other", None)])
    assert (
        junit_testcase_status(xml, "test_s1_s2_inactive_keeps_resting_orders_open")
        == EvidenceStatus.MISSING_MAPPING
    )


def test_parametrized_name_exact_match(tmp_path: Path) -> None:
    xml = tmp_path / "phase1.xml"
    name = "test_s3_s5_active_cancels_confirmed[adapter-a]"
    _write_junit(xml, [(name, None)])
    assert junit_testcase_status(xml, name) == EvidenceStatus.PASS
    assert (
        junit_testcase_status(xml, "test_s3_s5_active_cancels_confirmed")
        == EvidenceStatus.MISSING_MAPPING
    )


def test_nested_testsuites_aggregated(tmp_path: Path) -> None:
    xml = tmp_path / "phase1.xml"
    xml.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="outer">
    <testsuite name="inner">
      <testcase classname="pkg.mod" name="test_s9_double_kill_idempotent" time="0.1"/>
    </testsuite>
  </testsuite>
</testsuites>
""",
        encoding="utf-8",
    )
    assert (
        junit_testcase_status(xml, "test_s9_double_kill_idempotent")
        == EvidenceStatus.PASS
    )


def test_stale_junit_from_other_run_rejected(tmp_path: Path) -> None:
    xml = tmp_path / "phase1.xml"
    _write_junit(xml, [("test_s1_s2_inactive_keeps_resting_orders_open", None)])
    marker = tmp_path / ".run_marker"
    marker.write_text("run-b", encoding="utf-8")
    # File mtime older than marker → stale
    import os
    import time

    past = time.time() - 120
    os.utime(xml, (past, past))
    assert (
        junit_testcase_status(
            xml,
            "test_s1_s2_inactive_keeps_resting_orders_open",
            not_before_mtime=marker.stat().st_mtime,
        )
        == EvidenceStatus.INCOMPLETE
    )


def test_pytest_pass_with_complete_map_is_pass(tmp_path: Path) -> None:
    p1 = tmp_path / "phase1.xml"
    p2 = tmp_path / "phase2.xml"
    phase1_names = [
        name for sid, (phase, name) in SCENARIO_TEST_MAP.items() if phase == "phase1"
    ]
    _write_junit(p1, [(n, None) for n in phase1_names])
    _write_junit(p2, [("test_s10b_restart_reconciles_before_new_orders", None)])
    scenarios = resolve_scenarios(tmp_path)
    assert set(scenarios) == set(SCENARIO_TEST_MAP)
    assert all(v == EvidenceStatus.PASS.value for v in scenarios.values())
    overall, reason = resolve_overall_verdict(
        scenarios=scenarios,
        phase1_exit=0,
        phase2_exit=0,
        cleanup_pass=True,
        run_error="",
    )
    assert overall == EvidenceStatus.PASS.value
    assert reason == "EVIDENCE_COMPLETE"


def test_pytest_pass_with_mapping_gap_is_incomplete_not_product_fail(
    tmp_path: Path,
) -> None:
    """Regression #4222: missing JUnit must not invent product FAIL scenarios
    while overall_verdict stays PASS from pytest exit codes alone.
    """
    # No phase1/phase2 XML — legacy writer returned FAIL per scenario + PASS overall.
    scenarios = resolve_scenarios(tmp_path)
    assert all(v == EvidenceStatus.NOT_RUN.value for v in scenarios.values())
    overall, reason = resolve_overall_verdict(
        scenarios=scenarios,
        phase1_exit=0,
        phase2_exit=0,
        cleanup_pass=True,
        run_error="",
    )
    assert overall == EvidenceStatus.INCOMPLETE.value
    assert reason == "SCENARIO_EVIDENCE_INCOMPLETE"
    assert EvidenceStatus.FAIL.value not in scenarios.values()


def test_legacy_mismatch_fixture_reproduced_and_fixed(tmp_path: Path) -> None:
    """Observed #4222 shape: pytest exit 0, scenario map all FAIL via missing map."""
    # Simulate legacy false FAIL labels by invoking old semantics indirectly:
    # empty evidence dir + exit 0 must become INCOMPLETE, never PASS+FAIL mix.
    scenarios = resolve_scenarios(tmp_path)
    overall, _ = resolve_overall_verdict(
        scenarios=scenarios,
        phase1_exit=0,
        phase2_exit=0,
        cleanup_pass=True,
        run_error="",
    )
    assert overall != EvidenceStatus.PASS.value
    assert EvidenceStatus.FAIL.value not in set(scenarios.values())
    # Contradictory PASS overall with FAIL scenarios is forbidden.
    assert not (
        overall == EvidenceStatus.PASS.value
        and EvidenceStatus.FAIL.value in scenarios.values()
    )


def test_build_manifest_writes_machine_readable_status(tmp_path: Path) -> None:
    p1 = tmp_path / "phase1.xml"
    p2 = tmp_path / "phase2.xml"
    phase1_names = [
        name for phase, name in SCENARIO_TEST_MAP.values() if phase == "phase1"
    ]
    _write_junit(p1, [(n, None) for n in phase1_names])
    _write_junit(p2, [("test_s10b_restart_reconciles_before_new_orders", None)])
    manifest = build_manifest(
        evidence_dir=tmp_path,
        run_id="4185_deadbeef_20260730T000000Z",
        commit_sha="deadbeef" * 5,
        compose_project="cdb_4185_deadbeef",
        started_at_utc="2026-07-30T00:00:00Z",
        completed_at_utc="2026-07-30T00:01:00Z",
        phase1_exit=0,
        phase2_exit=0,
        cleanup_pass=True,
        run_error="",
    )
    out = tmp_path / "manifest.json"
    out.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == "cdb-kill-cancel-compose-evidence/v1"
    assert loaded["overall_verdict"] == EvidenceStatus.PASS.value
    assert loaded["evidence_status_model"]["states"]
    assert loaded["scenario_evidence_reason"] == "EVIDENCE_COMPLETE"
    assert all(v == "PASS" for v in loaded["scenarios"].values())


def test_namespaced_junit_still_resolves(tmp_path: Path) -> None:
    xml = tmp_path / "phase1.xml"
    xml.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<ns:testsuites xmlns:ns="https://example.invalid/junit">
  <ns:testsuite name="pytest">
    <ns:testcase classname="mod" name="test_s12_positions_visible_no_auto_unwind" time="0.0"/>
  </ns:testsuite>
</ns:testsuites>
""",
        encoding="utf-8",
    )
    assert (
        junit_testcase_status(xml, "test_s12_positions_visible_no_auto_unwind")
        == EvidenceStatus.PASS
    )
