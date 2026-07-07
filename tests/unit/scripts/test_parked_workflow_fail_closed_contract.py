"""Parked workflow fail-closed contract tests (#3846)."""

from __future__ import annotations

import pytest

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

PARKED_HEADER_MARKERS = {
    "control_board_auto_routing.yml": ("PARKED fail-closed", "#2772"),
    "control-board-routing-label-dispatch.yml": ("PARKED fail-closed", "#2805"),
    "auto-label.yml": ("Parked fail-closed", "#1642"),
    "comprehensive-issue-labeling.yml": ("Parked fail-closed", "#1642"),
    "issue-governance.yml": ("DEPRECATED", "#1642"),
    "gemini-scheduled-triage.yml": ("parked fail-closed",),
}


@pytest.mark.parametrize("filename", sorted(helpers.PARKED_WORKFLOW_FILES))
def test_known_parked_workflow_file_exists(filename: str) -> None:
    path = helpers.WORKFLOWS_DIR / filename
    assert path.is_file(), path


@pytest.mark.parametrize("filename", sorted(helpers.PARKED_WORKFLOW_FILES))
def test_parked_workflow_exposes_only_workflow_dispatch_trigger(filename: str) -> None:
    path = helpers.WORKFLOWS_DIR / filename
    workflow = helpers.load_workflow_yaml(path)
    triggers = helpers.extract_on_triggers(workflow)
    automatic = triggers.intersection(helpers.AUTOMATIC_TRIGGERS)
    assert not automatic, (
        f"{filename} must not declare automatic triggers; found {sorted(automatic)}"
    )
    assert "workflow_dispatch" in triggers, (
        f"{filename} must keep workflow_dispatch diagnostic stub trigger"
    )


@pytest.mark.parametrize("filename", sorted(helpers.PARKED_WORKFLOW_FILES))
def test_parked_workflow_has_no_forbidden_pull_request_target(filename: str) -> None:
    path = helpers.WORKFLOWS_DIR / filename
    assert helpers.workflow_declares_forbidden_trigger(path) == []


@pytest.mark.parametrize("filename,markers", sorted(PARKED_HEADER_MARKERS.items()))
def test_parked_workflow_documents_parking_in_header(
    filename: str,
    markers: tuple[str, ...],
) -> None:
    content = (helpers.WORKFLOWS_DIR / filename).read_text(encoding="utf-8")
    for marker in markers:
        assert marker in content, f"{filename} missing parking marker {marker!r}"


@pytest.mark.parametrize(
    "filename",
    [
        "auto-label.yml",
        "comprehensive-issue-labeling.yml",
        "issue-governance.yml",
        "control_board_auto_routing.yml",
        "control-board-routing-label-dispatch.yml",
    ],
)
def test_deprecated_parked_stubs_use_contents_read_only(filename: str) -> None:
    workflow = helpers.load_workflow_yaml(helpers.WORKFLOWS_DIR / filename)
    permissions = helpers.extract_effective_permissions(workflow)
    write_permissions = helpers.classify_write_permissions(permissions)
    assert write_permissions == set(), (
        f"{filename} parked stub must not request write permissions; found {write_permissions}"
    )


def test_gemini_scheduled_triage_parked_stub_has_no_schedule_trigger() -> None:
    workflow = helpers.load_workflow_yaml(
        helpers.WORKFLOWS_DIR / "gemini-scheduled-triage.yml"
    )
    triggers = helpers.extract_on_triggers(workflow)
    assert "schedule" not in triggers
    assert triggers == {"workflow_dispatch"}
