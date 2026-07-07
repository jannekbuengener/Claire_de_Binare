"""Agent-facing workflow map contract tests (#3854)."""

from __future__ import annotations

import json

import pytest

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REQUIRED_ENTRY_FIELDS = frozenset(
    {
        "file",
        "name",
        "purpose",
        "triggers",
        "permissions",
        "writes_github",
        "has_schedule",
        "status",
        "required_check_producer",
        "registered_in_markdown_register",
        "risk",
    }
)

ALLOWED_STATUS_VALUES = frozenset(
    {"active", "manual_only", "parked", "reusable", "frozen"}
)


def test_agent_workflow_map_file_exists_and_is_partial_coverage() -> None:
    payload = json.loads(helpers.AGENT_WORKFLOW_MAP_JSON.read_text(encoding="utf-8"))
    assert payload["coverage"] == "partial"
    assert payload["catalog_scope"] == "agent-facing-workflow-map-p2"
    assert payload["limitations"]
    assert "all workflows covered" not in " ".join(payload["limitations"]).lower()


def test_committed_agent_map_matches_builder_output() -> None:
    committed = json.loads(helpers.AGENT_WORKFLOW_MAP_JSON.read_text(encoding="utf-8"))
    built = helpers.build_agent_workflow_map()
    assert committed == built


def test_agent_map_lists_every_disk_workflow_or_marks_unregistered() -> None:
    payload = helpers.build_agent_workflow_map()
    disk = set(helpers.list_workflow_yaml_files(helpers.WORKFLOWS_DIR))
    mapped = {entry["file"] for entry in payload["entries"]}
    assert mapped == disk
    assert set(payload["unregistered_on_disk"]) == helpers.KNOWN_UNREGISTERED_WORKFLOWS
    for name in payload["unregistered_on_disk"]:
        entry = next(item for item in payload["entries"] if item["file"] == name)
        assert entry["registered_in_markdown_register"] is False


def test_agent_map_entry_schema_and_status_visibility() -> None:
    payload = helpers.build_agent_workflow_map()
    statuses = {entry["status"] for entry in payload["entries"]}
    assert statuses.issubset(ALLOWED_STATUS_VALUES)
    assert "parked" in statuses
    assert "reusable" in statuses
    assert "frozen" in statuses
    for entry in payload["entries"]:
        missing = REQUIRED_ENTRY_FIELDS - set(entry)
        assert not missing, f"{entry['file']} missing fields: {sorted(missing)}"


def test_required_check_producers_are_visible() -> None:
    payload = helpers.build_agent_workflow_map()
    producers = {
        entry["file"]
        for entry in payload["entries"]
        if entry["required_check_producer"]
    }
    assert producers == helpers.REQUIRED_CHECK_PRODUCER_FILES
    assert set(payload["required_check_contexts"]) == helpers.REQUIRED_CHECK_CONTEXTS


def test_write_and_schedule_semantics_are_visible() -> None:
    payload = helpers.build_agent_workflow_map()
    ci_entry = next(item for item in payload["entries"] if item["file"] == "ci.yml")
    assert ci_entry["writes_github"] is False
    assert ci_entry["has_schedule"] is False
    write_entry = next(
        item for item in payload["entries"] if item["file"] == "sync-labels.yml"
    )
    assert write_entry["writes_github"] is True


def test_risky_cascades_and_schedule_collisions_are_surfaced() -> None:
    payload = helpers.build_agent_workflow_map()
    assert payload["risky_cascade_families"]
    assert payload["risky_schedule_collisions"]
    monday_collision = payload["risky_schedule_collisions"].get("0 8 * * 1")
    assert monday_collision
    assert "weekly_digest.yml" in monday_collision
    assert "cdb-context-refresh-report.yml" in monday_collision


@pytest.mark.parametrize(
    "filename,expected_status",
    [
        ("ci.yml", "active"),
        ("ci.yaml", "frozen"),
        ("control_board_auto_routing.yml", "parked"),
        ("gemini-invoke.yml", "reusable"),
        ("cdb-control-followup-classifier.yml", "manual_only"),
    ],
)
def test_known_workflow_status_classification(
    filename: str,
    expected_status: str,
) -> None:
    assert (
        helpers.classify_workflow_operational_status(filename) == expected_status
    )


def test_map_builder_is_deterministic() -> None:
    first = helpers.build_agent_workflow_map()
    second = helpers.build_agent_workflow_map()
    assert first == second
