"""Required-check and policy-gate regression contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.governance.check_required_check_contexts import derive_context_mapping
from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_required_checks_baseline_matches_canonical_pair() -> None:
    contexts = helpers.load_required_checks_baseline(helpers.REQUIRED_CHECKS_BASELINE)
    assert set(contexts) == helpers.REQUIRED_CHECK_CONTEXTS


def test_derived_contexts_include_required_checks() -> None:
    mapping, parse_errors = derive_context_mapping(helpers.WORKFLOWS_DIR)
    assert parse_errors == []
    assert helpers.REQUIRED_CHECK_CONTEXTS <= set(mapping)


def test_ci_yml_is_sole_canonical_ci_context_source() -> None:
    mapping, _ = derive_context_mapping(helpers.WORKFLOWS_DIR)
    sources = {
        Path(str(entry["workflow_file"])).as_posix()
        for entry in mapping["ci (Unit/Integration + Lint gesammelt)"]
    }
    assert sources
    assert all(path.endswith("/.github/workflows/ci.yml") for path in sources)


def test_policy_gate_publishes_required_context() -> None:
    mapping, _ = derive_context_mapping(helpers.WORKFLOWS_DIR)
    sources = {
        Path(str(entry["workflow_file"])).as_posix()
        for entry in mapping["policy-gate"]
    }
    assert any(path.endswith("/.github/workflows/policy-gate.yml") for path in sources)


def test_policy_gate_blocks_pull_request_target_in_source() -> None:
    content = (helpers.WORKFLOWS_DIR / "policy-gate.yml").read_text(encoding="utf-8")
    assert "pull_request_target" in content
    assert "failures.push" in content or "failures.push(" in content


def test_required_checks_audit_lists_same_pair() -> None:
    content = (helpers.WORKFLOWS_DIR / "required-checks-audit.yml").read_text(encoding="utf-8")
    for context in helpers.REQUIRED_CHECK_CONTEXTS:
        assert context in content


def test_docs_guards_are_non_required() -> None:
    mapping, _ = derive_context_mapping(helpers.WORKFLOWS_DIR)
    for filename in helpers.NON_REQUIRED_GUARD_WORKFLOWS:
        suffix = f"/.github/workflows/{filename}"
        contexts = {
            context
            for context, entries in mapping.items()
            if any(str(entry["workflow_file"]).endswith(suffix) for entry in entries)
        }
        assert contexts
        assert contexts.isdisjoint(helpers.REQUIRED_CHECK_CONTEXTS)


def test_drift_report_and_baseline_metadata_exist() -> None:
    report = helpers.REPO_ROOT / "docs/evidence/reports/REQUIRED_CHECK_CONTEXTS_DRIFT_REPORT_main.md"
    assert "## Required Contexts (Baseline)" in report.read_text(encoding="utf-8")
    payload = json.loads(helpers.REQUIRED_CHECKS_BASELINE.read_text(encoding="utf-8"))
    assert payload.get("source") == "branch_protection_main"
