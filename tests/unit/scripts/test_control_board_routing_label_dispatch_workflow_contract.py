"""Workflow contract guards for the parked Control Board Routing Label Dispatch workflow (#2805)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "control-board-routing-label-dispatch.yml"
)
PARKING_HEADER = "PARKED fail-closed in #2805"
PARKING_REF_ISSUE = "#2805"
REMOVED_LISTENER_ISSUE = "#2772"
DISPATCH_EVENT_TYPE = "control_board_route_issue_label"


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), f"Workflow not found: {WORKFLOW_PATH}"
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _on_triggers(workflow: dict) -> dict:
    return workflow.get("on") or workflow.get(True) or {}


@pytest.mark.unit
def test_workflow_file_is_parked_with_header_comment() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert PARKING_HEADER in content
    assert PARKING_REF_ISSUE in content


@pytest.mark.unit
def test_parked_workflow_exposes_only_workflow_dispatch_trigger() -> None:
    workflow = _load_workflow()
    on_triggers = _on_triggers(workflow)

    assert "issues" not in on_triggers, (
        f"Parked workflow must not declare `issues` trigger "
        f"(removed in {PARKING_REF_ISSUE})."
    )
    assert "repository_dispatch" not in on_triggers, (
        f"Parked workflow must not declare `repository_dispatch` trigger "
        f"(listener was removed in {REMOVED_LISTENER_ISSUE})."
    )

    assert "workflow_dispatch" in on_triggers, (
        "Parked workflow must still expose `workflow_dispatch` as the only trigger "
        "so operators can run the diagnostic stub manually."
    )


@pytest.mark.unit
def test_parked_workflow_does_not_use_github_script_action() -> None:
    workflow = _load_workflow()
    jobs = workflow.get("jobs", {})
    for job_name, job_def in jobs.items():
        steps = job_def.get("steps", [])
        for step in steps:
            uses_action = step.get("uses", "")
            assert "actions/github-script" not in uses_action, (
                f"Parked workflow job `{job_name}` must not use "
                f"`actions/github-script` step in `{step.get('name', '')}`; "
                f"the `createDispatchEvent` call was removed in {PARKING_REF_ISSUE}."
            )


@pytest.mark.unit
def test_parked_workflow_does_not_reference_dispatch_event_type_in_on_block() -> None:
    workflow = _load_workflow()
    on_triggers = _on_triggers(workflow)
    assert "repository_dispatch" not in on_triggers, (
        f"Parked workflow must not declare `repository_dispatch` trigger in `on:` block; "
        f"the `{DISPATCH_EVENT_TYPE}` listener was removed in "
        f"{REMOVED_LISTENER_ISSUE}."
    )


@pytest.mark.unit
def test_parked_workflow_permissions_reduced_to_contents_read() -> None:
    workflow = _load_workflow()
    permissions = workflow.get("permissions") or {}

    assert permissions == {"contents": "read"}, (
        "Parked workflow should only request `contents: read`; "
        f"`contents: write` for `createDispatchEvent` was removed in {PARKING_REF_ISSUE}."
    )


@pytest.mark.unit
def test_parked_workflow_has_no_label_event_references() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    forbidden_label_refs = (
        "startsWith(github.event.label.name",
        "github.event.label.name",
        "context.payload.label?.name",
    )
    for ref in forbidden_label_refs:
        assert ref not in content, (
            f"Parked workflow must not reference label event payload `{ref}`; "
            f"the `issues: labeled` trigger was removed in {PARKING_REF_ISSUE}."
        )
