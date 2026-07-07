"""Main runtime docs/evidence drift regression tests (#3842).

Fixture-backed drift detection between core runtime eventflows, service contracts,
config/safety docs, and evidence surfaces. No auto-fix, no live GitHub in CI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tests.unit.runtime import _main_runtime_docs_drift_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

FIXTURES_ROOT = helpers.FIXTURES_ROOT

_FORBIDDEN_RUNTIME_IMPORTS = frozenset(
    {"requests", "httpx", "subprocess", "surrealdb", "gh"}
)


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))


def test_eventflow_services_have_repo_service_dirs() -> None:
    scan = helpers.scan_main_runtime_docs_drift()
    assert scan.eventflow_services
    assert scan.missing_service_dirs == (), scan.missing_service_dirs
    assert not any(
        finding.kind == "eventflow_service_dir_missing" for finding in scan.findings
    )


def test_eventflow_doc_declares_non_authoritative_status() -> None:
    text = helpers.EVENTFLOW_MD.read_text(encoding="utf-8").lower()
    assert "not authoritative" in text or "docs-only" in text


def test_p0_p1_contract_tests_exist_and_p1_doc_references_them() -> None:
    scan = helpers.scan_main_runtime_docs_drift()
    assert scan.missing_contract_tests == ()
    drift_kinds = {finding.kind for finding in scan.findings}
    assert "contract_test_missing" not in drift_kinds
    assert "p1_doc_contract_test_drift" not in drift_kinds


def test_market_state_contract_references_risk_consumer() -> None:
    text = helpers.MARKET_STATE_CONTRACT.read_text(encoding="utf-8")
    assert "cdb_risk" in text
    assert (helpers.REPO_ROOT / "services" / "risk").is_dir()


def test_lr_audit_status_contains_no_go_verdict() -> None:
    text = helpers.LR_AUDIT_STATUS.read_text(encoding="utf-8")
    assert "NO-GO" in text
    scan = helpers.scan_main_runtime_docs_drift()
    assert not any(f.kind == "config_safety_lr_drift" for f in scan.findings)


def test_active_evidence_docs_avoid_unpaired_live_go_claims() -> None:
    claims = helpers.scan_evidence_docs_for_forbidden_claims()
    assert claims == (), claims


def test_scan_outputs_include_limitations() -> None:
    scan = helpers.scan_main_runtime_docs_drift()
    assert scan.limitations
    assert any("no automatic" in item.lower() for item in scan.limitations)
    assert any("not authoritative" in item.lower() for item in scan.limitations)


def test_fixture_detects_eventflow_and_evidence_drift() -> None:
    fixture = _load_fixture("eventflow_evidence_mismatch_fixture.json")
    result = helpers.score_runtime_docs_drift_fixture(fixture)
    assert result.has_eventflow_drift
    assert "cdb_phantom_service" in fixture["eventflow_services"]
    assert result.has_evidence_mismatch
    assert result.forbidden_claims
    assert result.has_missing_paths
    assert "test_missing_contract.py" in "\n".join(result.missing_paths)


def test_fixture_canon_documents_drift_rules() -> None:
    canon = _load_fixture("docs_drift_canon_v1.json")
    assert canon["no_auto_fix_contract"]["mode"] == "detect_only"
    forbidden = canon["no_auto_fix_contract"]["forbidden"]
    assert "automatic doc correction" in forbidden
    assert "live_github_fetch_in_ci" in forbidden


def test_drift_helpers_module_avoids_live_dependencies() -> None:
    mod = sys.modules[helpers.__name__]
    for forbidden in _FORBIDDEN_RUNTIME_IMPORTS:
        assert forbidden not in vars(mod), f"forbidden import {forbidden!r}"


def test_real_repo_drift_scan_has_no_blocking_findings() -> None:
    scan = helpers.scan_main_runtime_docs_drift()
    blocking_kinds = {
        "eventflow_service_dir_missing",
        "contract_test_missing",
        "p1_doc_contract_test_drift",
        "p1_contract_doc_missing",
        "market_state_contract_drift",
        "market_state_consumer_missing",
        "config_safety_lr_drift",
        "evidence_forbidden_claim",
        "eventflow_missing_disclaimer",
    }
    blocking = [f for f in scan.findings if f.kind in blocking_kinds]
    assert not blocking, blocking
