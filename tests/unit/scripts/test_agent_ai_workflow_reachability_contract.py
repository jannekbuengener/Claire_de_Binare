"""Reachability contracts for active agent-facing workflows."""

from __future__ import annotations

import pytest

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]


@pytest.mark.parametrize(
    "filename,expected_triggers",
    [
        ("opencode.yml", ("issue_comment", "pull_request_review_comment")),
        ("copilot-setup-steps.yml", ("push", "workflow_dispatch")),
        ("copilot-housekeeping.yml", ("schedule", "workflow_dispatch")),
        ("ai-review-router.yml", ("schedule", "workflow_dispatch")),
    ],
)
def test_active_agent_workflows_have_entrypoints(
    filename: str, expected_triggers: tuple[str, ...]
) -> None:
    row = helpers.build_trigger_permission_row(helpers.WORKFLOWS_DIR / filename)
    assert row.triggers == expected_triggers
