"""Workflow contract guards for the parked Control Board Auto-Routing workflow (#2772)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "control_board_auto_routing.yml"
PARKING_HEADER = "PARKED fail-closed in #2772"
PARKING_REF_ISSUE = "#2772"
DISABLED_TRIGGERS = ("issues", "pull_request", "repository_dispatch")
ROUTING_INVOCATION_PATTERN = "python3 scripts/project/route_control_board.py"


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

    for trigger in DISABLED_TRIGGERS:
        assert trigger not in on_triggers, (
            f"Parked workflow must not declare `{trigger}` trigger "
            f"(removed in {PARKING_REF_ISSUE})."
        )

    assert "workflow_dispatch" in on_triggers, (
        "Parked workflow must still expose `workflow_dispatch` as the only trigger "
        "so operators can run the diagnostic stub manually."
    )


@pytest.mark.unit
def test_parked_workflow_has_no_concurrency_event_dependencies() -> None:
    workflow = _load_workflow()
    on_triggers = _on_triggers(workflow)

    for trigger in DISABLED_TRIGGERS:
        assert trigger not in on_triggers

    concurrency = workflow.get("concurrency") or {}
    if not concurrency:
        return

    group = concurrency.get("group") or ""
    assert "github.event.issue.number" not in group
    assert "github.event.pull_request.number" not in group
    assert "github.event.client_payload.issue_number" not in group


@pytest.mark.unit
def test_parked_workflow_permissions_reduced_to_contents_read() -> None:
    workflow = _load_workflow()
    permissions = workflow.get("permissions") or {}

    assert permissions == {"contents": "read"}, (
        "Parked workflow should only request `contents: read`; "
        "Project / Issues / Pull-Request write scopes were removed with the "
        f"auto-routing triggers in {PARKING_REF_ISSUE}."
    )


@pytest.mark.unit
def test_parked_workflow_does_not_invoke_routing_script() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert ROUTING_INVOCATION_PATTERN not in content, (
        f"Parked workflow must not invoke `{ROUTING_INVOCATION_PATTERN}`; the "
        "routing script requires an issue/PR/repository_dispatch payload that "
        f"`workflow_dispatch` cannot supply (see {PARKING_REF_ISSUE})."
    )


@pytest.mark.unit
def test_parked_workflow_does_not_reference_pat_or_app_secrets() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    forbidden_tokens = (
        "ADD_TO_PROJECT_PAT",
        "CDB_GH_APP_ID",
        "CDB_GH_APP_PRIVATE_KEY",
        "CDB_GH_APP_INSTALLATION_ID",
    )
    for token in forbidden_tokens:
        assert token not in content, (
            f"Parked workflow must not reference secret `{token}`; "
            f"it performs no Project mutations (see {PARKING_REF_ISSUE})."
        )


@pytest.mark.unit
def test_parked_workflow_does_not_set_project_owner_or_number() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    for env_var in ("PROJECT_OWNER", "PROJECT_NUMBER"):
        assert env_var not in content, (
            f"Parked workflow must not set env `{env_var}`; "
            f"no Project v2 calls remain in the diagnostic stub (see {PARKING_REF_ISSUE})."
        )


@pytest.mark.unit
def test_parked_workflow_diagnoses_without_making_project_calls() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    forbidden_commands = ("gh api graphql", "gh api repos")
    for command in forbidden_commands:
        assert command not in content, (
            f"Parked workflow must not invoke `{command}`; "
            f"the diagnostic stub is fail-closed and side-effect free (see {PARKING_REF_ISSUE})."
        )
