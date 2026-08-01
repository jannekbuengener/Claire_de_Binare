"""Required-check and policy-gate regression contracts."""

from __future__ import annotations

import json

import pytest

from scripts.governance.check_required_check_contexts import derive_context_mapping
from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_required_checks_baseline_matches_cdb_local_ci() -> None:
    contexts = helpers.load_required_checks_baseline(helpers.REQUIRED_CHECKS_BASELINE)
    assert set(contexts) == helpers.REQUIRED_CHECK_CONTEXTS
    assert contexts == ["cdb-local-ci"]


def test_app_check_run_contexts_contain_cdb_local_ci() -> None:
    check_runs = helpers.load_commit_status_contexts(helpers.REQUIRED_CHECKS_BASELINE)
    assert "cdb-local-ci" in check_runs
    assert set(check_runs) <= helpers.REQUIRED_CHECK_CONTEXTS


def test_workflow_mapping_need_not_include_cdb_local_ci() -> None:
    mapping, parse_errors = derive_context_mapping(helpers.WORKFLOWS_DIR)
    assert parse_errors == []
    # App Check Run (#4170): not a workflow job name.
    assert "cdb-local-ci" not in mapping


def test_policy_gate_blocks_pull_request_target_in_source() -> None:
    content = (helpers.WORKFLOWS_DIR / "policy-gate.yml").read_text(encoding="utf-8")
    assert "pull_request_target" in content
    assert "failures.push" in content or "failures.push(" in content


def test_policy_gate_workflow_still_publishes_named_job() -> None:
    """policy-gate.yml remains valuable workflow content (not a BP required context)."""
    mapping, _ = derive_context_mapping(helpers.WORKFLOWS_DIR)
    assert "policy-gate" in mapping
    sources = {
        str(entry["workflow_file"]).replace("\\", "/")
        for entry in mapping["policy-gate"]
    }
    assert any(path.endswith("/.github/workflows/policy-gate.yml") for path in sources)


def test_required_checks_audit_lists_cdb_local_ci() -> None:
    content = (helpers.WORKFLOWS_DIR / "required-checks-audit.yml").read_text(
        encoding="utf-8"
    )
    for context in helpers.REQUIRED_CHECK_CONTEXTS:
        assert context in content
    assert "ci (Unit/Integration + Lint gesammelt)" not in content


def test_docs_guards_are_non_required() -> None:
    mapping, _ = derive_context_mapping(helpers.WORKFLOWS_DIR)
    for filename in helpers.NON_REQUIRED_GUARD_WORKFLOWS:
        suffix = f"/.github/workflows/{filename}"
        contexts = {
            context
            for context, entries in mapping.items()
            if any(
                str(entry["workflow_file"]).replace("\\", "/").endswith(suffix)
                for entry in entries
            )
        }
        assert contexts
        assert contexts.isdisjoint(helpers.REQUIRED_CHECK_CONTEXTS)


def test_drift_report_and_baseline_metadata_exist() -> None:
    report = (
        helpers.REPO_ROOT
        / "docs/evidence/reports/REQUIRED_CHECK_CONTEXTS_DRIFT_REPORT_main.md"
    )
    report_text = report.read_text(encoding="utf-8")
    assert "## Required Contexts (Baseline)" in report_text
    assert "cdb-local-ci" in report_text
    payload = json.loads(helpers.REQUIRED_CHECKS_BASELINE.read_text(encoding="utf-8"))
    assert payload.get("source") == "branch_protection_main"
    assert payload.get("required_app_id") == 4410232
    assert "cdb-local-ci" in (payload.get("check_run_contexts") or [])
