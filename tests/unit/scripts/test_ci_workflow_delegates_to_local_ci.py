"""Contract: ci.yml delegates validation to the local CI orchestrator (#4163)."""

from __future__ import annotations

import re

import pytest
import yaml

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

CI_WORKFLOW = helpers.WORKFLOWS_DIR / "ci.yml"
CANONICAL_JOB_NAME = "ci (Unit/Integration + Lint gesammelt)"
ORCHESTRATOR = "ci/scripts/run.py"


def _load_ci() -> dict:
    payload = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _ci_job_steps(payload: dict) -> list[dict]:
    jobs = payload.get("jobs") or {}
    ci_job = jobs.get("ci")
    assert isinstance(ci_job, dict)
    steps = ci_job.get("steps") or []
    assert isinstance(steps, list)
    return [step for step in steps if isinstance(step, dict)]


def _joined_run_scripts(steps: list[dict]) -> str:
    parts: list[str] = []
    for step in steps:
        run = step.get("run")
        if isinstance(run, str):
            parts.append(run)
    return "\n".join(parts)


def test_ci_workflow_identity_stable() -> None:
    payload = _load_ci()
    assert payload.get("name") == "ci"
    triggers = helpers.extract_on_triggers(payload)
    # #4401: PR trigger removed; push-to-main + workflow_dispatch retained.
    assert triggers == {"push", "workflow_dispatch"}
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "branches: [ main ]" in text or "branches: [main]" in text
    assert "pull_request" not in helpers.extract_on_triggers(payload)
    row = helpers.build_trigger_permission_row(CI_WORKFLOW)
    assert row.write_permissions == ()
    permissions = helpers.extract_top_level_permissions(payload)
    assert permissions.get("contents") == "read"
    concurrency = payload.get("concurrency") or {}
    assert concurrency.get("cancel-in-progress") is True
    assert "${{ github.workflow }}-${{ github.ref }}" in str(
        concurrency.get("group", "")
    )
    jobs = payload.get("jobs") or {}
    assert "ci" in jobs
    assert jobs["ci"].get("name") == CANONICAL_JOB_NAME


def test_ci_job_delegates_to_local_orchestrator_fast_profile() -> None:
    steps = _ci_job_steps(_load_ci())
    run_text = _joined_run_scripts(steps)
    assert ORCHESTRATOR in run_text
    assert "--profile fast" in run_text
    assert re.search(
        rf"python\s+{re.escape(ORCHESTRATOR)}\s+--profile\s+fast", run_text
    )


def test_ci_job_has_no_drift_command_copies() -> None:
    """Mapped validation must not remain as parallel shell copies in job ci."""
    steps = _ci_job_steps(_load_ci())
    run_text = _joined_run_scripts(steps)
    assert "ruff check ." not in run_text
    assert "BASE=" not in run_text
    assert "black --config" not in run_text
    assert "pytest -q" not in run_text
    assert "validate_onboarding_docs" not in run_text
    assert "validate_readme_links" not in run_text
    assert "mcp-config-validate" not in run_text


def test_ci_workflow_fail_closed_and_pinned_actions() -> None:
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    payload = _load_ci()
    assert "continue-on-error" not in text
    assert "exit 0" not in _joined_run_scripts(_ci_job_steps(payload))
    for job in (payload.get("jobs") or {}).values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            uses = step.get("uses")
            if isinstance(uses, str):
                assert "@" in uses
                pin = uses.split("@", 1)[1]
                assert re.fullmatch(r"[0-9a-f]{40}", pin), f"unpinned action: {uses}"


def test_required_context_remains_cdb_local_ci_not_ci_job_name() -> None:
    assert helpers.REQUIRED_CHECK_CONTEXTS == frozenset({"cdb-local-ci"})
    baseline = helpers.load_required_checks_baseline(helpers.REQUIRED_CHECKS_BASELINE)
    assert baseline == ["cdb-local-ci"]
    assert CANONICAL_JOB_NAME not in helpers.REQUIRED_CHECK_CONTEXTS


def test_policy_gate_remains_github_native() -> None:
    path = helpers.WORKFLOWS_DIR / "policy-gate.yml"
    content = path.read_text(encoding="utf-8")
    payload = yaml.safe_load(content)
    assert isinstance(payload, dict)
    jobs = payload.get("jobs") or {}
    assert "policy-gate" in jobs
    assert jobs["policy-gate"].get("name") == "policy-gate"
    assert ORCHESTRATOR not in content
    assert "actions/github-script@" in content
    assert "full policy-gate parity" not in content.lower()


def test_hosted_pr_triggers_removed_when_local_fast_ci_covers() -> None:
    """#4401: drop PR triggers for Fast-CI-covered hosted mirrors; keep policy-gate."""
    covered_by_fast_ci = (
        "ci.yml",
        "docs-conflict-guard.yml",
        "repository-canon-guard.yml",
    )
    for name in covered_by_fast_ci:
        triggers = helpers.extract_on_triggers(
            helpers.load_workflow_yaml(helpers.WORKFLOWS_DIR / name)
        )
        assert "pull_request" not in triggers, name
        assert "push" in triggers or "workflow_dispatch" in triggers
    # CodeQL is not Fast-CI-equivalent; PR trigger removed for cost, push+schedule kept.
    codeql = helpers.extract_on_triggers(
        helpers.load_workflow_yaml(helpers.WORKFLOWS_DIR / "codeql-python.yml")
    )
    assert "pull_request" not in codeql
    assert {"push", "schedule", "workflow_dispatch"} <= codeql
    policy = helpers.extract_on_triggers(
        helpers.load_workflow_yaml(helpers.WORKFLOWS_DIR / "policy-gate.yml")
    )
    assert "pull_request" in policy
    docs_stage = (helpers.REPO_ROOT / "ci" / "stages" / "docs.py").read_text(
        encoding="utf-8"
    )
    assert "tools.ci.docs_conflict_guard" in docs_stage
    assert "tools.ci.repository_canon_guard" in docs_stage
    run_text = _joined_run_scripts(_ci_job_steps(_load_ci()))
    assert ORCHESTRATOR in run_text and "--profile fast" in run_text
