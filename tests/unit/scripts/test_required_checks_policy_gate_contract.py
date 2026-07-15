"""Required checks, CI split and policy-gate regression contract tests (#3847)."""

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


def test_derived_workflow_contexts_include_required_checks() -> None:
    mapping, parse_errors = derive_context_mapping(helpers.WORKFLOWS_DIR)
    assert parse_errors == []
    derived = set(mapping.keys())
    missing = sorted(helpers.REQUIRED_CHECK_CONTEXTS - derived)
    assert missing == [], f"missing derived required contexts: {missing}"


def test_ci_yaml_does_not_publish_required_pr_gate_contexts() -> None:
    mapping, _ = derive_context_mapping(helpers.WORKFLOWS_DIR)
    required_name = "ci (Unit/Integration + Lint gesammelt)"
    ci_yaml_sources = [
        entry
        for entry in mapping.get(required_name, [])
        if str(entry["workflow_file"]).endswith("ci.yaml")
    ]
    assert ci_yaml_sources == []


def test_ci_yml_publishes_canonical_required_ci_context() -> None:
    mapping, _ = derive_context_mapping(helpers.WORKFLOWS_DIR)
    required_name = "ci (Unit/Integration + Lint gesammelt)"
    assert required_name in mapping
    sources = {
        Path(str(entry["workflow_file"])).as_posix() for entry in mapping[required_name]
    }
    assert any(path.endswith("/.github/workflows/ci.yml") for path in sources)
    assert not any(path.endswith("/.github/workflows/ci.yaml") for path in sources)


def test_policy_gate_publishes_required_context() -> None:
    mapping, _ = derive_context_mapping(helpers.WORKFLOWS_DIR)
    assert "policy-gate" in mapping
    sources = {
        Path(str(entry["workflow_file"])).as_posix() for entry in mapping["policy-gate"]
    }
    assert any(path.endswith("/.github/workflows/policy-gate.yml") for path in sources)


def test_policy_gate_blocks_pull_request_target_in_source() -> None:
    content = (helpers.WORKFLOWS_DIR / "policy-gate.yml").read_text(encoding="utf-8")
    assert "pull_request_target" in content
    assert "failures.push" in content or "failures.push(" in content


def test_required_checks_audit_lists_same_required_pair() -> None:
    content = (helpers.WORKFLOWS_DIR / "required-checks-audit.yml").read_text(
        encoding="utf-8"
    )
    for context in helpers.REQUIRED_CHECK_CONTEXTS:
        assert context in content


def test_docs_guards_are_non_required_optional_checks() -> None:
    mapping, _ = derive_context_mapping(helpers.WORKFLOWS_DIR)
    for filename in helpers.NON_REQUIRED_GUARD_WORKFLOWS:
        workflow_suffix = f"/.github/workflows/{filename}"
        guard_contexts = [
            context
            for context, entries in mapping.items()
            if any(
                str(entry["workflow_file"]).endswith(workflow_suffix)
                for entry in entries
            )
        ]
        assert guard_contexts, f"expected derived context for {filename}"
        overlap = set(guard_contexts).intersection(helpers.REQUIRED_CHECK_CONTEXTS)
        assert (
            overlap == set()
        ), f"{filename} must not masquerade as required check; overlap={overlap}"


def test_drift_report_artifact_exists_and_documents_baseline_hash() -> None:
    report_path = (
        helpers.REPO_ROOT
        / "docs"
        / "evidence"
        / "reports"
        / "REQUIRED_CHECK_CONTEXTS_DRIFT_REPORT_main.md"
    )
    assert report_path.is_file()
    text = report_path.read_text(encoding="utf-8")
    assert "## Required Contexts (Baseline)" in text
    assert "## Extra Derivable Contexts (Informational)" in text


def test_baseline_json_has_branch_protection_source_metadata() -> None:
    payload = json.loads(helpers.REQUIRED_CHECKS_BASELINE.read_text(encoding="utf-8"))
    assert payload.get("source") == "branch_protection_main"
    assert isinstance(payload.get("contexts"), list)
