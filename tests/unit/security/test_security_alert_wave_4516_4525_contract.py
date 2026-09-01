"""Contract for security alert wave #4516–#4525 (2026-09-01).

Validates machine-readable wave evidence for upstream-blocked perl-base and
curl/libcurl clusters. Static parsing only — no GitHub writes, no alert mutation.
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
    / "CDB_SECURITY_ALERT_WAVE_4516-4525_2026-09-01.json"
)
WAVE_MD = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "security"
    / "CDB_SECURITY_ALERT_WAVE_4516-4525_2026-09-01.md"
)
HOLD_4080 = (
    REPO_ROOT / "docs" / "evidence" / "security" / "4080_CVE-2026-8286_UPSTREAM_HOLD.md"
)

EXPECTED_ISSUES = frozenset(range(4516, 4526))
PERL_ISSUES = frozenset(range(4516, 4522))
CURL_ISSUES = frozenset(range(4522, 4526))
BASE_DIGEST = "sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6"
RE_EVAL_DATE = "2026-09-15"


def _load_wave() -> dict:
    assert WAVE_JSON.is_file(), f"missing wave json: {WAVE_JSON}"
    return json.loads(WAVE_JSON.read_text(encoding="utf-8"))


def test_wave_markdown_and_json_exist() -> None:
    assert WAVE_MD.is_file(), f"missing markdown: {WAVE_MD}"
    assert WAVE_JSON.is_file(), f"missing json: {WAVE_JSON}"
    md = WAVE_MD.read_text(encoding="utf-8")
    assert "CDB_SECURITY_ALERT_WAVE_4516-4525_2026-09-01.json" in md
    assert "41b5c04aeb4826888e7eff00ccba9d1350cfda84" in md
    assert RE_EVAL_DATE in md
    assert "#2932" in md
    assert "#4080" in md
    assert "#4114" in md
    assert "no alert dismissal" in md.lower()


def test_wave_schema_and_upstream_hold_flags() -> None:
    data = _load_wave()
    assert data["schema"] == "cdb.security_alert_wave.v1"
    assert data["wave_id"] == "security-alert-wave-2026-09-01"
    assert data["base_sha"] == "41b5c04aeb4826888e7eff00ccba9d1350cfda84"
    assert data["alert_dismissal_allowed"] is False
    assert data["trivyignore_growth_allowed"] is False
    assert data["lr_verdict"] == "NO-GO"
    assert (
        data["debian_tracker_evidence"]["CVE-2026-57432"]["suite_native_fix_available"]
        is False
    )
    assert (
        data["debian_tracker_evidence"]["CVE-2026-8927"]["suite_native_fix_available"]
        is False
    )
    assert data["trivy_evidence"]["digest_refresh_clears_wave_cves"] is False


def test_exactly_ten_issues_partitioned_by_cluster() -> None:
    data = _load_wave()
    rows = data["issues"]
    assert len(rows) == 10
    numbers = {row["issue"] for row in rows}
    assert numbers == EXPECTED_ISSUES
    by_issue = {row["issue"]: row for row in rows}
    assert by_issue[4516]["cdb_disposition"] == "HOLD_UPSTREAM_NO_FIXED_VERSION"
    assert by_issue[4516]["canonical_tracker"] == 2932
    for issue in PERL_ISSUES - {4516}:
        assert by_issue[issue]["cdb_disposition"] == "DUPLICATE_TRACKING"
        assert by_issue[issue]["canonical_tracker"] == 2932
    assert by_issue[4522]["cdb_disposition"] == "HOLD_UPSTREAM_NO_FIXED_VERSION"
    assert by_issue[4522]["canonical_tracker"] == 4080
    for issue in CURL_ISSUES - {4522}:
        assert by_issue[issue]["cdb_disposition"] == "DUPLICATE_TRACKING"
        assert by_issue[issue]["canonical_tracker"] == 4080


def test_trivy_probe_documents_empty_fixed_versions() -> None:
    data = _load_wave()
    findings = data["trivy_evidence"]["findings"]
    cve57432 = [f for f in findings if f["cve"] == "CVE-2026-57432"]
    cve8927 = [f for f in findings if f["cve"] == "CVE-2026-8927"]
    assert len(cve57432) == 1
    assert cve57432[0]["installed"] == "5.40.1-6"
    assert cve57432[0]["fixed_version_trivy"] is None
    assert len(cve8927) == 2
    assert all(f["installed"] == "8.14.1-2+deb13u4" for f in cve8927)
    assert all(f["fixed_version_trivy"] is None for f in cve8927)


def test_re_eval_triggers_and_issue_close_policy() -> None:
    data = _load_wave()
    assert (
        data["re_eval_triggers"]["perl_cve_2026_57432"]["next_calendar_probe"]
        == RE_EVAL_DATE
    )
    assert (
        data["re_eval_triggers"]["curl_cve_2026_8927"]["next_calendar_probe"]
        == RE_EVAL_DATE
    )
    assert data["code_scanning_alerts_remaining_open_after_issue_close"] == 10
    assert data["issue_closure_after_merge_allowed"] is True


def test_canonical_4080_hold_references_wave_issues() -> None:
    text = HOLD_4080.read_text(encoding="utf-8")
    for issue in (4522, 4523, 4524, 4525):
        assert f"#{issue}" in text
    assert RE_EVAL_DATE in text
    assert BASE_DIGEST in text
