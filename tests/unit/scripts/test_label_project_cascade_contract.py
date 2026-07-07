"""Label, milestone and project cascade contract tests (#3848)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_label_cascade_workflow_files_exist() -> None:
    missing = sorted(
        name
        for name in helpers.LABEL_CASCADE_WORKFLOW_FILES
        if not (helpers.WORKFLOWS_DIR / name).is_file()
    )
    assert missing == []


def test_label_cascade_map_is_fixture_visible_and_deterministic() -> None:
    first = helpers.build_label_cascade_map()
    second = helpers.build_label_cascade_map()
    assert first == second
    assert set(first) == helpers.LABEL_CASCADE_WORKFLOW_FILES


@pytest.mark.parametrize(
    "filename,expected_issues_types",
    [
        ("auto-milestone.yml", ("opened", "reopened")),
        ("auto-milestone-label-dispatch.yml", ("labeled",)),
        ("project_status_sync.yml", ("opened", "reopened", "transferred")),
        ("project_status_label_map.yml", ("closed", "labeled", "reopened", "unlabeled")),
        ("triage_guard.yml", ("demilestoned", "edited", "milestoned", "opened", "reopened", "transferred")),
        ("add_to_project.yml", ("opened", "reopened", "transferred")),
    ],
)
def test_issues_trigger_types_are_classified(
    filename: str,
    expected_issues_types: tuple[str, ...],
) -> None:
    row = helpers.build_label_cascade_row(helpers.WORKFLOWS_DIR / filename)
    assert row.issues_types == expected_issues_types


@pytest.mark.parametrize(
    "filename,expected_write_permissions",
    [
        ("auto-milestone.yml", ("issues:write",)),
        ("auto-milestone-label-dispatch.yml", ("contents:write",)),
        ("sync-labels.yml", ("issues:write",)),
    ],
)
def test_label_cascade_write_permissions_are_classified(
    filename: str,
    expected_write_permissions: tuple[str, ...],
) -> None:
    row = helpers.build_label_cascade_row(helpers.WORKFLOWS_DIR / filename)
    assert row.write_permissions == expected_write_permissions


@pytest.mark.parametrize(
    "filename",
    [
        "project_status_sync.yml",
        "project_status_label_map.yml",
        "triage_guard.yml",
        "add_to_project.yml",
    ],
)
def test_project_board_workflows_use_graphql_not_issues_write(filename: str) -> None:
    row = helpers.build_label_cascade_row(helpers.WORKFLOWS_DIR / filename)
    assert row.uses_project_api is True
    assert "issues:write" not in row.write_permissions


def test_issues_labeled_cascade_is_explicit_subset() -> None:
    cascade = helpers.build_label_cascade_map()
    labeled_files = {
        name for name, row in cascade.items() if "labeled" in row.issues_types
    }
    assert labeled_files == helpers.ISSUES_LABELED_CASCADE_FILES


def test_milestone_label_dispatch_repository_dispatch_cascade() -> None:
    for source, event_type, target in helpers.MILESTONE_DISPATCH_CASCADE:
        source_content = (helpers.WORKFLOWS_DIR / source).read_text(encoding="utf-8")
        target_workflow = helpers.load_workflow_yaml(helpers.WORKFLOWS_DIR / target)
        target_triggers = helpers.extract_on_triggers(target_workflow)
        assert event_type in source_content
        assert "repository_dispatch" in target_triggers


def test_sync_labels_is_push_triggered_not_issue_cascade() -> None:
    row = helpers.build_label_cascade_row(helpers.WORKFLOWS_DIR / "sync-labels.yml")
    assert row.issues_types == ()
    assert "push" in row.triggers


@pytest.mark.parametrize("filename", sorted(helpers.LABEL_CASCADE_WORKFLOW_FILES))
def test_label_cascade_workflows_document_noise_guards(filename: str) -> None:
    row = helpers.build_label_cascade_row(helpers.WORKFLOWS_DIR / filename)
    assert row.has_noise_guard is True


def test_no_label_cascade_test_calls_live_project_api() -> None:
    this_file = Path(__file__)
    content = this_file.read_text(encoding="utf-8")
    for marker in helpers.PROJECT_API_MARKERS:
        assert marker not in content
