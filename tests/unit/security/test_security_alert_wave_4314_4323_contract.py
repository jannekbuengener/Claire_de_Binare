"""Contract for security alert wave #4314–#4323 (2026-08-03).

Validates machine-readable wave evidence and Prometheus pin surfaces.
Static parsing only — no GitHub writes, no alert mutation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]

WAVE_JSON = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "security"
    / "CDB_SECURITY_ALERT_WAVE_4314-4323_2026-08-03.json"
)
WAVE_MD = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "security"
    / "CDB_SECURITY_ALERT_WAVE_4314-4323_2026-08-03.md"
)

PROM_PIN = (
    "prom/prometheus:v3.13.2@"
    "sha256:508729e0e2d18e11fd742a5a5ca70e557b940a93948c3c95fd0123a6fd538b69"
)
GRAFANA_PIN = (
    "grafana/grafana:13.1.1-ubuntu@"
    "sha256:5a9df011defa8384ee01fc9b393854daecc6afb98132c66e2e658b3f564830e8"
)
CURRENT_GRAFANA_PIN = (
    "grafana/grafana:13.1.2-ubuntu@"
    "sha256:dbbf39afd3040b86fc6d2d9a6f0ce3dab9c18039af9af7f6404ba71e56be6c45"
)
STALE_PROM = "prom/prometheus:v3.13.1@sha256:3c42b892cf723fa54d2f262c37a0e1f80aa8c8ddb1da7b9b0df9455a35a7f893"

EXPECTED_ISSUES = frozenset(range(4314, 4324))
ALLOWED_DISPOSITIONS = frozenset(
    {
        "FIX_READY",
        "HOLD_UPSTREAM_NO_FIXED_VERSION",
        "DUPLICATE_TRACKING",
        "FALSE_POSITIVE_WITH_EVIDENCE",
        "NEEDS_EVIDENCE",
    }
)
ALLOWED_VERDICTS = frozenset({"confirmed", "not_actionable", "needs_review"})

PIN_FILES = (
    REPO_ROOT / "infrastructure" / "compose" / "base.yml",
    REPO_ROOT / "infrastructure" / "compose" / "compose.red.yml",
    REPO_ROOT / "infrastructure" / "compose" / "compose.prometheus-v3.yml",
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
    assert "CDB_SECURITY_ALERT_WAVE_4314-4323_2026-08-03.json" in md
    assert "a52a0e90b702cd2758736bfa4ed25e2b9fd382ab" in md
    assert "No alert dismissal" in md or "no alert dismissal" in md.lower()
    assert "2026-09-03" in md
    assert "OUT OF SCOPE" in md or "out of scope" in md.lower()


def test_wave_schema_and_safety_flags() -> None:
    data = _load_wave()
    assert data["schema"] == "cdb.security_alert_wave.v1"
    assert data["wave_id"] == "security-alert-wave-2026-08-03"
    assert data["snapshot_date"] == "2026-08-03"
    assert data["base_sha"] == "a52a0e90b702cd2758736bfa4ed25e2b9fd382ab"
    assert data["routing_decision"] == "CREATE_DEDICATED_PR"
    assert data["merge_allowed"] is False
    assert data["merge_mode"] is False
    assert data["issue_closure_before_merge_allowed"] is False
    assert data["alert_dismissal_allowed"] is False
    assert data["trivyignore_growth_allowed"] is False
    assert data["lr_verdict"] == "NO-GO"
    assert data["prometheus_target_pin"] == PROM_PIN
    assert data["grafana_runtime_pin"] == GRAFANA_PIN
    assert data["cap45_out_of_scope"]["documented"] is True


def test_exactly_ten_issues_with_required_fields() -> None:
    data = _load_wave()
    rows = data["issues"]
    assert len(rows) == 10
    numbers = [row["issue"] for row in rows]
    assert set(numbers) == EXPECTED_ISSUES
    assert len(numbers) == len(set(numbers))
    for row in rows:
        assert row["cdb_disposition"] in ALLOWED_DISPOSITIONS
        assert row["codex_verdict"] in ALLOWED_VERDICTS
        assert isinstance(row["alert"], int)
        assert isinstance(row["component"], str) and row["component"]
        assert isinstance(row["package"], str) and row["package"]
        assert isinstance(row["canonical_tracker"], int)
        assert isinstance(row["closure_condition"], str) and row["closure_condition"]
        assert isinstance(row["fingerprint"], str) and row["fingerprint"]


def test_cluster_partition_matches_dispositions() -> None:
    data = _load_wave()
    by_issue = {row["issue"]: row for row in data["issues"]}
    perl = {4314, 4315, 4316, 4317, 4318, 4319, 4320, 4321}
    assert by_issue[4314]["cdb_disposition"] == "HOLD_UPSTREAM_NO_FIXED_VERSION"
    for issue in perl - {4314}:
        assert by_issue[issue]["cdb_disposition"] == "DUPLICATE_TRACKING"
        assert by_issue[issue]["canonical_tracker"] == 2932
    assert by_issue[4314]["canonical_tracker"] == 2932
    assert by_issue[4322]["cdb_disposition"] == "HOLD_UPSTREAM_NO_FIXED_VERSION"
    assert by_issue[4322]["canonical_tracker"] == 2933
    assert by_issue[4323]["cdb_disposition"] == "FIX_READY"
    assert "merge" in by_issue[4323]["closure_condition"].lower()
    assert "recount" in by_issue[4323]["closure_condition"].lower()
    forbidden_fixed = {
        "FIXED_BY_PIN",
        "FIXED_SCAN_VERIFIED",
        "REMEDIATED_SCAN_VERIFIED",
    }
    for row in data["issues"]:
        assert row["cdb_disposition"] not in forbidden_fixed
        if row["issue"] != 4323:
            assert "closes #" not in row["closure_condition"].lower()


def test_prometheus_and_grafana_pins_synced_no_stale_prom() -> None:
    for path in PIN_FILES:
        text = path.read_text(encoding="utf-8")
        assert STALE_PROM not in text, f"stale prometheus pin still in {path}"
        assert PROM_PIN in text, f"missing prometheus v3.13.2 pin in {path}"
        if path.name in {
            "base.yml",
            "compose.red.yml",
            "security-scan.yml",
            "SERVICE_CATALOG.md",
        }:
            assert CURRENT_GRAFANA_PIN in text, f"missing current grafana pin in {path}"
            assert GRAFANA_PIN not in text, f"stale grafana 13.1.1 pin still in {path}"


def test_trivy_evidence_claims_are_internally_consistent() -> None:
    data = _load_wave()
    prom = data["trivy_evidence"]["prometheus_v3_13_2"]
    assert prom["cve_2026_56852_hits"] == 0
    assert prom["high_critical_total"] == 0
    assert prom["bin_prometheus_cleared"] is True
    assert prom["bin_promtool_cleared"] is True
    contrast = data["trivy_evidence"]["prometheus_v3_13_1_contrast"]
    assert contrast["cve_2026_56852_hits"] == 2
    grafana = data["trivy_evidence"]["grafana_13_1_1"]
    assert grafana["ghsa_r277_hits"] >= 1
    assert grafana["kin_openapi_installed"].startswith("v0.140")
    assert data["perl_hold_evidence"]["suite_native_fix_available"] is False
    assert data["perl_hold_evidence"]["re_eval_date"] == "2026-09-03"
    assert data["grafana_hold_evidence"]["re_eval_date"] == "2026-09-03"


def test_compose_prometheus_comment_mentions_v3_13_2() -> None:
    overlay = (
        REPO_ROOT / "infrastructure" / "compose" / "compose.prometheus-v3.yml"
    ).read_text(encoding="utf-8")
    assert re.search(r"cdb_prometheus \(v3\.13\.2\)", overlay)
    assert "v3.13.1)" not in overlay
