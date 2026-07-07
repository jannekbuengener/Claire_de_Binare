"""Agent and AI workflow reachability/safety contract tests (#3849)."""

from __future__ import annotations

import pytest

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_reusable_gemini_workflow_files_exist() -> None:
    missing = sorted(
        name
        for name in helpers.REUSABLE_GEMINI_WORKFLOW_FILES
        if not (helpers.WORKFLOWS_DIR / name).is_file()
    )
    assert missing == []


def test_reachable_agent_ai_workflow_files_exist() -> None:
    missing = sorted(
        name
        for name in helpers.REACHABLE_AGENT_AI_WORKFLOW_FILES
        if not (helpers.WORKFLOWS_DIR / name).is_file()
    )
    assert missing == []


@pytest.mark.parametrize("filename", sorted(helpers.REUSABLE_GEMINI_WORKFLOW_FILES))
def test_reusable_gemini_workflows_are_workflow_call_only(filename: str) -> None:
    path = helpers.WORKFLOWS_DIR / filename
    assert helpers.reusable_workflow_is_workflow_call_only(path)


@pytest.mark.parametrize("filename", sorted(helpers.REUSABLE_GEMINI_WORKFLOW_FILES))
def test_reusable_gemini_workflows_have_no_hidden_standalone_triggers(filename: str) -> None:
    workflow = helpers.load_workflow_yaml(helpers.WORKFLOWS_DIR / filename)
    triggers = helpers.extract_on_triggers(workflow)
    automatic = triggers.intersection(helpers.AUTOMATIC_TRIGGERS)
    assert automatic == set()


def test_gemini_dispatch_is_explicit_placeholder() -> None:
    content = (helpers.WORKFLOWS_DIR / "gemini-dispatch.yml").read_text(encoding="utf-8")
    assert any(marker in content for marker in helpers.GEMINI_DISPATCH_PLACEHOLDER_MARKERS)
    workflow = helpers.load_workflow_yaml(helpers.WORKFLOWS_DIR / "gemini-dispatch.yml")
    triggers = helpers.extract_on_triggers(workflow)
    assert triggers == {"workflow_dispatch"}
    permissions = helpers.extract_effective_permissions(workflow)
    assert helpers.classify_write_permissions(permissions) == set()


@pytest.mark.parametrize(
    "filename,expected_triggers",
    [
        ("gemini-invoke.yml", ("workflow_call",)),
        ("gemini-review.yml", ("workflow_call",)),
        ("gemini-triage.yml", ("workflow_call",)),
        ("gemini-dispatch.yml", ("workflow_dispatch",)),
        ("opencode.yml", ("issue_comment", "pull_request_review_comment")),
        ("copilot-setup-steps.yml", ("push", "workflow_dispatch")),
        ("copilot-housekeeping.yml", ("schedule", "workflow_dispatch")),
        ("ai-review-router.yml", ("schedule", "workflow_dispatch")),
    ],
)
def test_agent_ai_trigger_classification(
    filename: str,
    expected_triggers: tuple[str, ...],
) -> None:
    row = helpers.build_trigger_permission_row(helpers.WORKFLOWS_DIR / filename)
    assert row.triggers == expected_triggers


def test_opencode_declares_id_token_write_permission() -> None:
    row = helpers.build_trigger_permission_row(helpers.WORKFLOWS_DIR / "opencode.yml")
    assert "id-token:write" in row.write_permissions


def test_gemini_invoke_declares_expected_write_permissions() -> None:
    row = helpers.build_trigger_permission_row(helpers.WORKFLOWS_DIR / "gemini-invoke.yml")
    assert row.write_permissions == (
        "id-token:write",
        "issues:write",
        "pull-requests:write",
    )


def test_gemini_scheduled_triage_remains_parked_not_reachable() -> None:
    workflow = helpers.load_workflow_yaml(
        helpers.WORKFLOWS_DIR / "gemini-scheduled-triage.yml"
    )
    triggers = helpers.extract_on_triggers(workflow)
    assert triggers == {"workflow_dispatch"}
    assert "schedule" not in triggers
