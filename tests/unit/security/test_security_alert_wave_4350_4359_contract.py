"""Contract for security alert wave #4350-#4359 (2026-08-05).

Validates machine-readable wave evidence, Grafana pin surfaces, cluster
partition, CVE-family invariants and safety-boundary defaults. Static
parsing only - no GitHub writes, no alert mutation, no runtime touch.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]

WAVE_JSON = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "security"
    / "CDB_SECURITY_ALERT_WAVE_4350-4359_2026-08-05.json"
)
WAVE_MD = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "security"
    / "CDB_SECURITY_ALERT_WAVE_4350-4359_2026-08-05.md"
)

BASELINE_GRAFANA_PIN = (
    "grafana/grafana:13.1.1-ubuntu@"
    "sha256:5a9df011defa8384ee01fc9b393854daecc6afb98132c66e2e658b3f564830e8"
)
TARGET_GRAFANA_PIN = (
    "grafana/grafana:13.1.2-ubuntu@"
    "sha256:dbbf39afd3040b86fc6d2d9a6f0ce3dab9c18039af9af7f6404ba71e56be6c45"
)

EXPECTED_ISSUES = frozenset(range(4350, 4360))
ZIPKIN_CLUSTER_ISSUES = frozenset({4350, 4351, 4352, 4353, 4354, 4355, 4356, 4359})
FIX_READY_ISSUES = frozenset({4357, 4358})
UPSTREAM_CLUSTER_TRACKER = 2933

ALLOWED_DISPOSITIONS = frozenset(
    {
        "FIX_READY",
        "HOLD_UPSTREAM_NO_FIXED_VERSION",
        "DUPLICATE_TRACKING",
        "FALSE_POSITIVE_WITH_EVIDENCE",
        "NEEDS_EVIDENCE",
    }
)
ALLOWED_CODEX_VERDICTS = frozenset({"confirmed", "not_actionable", "needs_review"})
FORBIDDEN_DISPOSITIONS = frozenset(
    {"FIXED_BY_PIN", "FIXED_SCAN_VERIFIED", "REMEDIATED_SCAN_VERIFIED"}
)

PIN_FILES = (
    REPO_ROOT / "infrastructure" / "compose" / "base.yml",
    REPO_ROOT / "infrastructure" / "compose" / "compose.red.yml",
    REPO_ROOT / ".github" / "workflows" / "security-scan.yml",
    REPO_ROOT / "knowledge" / "governance" / "SERVICE_CATALOG.md",
)


def _load_wave() -> dict:
    assert WAVE_JSON.is_file(), f"missing wave json: {WAVE_JSON}"
    return json.loads(WAVE_JSON.read_text(encoding="utf-8"))


def test_wave_markdown_and_json_exist() -> None:
    assert WAVE_MD.is_file(), f"missing markdown: {WAVE_MD}"
    assert WAVE_JSON.is_file(), f"missing json: {WAVE_JSON}"
    md = WAVE_MD.read_text(encoding="utf-8")
    assert "CDB_SECURITY_ALERT_WAVE_4350-4359_2026-08-05.json" in md
    assert "42b9703c276c5f49810247ceea6b1442a6158ee2" in md
    assert "no alert dismissal" in md.lower()
    assert "out of scope" in md.lower()
    assert TARGET_GRAFANA_PIN in md
    assert BASELINE_GRAFANA_PIN in md


def test_wave_schema_and_safety_flags() -> None:
    data = _load_wave()
    assert data["schema"] == "cdb.security_alert_wave.v1"
    assert data["wave_id"] == "security-alert-wave-2026-08-05"
    assert data["snapshot_date"] == "2026-08-05"
    assert data["base_sha"] == "42b9703c276c5f49810247ceea6b1442a6158ee2"
    assert data["routing_decision"] == "CREATE_DEDICATED_PR"
    assert data["merge_allowed"] is False
    assert data["merge_mode"] is False
    assert data["issue_closure_before_merge_allowed"] is False
    assert data["alert_dismissal_allowed"] is False
    assert data["trivyignore_growth_allowed"] is False
    assert data["lr_verdict"] == "NO-GO"
    assert data["grafana_baseline_pin"] == BASELINE_GRAFANA_PIN
    assert data["grafana_target_pin"] == TARGET_GRAFANA_PIN
    assert data["cap13_out_of_scope"]["documented"] is True
    boundaries = data["safety_boundaries"]
    assert boundaries["lr_verdict"] == "NO-GO"
    assert boundaries["live_authorization"] is False
    assert boundaries["runtime_mutation"] is False
    assert boundaries["productive_db_write"] is False
    assert boundaries["mcp_mutation"] is False
    assert boundaries["blue_red_boundary_bypass"] is False
    assert boundaries["admin_merge_used"] is False


def test_exactly_ten_issues_with_required_fields() -> None:
    data = _load_wave()
    rows = data["issues"]
    assert len(rows) == 10
    numbers = [row["issue"] for row in rows]
    assert set(numbers) == EXPECTED_ISSUES
    assert len(numbers) == len(set(numbers))
    for row in rows:
        assert row["cdb_disposition"] in ALLOWED_DISPOSITIONS
        assert row["cdb_disposition"] not in FORBIDDEN_DISPOSITIONS
        assert row["codex_verdict"] in ALLOWED_CODEX_VERDICTS
        assert isinstance(row["alert"], int)
        assert isinstance(row["component"], str) and row["component"]
        assert isinstance(row["package"], str) and row["package"]
        assert isinstance(row["canonical_tracker"], int)
        assert isinstance(row["closure_condition"], str) and row["closure_condition"]
        assert isinstance(row["fingerprint"], str) and row["fingerprint"]
        assert row["cve"].startswith("CVE-2026-")


def test_cluster_partition_matches_dispositions() -> None:
    data = _load_wave()
    by_issue = {row["issue"]: row for row in data["issues"]}
    assert by_issue[4350]["cdb_disposition"] == "HOLD_UPSTREAM_NO_FIXED_VERSION"
    for issue in ZIPKIN_CLUSTER_ISSUES - {4350}:
        assert by_issue[issue]["cdb_disposition"] == "DUPLICATE_TRACKING"
    for issue in ZIPKIN_CLUSTER_ISSUES:
        assert by_issue[issue]["canonical_tracker"] == UPSTREAM_CLUSTER_TRACKER
        assert by_issue[issue]["verified_still_present_on_13_1_2"] is True
    for issue in FIX_READY_ISSUES:
        assert by_issue[issue]["cdb_disposition"] == "FIX_READY"
        assert by_issue[issue]["canonical_tracker"] == issue
        assert by_issue[issue]["verified_cleared_on_13_1_2"] is True
        closure = by_issue[issue]["closure_condition"].lower()
        assert "merge" in closure
        assert "recount" in closure
    for row in data["issues"]:
        if row["issue"] != 4350:
            assert "closes #" not in row["closure_condition"].lower()


def test_grafana_pin_surfaces_synced_on_target_and_baseline_removed() -> None:
    for path in PIN_FILES:
        text = path.read_text(encoding="utf-8")
        assert TARGET_GRAFANA_PIN in text, f"missing grafana 13.1.2 pin in {path}"
        assert (
            BASELINE_GRAFANA_PIN not in text
        ), f"stale grafana 13.1.1 pin still in {path}"


def test_trivy_evidence_delta_from_baseline_to_candidate() -> None:
    data = _load_wave()
    evidence = data["trivy_evidence"]
    baseline = evidence["grafana_13_1_1_baseline"]
    candidate = evidence["grafana_13_1_2_candidate"]
    assert baseline["image"] == BASELINE_GRAFANA_PIN
    assert candidate["image"] == TARGET_GRAFANA_PIN
    assert baseline["high_total"] == 18
    assert baseline["critical_total"] == 1
    assert baseline["target_cve_hits"] == 13
    assert candidate["high_total"] == 14
    assert candidate["critical_total"] == 0
    assert candidate["target_cve_hits"] == 11
    assert candidate["grafana_bin_cleared"] is True
    assert candidate["elasticsearch_x_text_cleared"] is True
    assert candidate["zipkin_findings_unchanged"] is True
    delta = candidate["delta_from_baseline"]
    assert delta["high_reduced"] == baseline["high_total"] - candidate["high_total"]
    assert delta["critical_reduced"] == (
        baseline["critical_total"] - candidate["critical_total"]
    )
    assert set(delta["cleared_wave_issues"]) == FIX_READY_ISSUES
    assert set(delta["still_present_wave_issues"]) == ZIPKIN_CLUSTER_ISSUES
    assert (
        set(delta["cleared_wave_issues"]) | set(delta["still_present_wave_issues"])
        == EXPECTED_ISSUES
    )


def test_cve_2026_56852_family_origin_and_zipkin_root_cause() -> None:
    data = _load_wave()
    family = data["cve_family_analysis"]
    assert "0.39.0" in family["cve_2026_56852_common_origin"]
    assert "v0.37.0" in family["cve_2026_56852_common_origin"]
    assert "v0.33.0" in family["cve_2026_56852_common_origin"]
    assert "1.26.3" in family["zipkin_path_root_cause"]
    assert "v0.49.0" in family["zipkin_path_root_cause"]
    assert "v0.33.0" in family["zipkin_path_root_cause"]
    prior = family["prior_evidence_confirmation"]
    assert "UPSTREAM_BLOCKED" in prior["cve_2026_42504"]
    assert "1.26.3" in prior["cve_2026_27145"]


def test_clusters_declare_hold_evidence_and_forbidden_actions() -> None:
    data = _load_wave()
    hold = data["grafana_hold_evidence"]
    assert hold["canonical_tracker"] == UPSTREAM_CLUSTER_TRACKER
    assert hold["re_eval_date"] == "2026-11-05"
    forbidden = set(hold["forbidden_actions"])
    assert "no alert dismissal" in forbidden
    assert "no trivyignore growth" in forbidden
    assert "no vendoring of grafana source" in forbidden
    assert "no plugin-only patch commit" in forbidden
    fix = data["grafana_fix_evidence"]
    assert fix["cleared_wave_issues"] == [4357, 4358]
    assert "13.1.2" in fix["trigger"]
    closure = fix["closure_gate"].lower()
    assert "post-merge" in closure
    assert "recount" in closure


def test_brain_evidence_is_repo_only_and_insufficient() -> None:
    data = _load_wave()
    brain = data["brain_evidence"]
    assert brain["brain_source"] == "repo-only"
    assert brain["brain_status"] == "not-used"
    assert brain["context_brain_attempted"] is True
    assert brain["context_brain_used"] is False
    assert brain["context_available"] is False
    assert brain["repo_fallback_used"] is True
    assert brain["repo_fallback_reason"] == "insufficient_evidence"
    assert brain["context_trust_level"] == "none"
    assert brain["records_found"] == "none"


def test_pin_surfaces_are_pointed_at_by_wave_json() -> None:
    data = _load_wave()
    declared = set(data["pin_surfaces_synced"])
    on_disk = {p.relative_to(REPO_ROOT).as_posix() for p in PIN_FILES}
    assert declared == on_disk


def test_related_merged_prs_kept_for_lineage_only() -> None:
    data = _load_wave()
    related = data["related_merged_prs"]
    pr_4162 = related["4162"]
    assert "13.1.1-ubuntu" in pr_4162["title"]
    assert pr_4162["merge_commit"] == "4608aeff96ad9832a0335ab55676eea70021ae44"
    assert "did not clear" in pr_4162["note"].lower()
