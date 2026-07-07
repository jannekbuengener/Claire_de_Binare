"""ARVP docs/evidence drift regression tests (#3825).

Fixture-backed drift detection between ARVP roadmap, evidence docs, contract-test
stand, and issue-status snapshots. No auto-fix, no live GitHub in CI.
"""

from __future__ import annotations

import json
import sys

import pytest

from tests.unit.arvp import _arvp_docs_drift_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

_FORBIDDEN_RUNTIME_IMPORTS = frozenset(
    {"requests", "httpx", "subprocess", "surrealdb", "gh"}
)


def test_arvp_flow_doc_declares_non_authoritative_status() -> None:
    text = helpers.ARVP_FLOW_MD.read_text(encoding="utf-8").lower()
    assert "not authoritative" in text or "docs-only" in text


def test_p0_p1_contract_tests_exist_and_docs_reference_them() -> None:
    scan = helpers.scan_arvp_docs_drift()
    assert scan.missing_contract_tests == ()
    drift_kinds = {finding.kind for finding in scan.findings}
    assert "contract_test_missing" not in drift_kinds
    assert "p1_doc_contract_test_drift" not in drift_kinds
    assert "p0_doc_contract_test_drift" not in drift_kinds


def test_arvp_roadmap_and_lr050_mapping_contain_no_go() -> None:
    assert "NO-GO" in helpers.ARVP_ROADMAP.read_text(encoding="utf-8")
    assert "NO-GO" in helpers.LR050_ARVP_MAPPING.read_text(encoding="utf-8")
    scan = helpers.scan_arvp_docs_drift()
    assert not any(
        f.kind in {"arvp_roadmap_lr_drift", "lr050_mapping_lr_drift"}
        for f in scan.findings
    )


def test_arvp_test_map_json_exists_with_partial_coverage() -> None:
    payload = json.loads(helpers.P2_TEST_MAP_JSON.read_text(encoding="utf-8"))
    assert payload["coverage"] == "partial"
    assert payload["catalog_scope"] == "agent-facing-arvp-test-map-p2"


def test_active_arvp_evidence_docs_avoid_unpaired_live_go_claims() -> None:
    claims = helpers.scan_arvp_evidence_docs_for_forbidden_claims()
    assert claims == (), claims


def test_scan_outputs_include_limitations() -> None:
    scan = helpers.scan_arvp_docs_drift()
    assert scan.limitations
    assert any("no automatic" in item.lower() for item in scan.limitations)
    assert any("not authoritative" in item.lower() for item in scan.limitations)


def test_fixture_detects_roadmap_repo_and_issue_status_drift() -> None:
    fixture = helpers.load_drift_fixture("roadmap_evidence_mismatch_fixture.json")
    result = helpers.score_arvp_docs_drift_fixture(fixture)
    assert result.has_roadmap_repo_drift
    assert result.has_issue_status_mismatch
    assert result.has_stale_evidence_ref
    assert result.has_evidence_mismatch
    assert result.forbidden_claims
    assert result.has_missing_paths
    assert "test_missing_contract.py" in "\n".join(result.missing_paths)


def test_fixture_canon_documents_drift_rules() -> None:
    canon = helpers.load_drift_fixture("docs_drift_canon_v1.json")
    assert canon["no_auto_fix_contract"]["mode"] == "detect_only"
    forbidden = canon["no_auto_fix_contract"]["forbidden"]
    assert "automatic doc correction" in forbidden
    assert "live_github_fetch_in_ci" in forbidden
    assert "automatic issue closure" in forbidden


def test_drift_helpers_module_avoids_live_dependencies() -> None:
    mod = sys.modules[helpers.__name__]
    for forbidden in _FORBIDDEN_RUNTIME_IMPORTS:
        assert forbidden not in vars(mod), f"forbidden import {forbidden!r}"


def test_real_repo_drift_scan_has_no_blocking_findings() -> None:
    scan = helpers.scan_arvp_docs_drift()
    blocking_kinds = {
        "arvp_flow_missing_disclaimer",
        "contract_test_missing",
        "p1_doc_contract_test_drift",
        "p1_contract_doc_missing",
        "p0_doc_contract_test_drift",
        "p0_contract_doc_missing",
        "arvp_roadmap_lr_drift",
        "lr050_mapping_lr_drift",
        "arvp_test_map_missing",
        "arvp_test_map_coverage_drift",
        "evidence_forbidden_claim",
    }
    blocking = [f for f in scan.findings if f.kind in blocking_kinds]
    assert not blocking, blocking
