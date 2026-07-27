"""Unit tests for tools.ci.policy_gate_local (Issue #4164 / #4169)."""

from __future__ import annotations

import pytest

from tools.ci.policy_gate_local import evaluate_policy_gate

pytestmark = pytest.mark.unit

SAFE_WORKFLOW = """
name: Safe
on:
  pull_request:
permissions:
  contents: read
jobs:
  j:
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""

WORKFLOW_RUN_METADATA = """
name: Meta
on:
  workflow_run:
    workflows: [ci]
    types: [completed]
permissions:
  contents: read
jobs:
  j:
    runs-on: ubuntu-latest
    steps:
      - run: echo metadata-only
"""


def test_docs_only_pass():
    result = evaluate_policy_gate(
        title="docs-only: update runbook",
        labels=[],
        files=[{"filename": "docs/ci/local-status-publisher.md", "status": "modified"}],
    )
    assert result.ok is True
    assert result.category == "docs-only"
    assert result.category_source == "title-prefix"


def test_docs_only_with_code_fail():
    result = evaluate_policy_gate(
        title="docs-only: sneak code",
        labels=["docs-only"],
        files=[
            {"filename": "docs/readme.md", "status": "modified"},
            {"filename": "core/utils/clock.py", "status": "modified"},
        ],
    )
    assert result.ok is False
    assert result.category == "docs-only"
    assert any("docs-only allows only" in f for f in result.failures)


def test_workflows_only_with_bad_file_fail():
    result = evaluate_policy_gate(
        title="workflows-only: touch service",
        labels=["workflows-only"],
        files=[
            {"filename": ".github/workflows/ci.yml", "status": "modified"},
            {"filename": "services/risk/service.py", "status": "modified"},
        ],
        workflow_contents={".github/workflows/ci.yml": SAFE_WORKFLOW},
    )
    assert result.ok is False
    assert result.category == "workflows-only"
    assert any("workflows-only allows only" in f for f in result.failures)


def test_pull_request_target_fail():
    bad = SAFE_WORKFLOW.replace("pull_request:", "pull_request_target:")
    result = evaluate_policy_gate(
        title="fix workflow",
        labels=[],
        files=[{"filename": ".github/workflows/bad.yml", "status": "modified"}],
        workflow_contents={".github/workflows/bad.yml": bad},
    )
    assert result.ok is False
    assert any("pull_request_target" in f for f in result.failures)


def test_write_all_fail():
    bad = SAFE_WORKFLOW.replace(
        "permissions:\n  contents: read", "permissions: write-all"
    )
    result = evaluate_policy_gate(
        title="fix workflow",
        labels=[],
        files=[{"filename": ".github/workflows/bad.yml", "status": "modified"}],
        workflow_contents={".github/workflows/bad.yml": bad},
    )
    assert result.ok is False
    assert any("write-all" in f for f in result.failures)


def test_missing_permissions_fail():
    no_perms = """
name: NoPerms
on:
  pull_request:
jobs:
  j:
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""
    result = evaluate_policy_gate(
        title="fix workflow",
        labels=[],
        files=[{"filename": ".github/workflows/bad.yml", "status": "modified"}],
        workflow_contents={".github/workflows/bad.yml": no_perms},
    )
    assert result.ok is False
    assert any("missing an explicit permissions" in f for f in result.failures)


def test_workflow_run_plus_checkout_fail():
    bad = WORKFLOW_RUN_METADATA.replace(
        "- run: echo metadata-only",
        "- uses: actions/checkout@v4\n      - run: echo metadata-only",
    )
    result = evaluate_policy_gate(
        title="fix workflow",
        labels=[],
        files=[{"filename": ".github/workflows/bad.yml", "status": "modified"}],
        workflow_contents={".github/workflows/bad.yml": bad},
    )
    assert result.ok is False
    assert any("metadata-only" in f for f in result.failures)


def test_core_service_pass():
    result = evaluate_policy_gate(
        title="feat(risk): tighten exposure gate",
        labels=[],
        files=[
            {"filename": "services/risk/service.py", "status": "modified"},
            {"filename": "tests/unit/risk/test_risk_service.py", "status": "added"},
        ],
    )
    assert result.ok is True
    assert result.category == "core/service"
    assert result.category_source == "default"
    assert any("core/service scope classified" in p for p in result.passes)


def test_removed_workflow_skips_content_inspection():
    result = evaluate_policy_gate(
        title="chore: drop workflow",
        labels=[],
        files=[{"filename": ".github/workflows/old.yml", "status": "removed"}],
    )
    assert result.ok is True
    assert result.category == "workflows-only"
    assert result.category_source == "file-inference"
