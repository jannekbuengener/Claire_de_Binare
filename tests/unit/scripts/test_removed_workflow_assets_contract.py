"""Deletion contract for retired workflow assets."""

from pathlib import Path

import pytest

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REMOVED_WORKFLOWS = {
    "auto-label.yml",
    "comprehensive-issue-labeling.yml",
    "issue-governance.yml",
    "control_board_auto_routing.yml",
    "control-board-routing-label-dispatch.yml",
    "gemini-scheduled-triage.yml",
    "bulk-issue-labeling.yml",
    "milestone-assignment.yml",
    "ci.yaml",
    "gemini-dispatch.yml",
    "gemini-invoke.yml",
    "gemini-review.yml",
    "gemini-triage.yml",
}

REMOVED_SUPPORT_FILES = {
    ".github/commands/gemini-invoke.toml",
    ".github/commands/gemini-review.toml",
    ".github/commands/gemini-triage.toml",
    ".github/commands/gemini-scheduled-triage.toml",
    "agents/templates/gemini_mcp_config.yml.template",
}


def test_retired_workflows_are_absent() -> None:
    assert REMOVED_WORKFLOWS.isdisjoint(helpers.list_workflow_yaml_files(helpers.WORKFLOWS_DIR))


@pytest.mark.parametrize("relative_path", sorted(REMOVED_SUPPORT_FILES))
def test_orphaned_support_files_are_absent(relative_path: str) -> None:
    assert not (helpers.REPO_ROOT / Path(relative_path)).exists()
