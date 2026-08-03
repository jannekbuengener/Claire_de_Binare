"""Contract for the 2026-08-03 security backlog reconciliation snapshot (#2513).

Validates the machine-readable reconciliation JSON against role/disposition
invariants. Static parsing only — no image build, no scanner mutation, no
GitHub writes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]

SNAPSHOT_JSON = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "security"
    / "CDB_SECURITY_BACKLOG_RECONCILIATION_2026-08-03.json"
)
SNAPSHOT_MD = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "security"
    / "CDB_SECURITY_BACKLOG_RECONCILIATION_2026-08-03.md"
)

ALLOWED_DISPOSITIONS = frozenset(
    {
        "FIXED_SCAN_VERIFIED",
        "CANONICAL_TRACKER_ACTIVE",
        "DUPLICATE_TRACKING_PENDING_CLOSE_AFTER_MERGE",
        "HOLD_UPSTREAM_NO_FIXED_VERSION",
        "REMEDIATED_SCAN_VERIFIED",
        "BLOCKED_INSUFFICIENT_EVIDENCE",
    }
)

EXPECTED_ISSUES = frozenset(
    {
        2513,
        2932,
        2933,
        3705,
        3802,
        3803,
        3936,
        4080,
        4089,
        4090,
        4091,
        4092,
        4093,
        4094,
        4095,
        4096,
        4097,
        4098,
        4106,
        4114,
    }
)

CURL_DUPLICATES = frozenset({4089, 4090, 4091, 4092, 4093, 4096, 4097, 4098})
PIP_FIXED = frozenset({4094, 4095})
PERL_HOLDS = frozenset({4106, 4114})
CANONICAL_RESIDUALS = frozenset({2932, 2933, 3705, 3802, 3803, 3936})


def _load_snapshot() -> dict:
    assert SNAPSHOT_JSON.is_file(), f"missing snapshot: {SNAPSHOT_JSON}"
    return json.loads(SNAPSHOT_JSON.read_text(encoding="utf-8"))


def test_snapshot_markdown_and_json_exist() -> None:
    assert SNAPSHOT_MD.is_file(), f"missing markdown: {SNAPSHOT_MD}"
    assert SNAPSHOT_JSON.is_file(), f"missing json: {SNAPSHOT_JSON}"
    md = SNAPSHOT_MD.read_text(encoding="utf-8")
    assert "CDB_SECURITY_BACKLOG_RECONCILIATION_2026-08-03.json" in md
    assert "abf997d5fec97c4d4da139ae0fb9c1fe28773e89" in md
    assert "No alert dismissal" in md or "no alert dismissal" in md.lower()


def test_snapshot_schema_and_base_sha() -> None:
    data = _load_snapshot()
    assert data["schema"] == "cdb.security_backlog_reconciliation.v1"
    assert data["snapshot_date"] == "2026-08-03"
    assert data["anchor_issue"] == 2513
    assert data["base_sha"] == "abf997d5fec97c4d4da139ae0fb9c1fe28773e89"
    assert data["routing_decision"] == "CREATE_DEDICATED_PR"
    assert data["merge_allowed"] is False
    assert data["issue_closure_before_merge_allowed"] is False
    assert data["alert_dismissal_allowed"] is False
    assert data["trivyignore_growth_allowed"] is False
    assert data["open_type_security_count"] == 20
    assert 4302 in data["unrelated_prs_excluded"]


def test_exactly_twenty_issues_with_unique_dispositions() -> None:
    data = _load_snapshot()
    issues = data["issues"]
    assert len(issues) == 20
    numbers = [row["issue"] for row in issues]
    assert set(numbers) == EXPECTED_ISSUES
    assert len(numbers) == len(set(numbers))
    for row in issues:
        assert row["disposition"] in ALLOWED_DISPOSITIONS
        assert isinstance(row["canonical_issue"], int)
        assert isinstance(row["closure_condition"], str) and row["closure_condition"]
        assert isinstance(row["evidence_refs"], list) and row["evidence_refs"]


def test_disposition_summary_partitions_all_issues() -> None:
    data = _load_snapshot()
    summary = data["disposition_summary"]
    flattened: list[int] = []
    for key, values in summary.items():
        assert key in ALLOWED_DISPOSITIONS
        flattened.extend(values)
    assert set(flattened) == EXPECTED_ISSUES
    assert len(flattened) == 20
    by_issue = {row["issue"]: row["disposition"] for row in data["issues"]}
    for disposition, issue_list in summary.items():
        for issue in issue_list:
            assert by_issue[issue] == disposition


def test_curl_duplicates_point_at_4080() -> None:
    data = _load_snapshot()
    by_issue = {row["issue"]: row for row in data["issues"]}
    assert by_issue[4080]["disposition"] == "CANONICAL_TRACKER_ACTIVE"
    assert by_issue[4080]["role"] == "canonical_curl"
    for issue in CURL_DUPLICATES:
        row = by_issue[issue]
        assert row["disposition"] == "DUPLICATE_TRACKING_PENDING_CLOSE_AFTER_MERGE"
        assert row["canonical_issue"] == 4080


def test_pip_fixed_requires_fixed_alert_evidence() -> None:
    data = _load_snapshot()
    by_issue = {row["issue"]: row for row in data["issues"]}
    expected_alerts = {4094: 5527, 4095: 5526}
    for issue in PIP_FIXED:
        row = by_issue[issue]
        assert row["disposition"] == "FIXED_SCAN_VERIFIED"
        assert len(row["alerts"]) >= 1
        alert = row["alerts"][0]
        assert alert["number"] == expected_alerts[issue]
        assert alert["state"] == "fixed"
        assert alert["fixed_at"]
        assert alert["dismissed_at"] is None
        assert alert["rule_id"] == "CVE-2026-8643"


def test_perl_holds_and_residuals() -> None:
    data = _load_snapshot()
    by_issue = {row["issue"]: row for row in data["issues"]}
    for issue in PERL_HOLDS:
        assert by_issue[issue]["disposition"] == "HOLD_UPSTREAM_NO_FIXED_VERSION"
        assert by_issue[issue]["upstream_hold"] is True
    for issue in CANONICAL_RESIDUALS | {2513, 4080}:
        assert by_issue[issue]["disposition"] == "CANONICAL_TRACKER_ACTIVE"
    # #4114 scope drift correction markers
    row_4114 = by_issue[4114]
    assert row_4114["scope_images"] == ["cdb_allocation", "cdb_db_writer"]
    assert "scope_drift_correction" in row_4114
    assert "allocation" in row_4114["scope_drift_correction"].lower()


def test_no_remediation_or_dismiss_path_in_snapshot() -> None:
    data = _load_snapshot()
    assert data["remediations_this_slice"] == []
    forbidden = set(data["forbidden_actions_this_slice"])
    for required in (
        "merge",
        "issue_close",
        "alert_dismiss",
        "trivyignore_expand",
        "full_fast_ci",
        "cdb_local_ci_publish",
        "touch_pr_4302",
    ):
        assert required in forbidden
    assert data["disposition_summary"]["REMEDIATED_SCAN_VERIFIED"] == []
    assert data["disposition_summary"]["BLOCKED_INSUFFICIENT_EVIDENCE"] == []


def test_evidence_refs_point_at_existing_repo_files() -> None:
    data = _load_snapshot()
    for row in data["issues"]:
        for ref in row["evidence_refs"]:
            path = REPO_ROOT / ref
            assert path.is_file(), f"missing evidence ref for #{row['issue']}: {ref}"
